from flask import request, send_file
from flask_login import login_required

from src import app
from src.decorators import admin_required
from src.services.reports.registrations_xlsx import build_registrations_workbook


@app.route("/admin/relatorio-inscritos.xlsx")
@login_required
@admin_required
def admin_relatorio_inscritos_xlsx():
    """
    Relatório completo em Excel.
    Suporta filtros opcionais via querystring:
      - ?status=CONFIRMADA
      - ?payment_type=pix
      - ?from=2026-02-01&to=2026-02-10 (YYYY-MM-DD)
    """
    workbook = build_registrations_workbook(
        status=(request.args.get("status") or "").strip(),
        payment_type=(request.args.get("payment_type") or "").strip(),
        date_from=(request.args.get("from") or "").strip(),
        date_to=(request.args.get("to") or "").strip(),
    )
    return send_file(
        workbook,
        as_attachment=True,
        download_name="relatorio_inscritos_completo.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
