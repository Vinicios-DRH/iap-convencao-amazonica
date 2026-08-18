from flask import Response, abort, jsonify
from flask_login import current_user, login_required

from src import app
from src.models import Registration
from src.services.pix import VALID_INSTALLMENT_OPTIONS, generate_dynamic_qr_png, get_static_payload


@app.route("/pix/qr/<int:n>")
@login_required
def pix_qr_n(n):
    reg = Registration.query.filter_by(user_id=current_user.id).first_or_404()

    if n not in VALID_INSTALLMENT_OPTIONS:
        abort(400)

    png_bytes = generate_dynamic_qr_png(reg.id, n, reg.lot_value_cents)
    return Response(png_bytes, mimetype="image/png")


@app.route("/pix/copia-cola/<int:n>")
@login_required
def pix_copia_cola(n):
    payload = get_static_payload(n)
    if not payload:
        abort(400)
    return jsonify({"payload": payload})
