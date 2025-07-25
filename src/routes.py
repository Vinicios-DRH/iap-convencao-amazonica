import datetime
from flask import abort, render_template, request, redirect, send_file, session, url_for, flash, jsonify, send_from_directory, current_app
from flask_login import login_required, current_user, login_user, logout_user
from src import UPLOAD_FOLDER, app, bcrypt, database
from src.models import Filho, User, FuncaoUser, ComprovantesPagamento, ComprovanteFilho
from src.forms import InscricaoForm, LoginForm, FormCriarUsuario
from src import supabase
import os
import re
import pandas as pd
import io
import uuid
from werkzeug.utils import secure_filename
from src.controllers.b2_utils import upload_to_b2, get_b2_file_url


@app.route("/")
def home():
    # if current_user.is_authenticated:
    #     return redirect(url_for('candidato'))
    return redirect(url_for('save_the_date'))


@app.route("/save-the-date", methods=['GET', 'POST'])
def save_the_date():
    return render_template('conferencia_reino_ntcnc/save_the_date_2.html')


@app.route("/conferencia-reino", methods=['GET', 'POST'])
def info():
    return render_template('conferencia_reino_ntcnc/info.html')


def get_user_ip():
    # Verifica se o cabeçalho X-Forwarded-For está presente
    if request.headers.get('X-Forwarded-For'):
        # Pode conter múltiplos IPs, estou pegando o primeiro
        ip = request.headers.getlist('X-Forwarded-For')[0]
    else:
        # Fallback para o IP remoto
        ip = request.remote_addr
    return ip


def inscricoes_suspensas():
    return os.environ.get("INSCRICOES_SUSPENSAS") == "1"


