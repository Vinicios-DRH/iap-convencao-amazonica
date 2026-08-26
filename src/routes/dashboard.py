from flask import render_template
from flask_login import current_user, login_required

from src import app
from src.services.pix import STATIC_PIX_PAYLOADS

CREDIT_PAYMENT_LINK = "https://link.infinitepay.io/senamarcos/VC1DLTAtUg-7QQz9P8uAx-200,09"


@app.route("/painel")
@login_required
def painel():
    return render_template(
        "convencao_jovem/dashboard/painel.html",
        reg=current_user.registration,
        lot_info="R$200,09",
        pix_prices={"v1": 200.09, "v2": 100.09, "v4": 50.09},
        credit_link=CREDIT_PAYMENT_LINK,
        pix_payloads=STATIC_PIX_PAYLOADS,
    )
