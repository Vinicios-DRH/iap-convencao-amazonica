from flask import render_template

from src import app
from src.decorators import admin_required
from src.services.registration import get_kpis, get_recent_registrations


@app.route("/admin")
@admin_required
def admin_home():
    kpis = get_kpis()
    return render_template(
        "admin/home.html",
        kpi_total=kpis["total"],
        kpi_aguardando=kpis["aguardando"],
        kpi_confirmadas=kpis["confirmadas"],
        kpi_negadas=kpis["negadas"],
        kpi_pendentes_comprovante=kpis["pendentes_comprovante"],
        ultimas=get_recent_registrations(8),
    )
