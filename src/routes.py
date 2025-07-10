from flask import render_template, request, redirect, send_file, url_for, flash, jsonify, send_from_directory
from flask_login import login_required, current_user, login_user, logout_user
from src import app, bcrypt, database
from src.models import User, FuncaoUser, ComprovantesPagamento
from src.forms import InscricaoForm, LoginForm, FormCriarUsuario
import os
import re
import pandas as pd
import io
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
    return render_template("painel.html", usuario=current_user)


@app.route("/upload_comprovante", methods=["POST"])
@login_required
def upload_comprovante():
    file = request.files.get("comprovante")
    if file:
        filename = secure_filename(file.filename)
        caminho = os.path.join(app.root_path, 'static',
                               'comprovantes', filename)
        file.save(caminho)

        novo = ComprovantesPagamento(
            id_user=current_user.id,
            parcela="Única",
            arquivo_comprovante=filename,
            status="Pendente"
        )
        database.session.add(novo)
        database.session.commit()
        flash("Comprovante enviado com sucesso!", "success")

    return redirect(url_for("painel_candidato"))


@app.route("/admin/comprovantes")
@login_required
def admin_comprovantes():
    if current_user.funcao_user_id != 1:  # ID 1 = DIRETOR, por exemplo
        flash("Acesso restrito!", "danger")
        return redirect(url_for("info"))

    comprovantes = ComprovantesPagamento.query.order_by(
        ComprovantesPagamento.data_envio.desc()).all()
    return render_template("admin_comprovantes.html", comprovantes=comprovantes)


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


@app.route("/exportar_comprovantes")
@login_required
def exportar_comprovantes():
    # Buscar todos os comprovantes com o usuário relacionado
    comprovantes = database.session.query(
        ComprovantesPagamento).join(User).all()

    # Montar os dados para o DataFrame
    dados = []
    for c in comprovantes:
        dados.append({
            "Nome": c.usuario.nome,
            "Email": c.usuario.email,
            "Telefone": c.usuario.telefone,
            "IAP Local": c.usuario.iap_local,
            "Parcela": c.parcela or "Única",
            "Arquivo": c.arquivo_comprovante,
            "Status": c.status,
            "Data Envio": c.data_envio.strftime("%d/%m/%Y %H:%M"),
        })

    # Criar o DataFrame
    df = pd.DataFrame(dados)

    # Criar arquivo Excel em memória
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name="Comprovantes", index=False)

    output.seek(0)

    return send_file(
        output,
        download_name="comprovantes_exportados.xlsx",
        as_attachment=True,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Você saiu com sucesso!", "info")
    return redirect(url_for("login"))
