from flask import render_template, request

from src import app
from src.services.settings import inscricoes_status

_LANDING_VARIANTS = {
    "a": "convencao_jovem/site/landing_a.html",
    "b": "convencao_jovem/site/landing_b.html",
    "c": "convencao_jovem/site/landing_c.html",
    "d": "convencao_jovem/site/landing_d.html",
    "e": "convencao_jovem/site/landing_e.html",
    "f": "convencao_jovem/site/landing_f.html",
}


@app.route("/")
def landing():
    variant = (request.args.get("v") or "a").lower()
    template_name = _LANDING_VARIANTS.get(variant, "convencao_jovem/site/landing_a.html")
    return render_template(template_name, inscricoes_status=inscricoes_status())


@app.route("/quiz-licao")
def quiz_licao():
    return render_template("convencao_jovem/site/quiz_licao.html")
