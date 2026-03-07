# src/routes_coracao.py
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from sqlalchemy.exc import IntegrityError

from src import database
from src.models import CoracaoNome
from src.utils.texto import normalizar_nome

bp_coracao = Blueprint("coracao", __name__, url_prefix="/coracao")

ADMIN_NOME = "vinicios"


@bp_coracao.route("/", methods=["GET"])
def index():
    return render_template(
        "coracao/index.html",
        is_admin=session.get("coracao_admin", False)
    )


@bp_coracao.route("/api/nomes", methods=["GET"])
def listar_nomes():
    nomes = CoracaoNome.query.order_by(CoracaoNome.created_at.asc()).all()

    return jsonify({
        "ok": True,
        "total": len(nomes),
        "nomes": [{"id": n.id, "nome": n.nome} for n in nomes]
    })


@bp_coracao.route("/api/nomes", methods=["POST"])
def adicionar_nome():
    data = request.get_json(silent=True) or {}
    nome = (data.get("nome") or "").strip()
    nome = " ".join(nome.split())

    if not nome:
        return jsonify({"ok": False, "mensagem": "Digite seu nome."}), 400

    nome_normalizado = normalizar_nome(nome)

    if not nome_normalizado:
        return jsonify({"ok": False, "mensagem": "Nome inválido."}), 400

    # Se for VINICIOS, ativa admin e não salva no banco
    if nome_normalizado == ADMIN_NOME:
        session["coracao_admin"] = True
        return jsonify({
            "ok": True,
            "admin": True,
            "mensagem": "Modo professor ativado."
        })

    existente = CoracaoNome.query.filter_by(
        nome_normalizado=nome_normalizado).first()
    if existente:
        return jsonify({"ok": False, "mensagem": "Esse nome já foi registrado."}), 409

    novo = CoracaoNome(
        nome=nome,
        nome_normalizado=nome_normalizado
    )

    try:
        database.session.add(novo)
        database.session.commit()
    except IntegrityError:
        database.session.rollback()
        return jsonify({"ok": False, "mensagem": "Esse nome já foi registrado."}), 409
    except Exception:
        database.session.rollback()
        return jsonify({"ok": False, "mensagem": "Erro ao salvar o nome."}), 500

    return jsonify({
        "ok": True,
        "admin": False,
        "mensagem": "Seu nome foi registrado com sucesso."
    })


@bp_coracao.route("/apresentacao", methods=["GET"])
def apresentacao():
    if not session.get("coracao_admin"):
        return redirect(url_for("coracao.index"))

    nomes = CoracaoNome.query.order_by(CoracaoNome.created_at.asc()).all()
    return render_template("coracao/apresentacao.html", nomes=nomes)


@bp_coracao.route("/limpar", methods=["POST"])
def limpar():
    if not session.get("coracao_admin"):
        return jsonify({"ok": False, "mensagem": "Acesso negado."}), 403

    try:
        CoracaoNome.query.delete()
        database.session.commit()
        return jsonify({"ok": True, "mensagem": "Nomes apagados com sucesso."})
    except Exception:
        database.session.rollback()
        return jsonify({"ok": False, "mensagem": "Erro ao limpar os nomes."}), 500


@bp_coracao.route("/sair-admin", methods=["POST"])
def sair_admin():
    session.pop("coracao_admin", None)
    return jsonify({"ok": True})
