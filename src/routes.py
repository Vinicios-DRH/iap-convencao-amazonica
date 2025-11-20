# iap_laranjeiras/routes.py
from datetime import datetime, timedelta
from io import BytesIO
from flask import (
    render_template,
    redirect,
    send_file,
    url_for,
    flash,
    request,
)
from flask_login import login_user, logout_user, login_required, current_user
import pytz
from sqlalchemy import func

from src import app, database as db
from src.models import User, FichaPasse
from src.forms import LoginForm, FichaPasseForm
import openpyxl


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user and user.check_password(form.senha.data):
            login_user(user, remember=form.lembrar.data)
            next_page = request.args.get("next") or url_for("dashboard")
            return redirect(next_page)
        flash("E-mail ou senha inválidos.", "danger")
    return render_template("laranjeiras/auth_login.html", form=form)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


fuso_am = pytz.timezone("America/Manaus")


@app.route("/")
@login_required
def dashboard():
    # Agora em Manaus
    agora = datetime.now(fuso_am)

    # Limites de dia/semana/mês
    inicio_dia = agora.replace(hour=0, minute=0, second=0, microsecond=0)
    fim_dia = agora.replace(hour=23, minute=59, second=59, microsecond=999999)

    inicio_semana = (inicio_dia - timedelta(days=6))  # últimos 7 dias
    inicio_mes = agora.replace(
        day=1, hour=0, minute=0, second=0, microsecond=0)

    # KPIs básicos
    total_fichas = FichaPasse.query.count()

    fichas_hoje = (
        FichaPasse.query
        .filter(FichaPasse.created_at >= inicio_dia)
        .filter(FichaPasse.created_at <= fim_dia)
        .count()
    )

    fichas_semana = (
        FichaPasse.query
        .filter(FichaPasse.created_at >= inicio_semana)
        .filter(FichaPasse.created_at <= fim_dia)
        .count()
    )

    fichas_mes = (
        FichaPasse.query
        .filter(FichaPasse.created_at >= inicio_mes)
        .filter(FichaPasse.created_at <= fim_dia)
        .count()
    )

    # ------- Gráfico 1: últimos 7 dias (linha/coluna) -------

    inicio_7d = inicio_semana  # já calculado
    rows_dias = (
        db.session.query(
            func.date(FichaPasse.created_at).label("dia"),
            func.count(FichaPasse.id)
        )
        .filter(FichaPasse.created_at >= inicio_7d)
        .group_by(func.date(FichaPasse.created_at))
        .order_by(func.date(FichaPasse.created_at))
        .all()
    )

    # monta dicionário dia -> count
    mapa_dias = {r.dia: r[1] for r in rows_dias}

    labels_dias = []
    valores_dias = []

    # garante todos os 7 dias no eixo X
    for i in range(6, -1, -1):
        dia = (inicio_7d + timedelta(days=i)).date()
        labels_dias.append(dia.strftime("%d/%m"))
        valores_dias.append(mapa_dias.get(dia, 0))

    # ------- Gráfico 2: distribuição por serviço (pizza) -------

    form_tmp = FichaPasseForm()
    servicos_dict = dict(form_tmp.servico.choices)

    rows_servicos = (
        db.session.query(
            FichaPasse.servico,
            func.count(FichaPasse.id)
        )
        .group_by(FichaPasse.servico)
        .all()
    )

    labels_servicos = []
    valores_servicos = []

    for codigo, qtd in rows_servicos:
        label_legivel = servicos_dict.get(codigo, codigo or "Não informado")
        labels_servicos.append(label_legivel)
        valores_servicos.append(qtd)

    return render_template(
        "laranjeiras/dashboard.html",
        total_fichas=total_fichas,
        fichas_hoje=fichas_hoje,
        fichas_semana=fichas_semana,
        fichas_mes=fichas_mes,
        labels_dias=labels_dias,
        valores_dias=valores_dias,
        labels_servicos=labels_servicos,
        valores_servicos=valores_servicos,
    )


@app.route("/passe/novo", methods=["GET", "POST"])
@login_required
def novo_passe():
    form = FichaPasseForm()
    if form.validate_on_submit():
        ficha = FichaPasse(
            nome=form.nome.data,
            endereco=form.endereco.data,
            complemento=form.complemento.data,
            bairro=form.bairro.data,
            telefone=form.telefone.data,
            servico=form.servico.data,
            ja_conhecia=(form.ja_conhecia.data == "sim"),
            quer_conhecer_mais=(form.quer_conhecer_mais.data == "sim"),
            usuario_id=current_user.id,
        )
        db.session.add(ficha)
        db.session.commit()
        flash("Ficha registrada com sucesso!", "success")
        return redirect(url_for("novo_passe"))
    return render_template("laranjeiras/passe_form.html", form=form)