@app.route("/inscricao", methods=["GET", "POST"])
def inscricao():
    if inscricoes_suspensas():
        # Se for admin, permite o acesso normal
        if current_user.is_authenticated and current_user.funcao_user_id == 1:
            pass  # Segue normal
        else:
            return render_template("conferencia_reino_ntcnc/suspenso.html")

    form = InscricaoForm()
    if form.validate_on_submit():
        telefone_limpo = re.sub(r"\D", "", form.telefone.data or "")
        senha_gerada = telefone_limpo or "123456"

        hash_senha = bcrypt.generate_password_hash(
            senha_gerada).decode("utf-8")
        novo_usuario = User(
            nome=form.nome.data,
            email=form.email.data.lower(),
            telefone=telefone_limpo,
            iap_local=form.iap_local.data,
            senha=hash_senha,
            ip_address=get_user_ip()
        )
        database.session.add(novo_usuario)
        database.session.commit()
        login_user(novo_usuario)

        # Cria o comprovante pendente automaticamente
        comprovante_pendente = ComprovantesPagamento(
            id_user=novo_usuario.id,
            status="PENDENTE",
            parcela="1ª PARCELA"
        )
        database.session.add(comprovante_pendente)
        database.session.commit()

        flash("Inscrição realizada com sucesso!", "success")
        return redirect(url_for("painel_candidato"))

    return render_template("conferencia_reino_ntcnc/inscricao.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    if inscricoes_suspensas():
        if current_user.is_authenticated and current_user.funcao_user_id == 1:
            pass
        else:
            return render_template("suspenso.html")

    form = LoginForm()
    if form.validate_on_submit():
        usuario = User.query.filter_by(email=form.email.data.lower()).first()
        if usuario and bcrypt.check_password_hash(usuario.senha, form.senha.data):
            login_user(usuario, remember=form.lembrar.data)
            flash("Login realizado com sucesso!", "success")

            # Redireciona conforme função
            if usuario.funcao_user_id == 1:  # DIRETOR
                return redirect(url_for("admin_comprovantes"))
            else:
                return redirect(url_for("painel_candidato"))
        else:
            flash("E-mail ou senha inválidos.", "danger")
    return render_template("conferencia_reino_ntcnc/login.html", form=form)


@app.route("/painel")
@login_required
def painel_candidato():
    comprovante = ComprovantesPagamento.query.filter(
        ComprovantesPagamento.id_user == current_user.id,
        ComprovantesPagamento.arquivo_comprovante.isnot(None)
    ).order_by(ComprovantesPagamento.data_envio.desc()).first()

    status = None
    url_arquivo = None

    if comprovante:
        status = comprovante.status
        url_arquivo = current_app.supabase.storage.from_("comprovantes")\
            .get_public_url(comprovante.arquivo_comprovante)
    else:
        comprovante = ComprovantesPagamento.query.filter_by(
            id_user=current_user.id
        ).order_by(ComprovantesPagamento.data_envio.desc()).first()
        if comprovante:
            status = comprovante.status

    filhos = Filho.query.filter_by(id_usuario=current_user.id).all()

    for filho in filhos:
        comprovantes = sorted(filho.comprovantes,
                              key=lambda c: c.data_envio, reverse=True)
        filho.comp_pendente = next(
            (c for c in comprovantes if c.status == "AGUARDANDO CONFIRMAÇÃO"), None)
        filho.comp_rejeitado = next(
            (c for c in comprovantes if c.status == "Rejeitado"), None)
        filho.comp_aprovado = next(
            (c for c in comprovantes if getattr(c, 'status', None) == "Aprovado"), None)

    return render_template(
        "conferencia_reino_ntcnc/painel.html",
        usuario=current_user,
        status_comprovante=status,
        url_comprovante=url_arquivo,
        filhos=filhos
    )


@app.route("/upload_comprovante", methods=["POST"])
@login_required
def upload_comprovante():
    file = request.files.get("comprovante")
    if not file or file.filename.strip() == "":
        flash("Nenhum arquivo selecionado.", "warning")
        return redirect(url_for("painel_candidato"))

    supabase = current_app.supabase

    try:
        # Gera nome único pra evitar conflitos
        ext = file.filename.rsplit(".", 1)[-1].lower()
        nome_arquivo = f"{uuid.uuid4().hex}.{ext}"
        caminho_bucket = f"{current_user.id}/{nome_arquivo}"

        # Upload para Supabase Storage (USA BYTES)
        file.stream.seek(0)
        file_bytes = file.read()
        resultado = supabase.storage.from_("comprovantes").upload(
            caminho_bucket, file_bytes, {"content-type": file.mimetype}
        )

        # Procura pendente (envio inicial)
        comprovante = ComprovantesPagamento.query.filter_by(
            id_user=current_user.id, status="PENDENTE"
        ).order_by(ComprovantesPagamento.data_envio.desc()).first()

        if comprovante:
            # Atualiza o existente
            comprovante.arquivo_comprovante = caminho_bucket
            comprovante.parcela = "Única"
            comprovante.status = "AGUARDANDO CONFIRMAÇÃO"
            comprovante.data_envio = datetime.datetime.utcnow()
            database.session.commit()
        else:
            # Se não existe PENDENTE, cria um NOVO
            novo_comprovante = ComprovantesPagamento(
                id_user=current_user.id,
                parcela="Única",
                arquivo_comprovante=caminho_bucket,
                status="AGUARDANDO CONFIRMAÇÃO",
                data_envio=datetime.datetime.utcnow()
            )
            database.session.add(novo_comprovante)
            database.session.commit()

        flash("Comprovante enviado com sucesso!", "success")

    except Exception as e:
        print("Erro no upload:", e)
        flash("Erro ao enviar comprovante!", "danger")

    return redirect(url_for("painel_candidato"))


@app.route("/painel/filhos", methods=["POST"])
@login_required
def adicionar_filho():
    qt = int(request.form.get("quantidade_filhos", 0))
    for i in range(1, qt+1):
        nome = request.form.get(f"nome_filho_{i}")
        idade = int(request.form.get(f"idade_filho_{i}", 0))
        if nome and idade is not None:
            filho = Filho(nome=nome, idade=idade, paga_inscricao=(
                idade >= 5), id_usuario=current_user.id)
            database.session.add(filho)
    database.session.commit()
    flash("Informações dos filhos salvas!", "success")
    return redirect(url_for("painel_candidato"))


@app.route('/upload_comprovante_filho/<int:id>', methods=['POST'])
@login_required
def upload_comprovante_filho(id):
    filho = Filho.query.get_or_404(id)
    if filho.id_usuario != current_user.id:
        abort(403)
    arquivos = request.files.getlist("comprovante")
    for arquivo in arquivos:
        if arquivo:
            filename = secure_filename(arquivo.filename)
            caminho = f"filhos/{current_user.id}/{filho.id}_{filename}"
            upload_to_b2(caminho, arquivo.stream)
            novo_comp = ComprovanteFilho(
                id_filho=filho.id, caminho_arquivo=caminho)
            database.session.add(novo_comp)
    database.session.commit()
    flash("Comprovante(s) enviado(s)!", "success")
    return redirect(url_for("painel_candidato"))


@app.route("/admin/comprovantes")
@login_required
def admin_comprovantes():
    if current_user.funcao_user_id != 1:
        flash("Acesso restrito!", "danger")
        return redirect(url_for("info"))

    # Comprovantes do responsável
    comprovantes = ComprovantesPagamento.query.filter(
        ComprovantesPagamento.status == "AGUARDANDO CONFIRMAÇÃO"
    ).order_by(ComprovantesPagamento.data_envio.desc()).all()
    for c in comprovantes:
        if c.arquivo_comprovante:
            c.link_arquivo = supabase.storage.from_(
                "comprovantes").get_public_url(c.arquivo_comprovante)

    # Comprovantes dos filhos
    comprovantes_filhos = ComprovanteFilho.query.\
        join(Filho).filter(ComprovanteFilho.status == "AGUARDANDO CONFIRMAÇÃO").\
        order_by(ComprovanteFilho.data_envio.desc()).all()

    # Adiciona o link público do arquivo (Backblaze)
    from src.controllers.b2_utils import get_b2_file_url
    for cf in comprovantes_filhos:
        cf.link_arquivo = get_b2_file_url(cf.caminho_arquivo)

    return render_template(
        "conferencia_reino_ntcnc/admin_comprovantes.html",
        comprovantes=comprovantes,
        comprovantes_filhos=comprovantes_filhos
    )


@app.route("/admin/comprovantes/historico")
@login_required
def historico_comprovantes():
    if current_user.funcao_user_id != 1:
        flash("Acesso restrito!", "danger")
        return redirect(url_for("info"))

    comprovantes = ComprovantesPagamento.query.order_by(
        ComprovantesPagamento.data_envio.desc()).all()

    for c in comprovantes:
        if c.arquivo_comprovante:
            c.link_arquivo = supabase.storage.from_(
                "comprovantes").get_public_url(c.arquivo_comprovante)

    return render_template("conferencia_reino_ntcnc/admin_historico_comprovantes.html", comprovantes=comprovantes)


@app.route("/admin/comprovantes/filho/<int:id>", methods=["POST"])
@login_required
def atualizar_comprovante_filho(id):
    if current_user.funcao_user_id != 1:
        abort(403)
    comp = ComprovanteFilho.query.get_or_404(id)
    status = request.form.get("status")
    comp.status = status
    database.session.commit()
    flash(f"Comprovante do filho atualizado para {status}!", "success")
    return redirect(url_for("admin_comprovantes"))


@app.route("/admin/comprovantes/<int:id>/atualizar", methods=["POST"])
@login_required
def atualizar_comprovante(id):
    if current_user.funcao_user_id != 1:
        flash("Acesso negado!", "danger")
        return redirect(url_for("info"))

    status = request.form.get("status")
    comp = ComprovantesPagamento.query.get_or_404(id)
    comp.status = status
    database.session.commit()
    flash(f"Status atualizado para {status}", "success")
    return redirect(url_for("admin_comprovantes"))


@app.route("/admin/candidatos")
@login_required
def admin_candidatos():
    if current_user.funcao_user_id != 1:
        flash("Acesso restrito!", "danger")
        return redirect(url_for("info"))

    # Pega todos os usuários (ou filtra por tipo se quiser)
    candidatos = User.query.order_by(User.nome).all()

    # Se quiser o último status do comprovante do cara:
    for c in candidatos:
        ultimo_comprovante = ComprovantesPagamento.query.filter_by(id_user=c.id)\
            .order_by(ComprovantesPagamento.data_envio.desc()).first()
        c.status_comprovante = ultimo_comprovante.status if ultimo_comprovante else "Não enviado"
        c.data_envio = ultimo_comprovante.data_envio if ultimo_comprovante else None

    return render_template("conferencia_reino_ntcnc/admin_candidatos.html", candidatos=candidatos)


@app.route("/admin/candidatos/exportar")
@login_required
def exportar_candidatos():
    if current_user.funcao_user_id != 1:
        flash("Acesso restrito!", "danger")
        return redirect(url_for("info"))

    candidatos = User.query.order_by(User.nome).all()
    data = []
    for c in candidatos:
        ultimo_comprovante = ComprovantesPagamento.query.filter_by(id_user=c.id)\
            .order_by(ComprovantesPagamento.data_envio.desc()).first()
        status = ultimo_comprovante.status if ultimo_comprovante else "Não enviado"
        data_envio = ultimo_comprovante.data_envio.strftime(
            '%d/%m/%Y %H:%M') if ultimo_comprovante and ultimo_comprovante.data_envio else ""
        data.append({
            "Nome": c.nome,
            "Email": c.email,
            "Telefone": c.telefone,
            "IAP Local": getattr(c, "iap_local", ""),  # só se existir o campo
            "Status Comprovante": status,
            "Data do Último Comprovante": data_envio,
            "Data de Inscrição": c.created_at.strftime('%d/%m/%Y %H:%M') if getattr(c, "created_at", None) else ""
        })

    df = pd.DataFrame(data)
    output = io.BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    return send_file(output, download_name="candidatos.xlsx", as_attachment=True)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    session.pop('_flashes', None)
    flash("Você saiu com sucesso!", "info")
    return redirect(url_for("login"))
