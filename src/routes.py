import datetime
from flask import render_template, request, redirect, send_file, session, url_for, flash, jsonify, send_from_directory, current_app
from flask_login import login_required, current_user, login_user, logout_user
from src import app, bcrypt, database
from src.models import User, FuncaoUser, ComprovantesPagamento
from src.forms import InscricaoForm, LoginForm, FormCriarUsuario
from src import supabase
import os
import re
import pandas as pd
import io
import uuid
from werkzeug.utils import secure_filename


@app.route("/")
def home():
    # if current_user.is_authenticated:
    #     return redirect(url_for('candidato'))
    return redirect(url_for('info'))


@app.route("/info", methods=['GET', 'POST'])
def info():
    return render_template('info.html')


def get_user_ip():
    # Verifica se o cabeçalho X-Forwarded-For está presente
    if request.headers.get('X-Forwarded-For'):
        # Pode conter múltiplos IPs, estou pegando o primeiro
        ip = request.headers.getlist('X-Forwarded-For')[0]
    else:
        # Fallback para o IP remoto
        ip = request.remote_addr
    return ip


@app.route("/inscricao", methods=["GET", "POST"])
def inscricao():
    if current_user.is_authenticated:
        return redirect(url_for("painel_candidato"))

    form = InscricaoForm()
    if form.validate_on_submit():
        telefone_limpo = re.sub(r"\D", "", form.telefone.data or "")
        senha_gerada = telefone_limpo or "123456"

        hash_senha = bcrypt.generate_password_hash(
            senha_gerada).decode("utf-8")
        novo_usuario = User(
            nome=form.nome.data,
            email=form.email.data,
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

    return render_template("inscricao.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("painel_candidato"))

    form = LoginForm()
    if form.validate_on_submit():
        usuario = User.query.filter_by(email=form.email.data).first()
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
    return render_template("login.html", form=form)


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

    return render_template(
        "painel.html",
        usuario=current_user,
        status_comprovante=status,
        url_comprovante=url_arquivo
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


@app.route("/admin/comprovantes")
@login_required
def admin_comprovantes():
    if current_user.funcao_user_id != 1:
        flash("Acesso restrito!", "danger")
        return redirect(url_for("info"))

    comprovantes = ComprovantesPagamento.query.filter(
        ComprovantesPagamento.status == "AGUARDANDO CONFIRMAÇÃO"
    ).order_by(ComprovantesPagamento.data_envio.desc()).all()

    for c in comprovantes:
        if c.arquivo_comprovante:
            c.link_arquivo = supabase.storage.from_(
                "comprovantes").get_public_url(c.arquivo_comprovante)

    return render_template("admin_comprovantes.html", comprovantes=comprovantes)


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

    return render_template("admin_historico_comprovantes.html", comprovantes=comprovantes)


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

    return render_template("admin_candidatos.html", candidatos=candidatos)


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