@app.route("/passe")
@login_required
def lista_passe():
    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "", type=str)
    servico = request.args.get("servico", "", type=str)
    data_inicio = request.args.get("data_inicio", "", type=str)
    data_fim = request.args.get("data_fim", "", type=str)

    query = FichaPasse.query

    if search:
        like = f"%{search}%"
        query = query.filter(
            db.or_(
                FichaPasse.nome.ilike(like),
                FichaPasse.telefone.ilike(like),
                FichaPasse.bairro.ilike(like),
            )
        )

    if servico:
        query = query.filter(FichaPasse.servico == servico)

    # filtro de data por created_at (somente dia)
    if data_inicio:
        try:
            dt_ini = datetime.strptime(data_inicio, "%Y-%m-%d")
            query = query.filter(FichaPasse.created_at >= dt_ini)
        except ValueError:
            pass

    if data_fim:
        try:
            # inclui o final do dia
            dt_fim = datetime.strptime(data_fim, "%Y-%m-%d")
            dt_fim = dt_fim.replace(hour=23, minute=59, second=59)
            query = query.filter(FichaPasse.created_at <= dt_fim)
        except ValueError:
            pass

    query = query.order_by(FichaPasse.created_at.desc())
    fichas = query.paginate(page=page, per_page=20)

    # dicionário de serviços (value -> label)
    form_tmp = FichaPasseForm()
    servicos_dict = dict(form_tmp.servico.choices)

    return render_template(
        "laranjeiras/passe_lista.html",
        fichas=fichas,
        servicos_dict=servicos_dict,
    )


@app.route("/passe/exportar-excel")
@login_required
def exportar_passe_excel():
    search = request.args.get("search", "", type=str)
    servico = request.args.get("servico", "", type=str)
    data_inicio = request.args.get("data_inicio", "", type=str)
    data_fim = request.args.get("data_fim", "", type=str)

    query = FichaPasse.query

    if search:
        like = f"%{search}%"
        query = query.filter(
            db.or_(
                FichaPasse.nome.ilike(like),
                FichaPasse.telefone.ilike(like),
                FichaPasse.bairro.ilike(like),
            )
        )

    if servico:
        query = query.filter(FichaPasse.servico == servico)

    if data_inicio:
        try:
            dt_ini = datetime.strptime(data_inicio, "%Y-%m-%d")
            query = query.filter(FichaPasse.created_at >= dt_ini)
        except ValueError:
            pass

    if data_fim:
        try:
            dt_fim = datetime.strptime(data_fim, "%Y-%m-%d")
            dt_fim = dt_fim.replace(hour=23, minute=59, second=59)
            query = query.filter(FichaPasse.created_at <= dt_fim)
        except ValueError:
            pass

    registros = query.order_by(FichaPasse.created_at.desc()).all()

    # monta Excel com openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Fichas"

    ws.append([
        "ID", "Nome", "Telefone", "Endereço", "Complemento",
        "Bairro", "Serviço", "Já conhecia?", "Quer conhecer mais?", "Data"
    ])

    form_tmp = FichaPasseForm()
    servicos_dict = dict(form_tmp.servico.choices)

    for f in registros:
        ws.append([
            f.id,
            f.nome,
            f.telefone,
            f.endereco,
            f.complemento or "",
            f.bairro or "",
            servicos_dict.get(f.servico, f.servico),
            "Sim" if f.ja_conhecia else "Não",
            "Sim" if f.quer_conhecer_mais else "Não",
            f.created_at.strftime("%d/%m/%Y %H:%M"),
        ])

    file_stream = BytesIO()
    wb.save(file_stream)
    file_stream.seek(0)

    return send_file(
        file_stream,
        as_attachment=True,
        download_name="fichas_passe.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.route("/criar-admin")
def criar_admin():
    if User.query.first():
        return "Já existe usuário criado.", 400

    admin = User(nome="Admin", email="admin@teste.com")
    admin.set_password("123456")
    db.session.add(admin)
    db.session.commit()
    return "Usuário admin criado!"
