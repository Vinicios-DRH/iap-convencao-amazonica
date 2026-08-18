from decimal import ROUND_DOWN, Decimal
from io import BytesIO

import qrcode

from src.controllers.pix_emv import build_pix_payload

PIX_KEY = "17739576000178"
MERCHANT_NAME = "CONVENCAO AMAZONICA"
MERCHANT_CITY = "MANAUS"

VALID_INSTALLMENT_OPTIONS = (1, 2, 4)

STATIC_PIX_PAYLOADS = {
    1: "00020126500014BR.GOV.BCB.PIX0128convencaoamazonica@gmail.com5204000053039865406200.095802BR5925CONVENCAO REGIONAL AMAZON6006MANAUS622605224FUieu9XhujOBxKlhc4Fl0630428FD",
    2: "00020126500014BR.GOV.BCB.PIX0128convencaoamazonica@gmail.com5204000053039865406100.095802BR5925CONVENCAO REGIONAL AMAZON6006MANAUS622605226AO0b6MMKJb3EbxlKCgc5863046D2C",
    4: "00020126500014BR.GOV.BCB.PIX0128convencaoamazonica@gmail.com520400005303986540550.095802BR5925CONVENCAO REGIONAL AMAZON6006MANAUS62250521D1GCrRAr22LDxyydZOIt16304C231",
}


def calculate_installment_amount(lot_value_cents: int, installments: int) -> Decimal:
    lot = Decimal(lot_value_cents or 18000) / Decimal(100)

    # parcela inteira (ex: 180/2 = 90) + 0.09
    parcela = (lot / Decimal(installments)).quantize(Decimal("0"), rounding=ROUND_DOWN) + Decimal("0.09")
    return parcela.quantize(Decimal("0.00"))


def generate_dynamic_qr_png(registration_id: int, installments: int, lot_value_cents: int) -> bytes:
    amount = calculate_installment_amount(lot_value_cents, installments)
    txid = f"R{registration_id}N{installments}"[:25]  # alfanumérico

    payload = build_pix_payload(
        pix_key=PIX_KEY,
        merchant_name=MERCHANT_NAME,
        merchant_city=MERCHANT_CITY,
        amount=str(amount),
        txid=txid,
    )

    buffer = BytesIO()
    qrcode.make(payload).save(buffer, format="PNG")
    buffer.seek(0)
    return buffer.getvalue()


def get_static_payload(installments: int) -> str | None:
    return STATIC_PIX_PAYLOADS.get(installments)
