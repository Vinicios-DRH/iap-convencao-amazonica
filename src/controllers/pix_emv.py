# src/controllers/pix_emv.py
import re


def _tlv(tag: str, value: str) -> str:
    ln = f"{len(value):02d}"
    return f"{tag}{ln}{value}"


def _crc16_ccitt(payload: str) -> str:
    crc = 0xFFFF
    for ch in payload.encode("utf-8"):
        crc ^= ch << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return f"{crc:04X}"


def build_pix_payload(
    pix_key: str,
    merchant_name: str = "CONVENCAO AMAZONICA",
    merchant_city: str = "MANAUS",
    amount: float | None = None,
    txid: str = "***",
) -> str:
    # ✅ Para CNPJ, deixa SOMENTE números (14 dígitos)
    key = re.sub(r"\D", "", pix_key).strip()

    # 00 = Payload Format Indicator
    pfi = "000201"

    # 01 = Point of Initiation Method (11 = static)
    pim = _tlv("01", "11")

    # 26 = Merchant Account Information (GUI + chave)
    gui = _tlv("00", "br.gov.bcb.pix")
    chave = _tlv("01", key)
    mai = _tlv("26", gui + chave)

    # 52 = MCC, 53 = Currency (986 BRL)
    mcc = _tlv("52", "0000")
    moeda = _tlv("53", "986")

    # 54 = Amount (opcional)
    valor = _tlv("54", f"{amount:.2f}") if amount is not None else ""

    # 58 = Country, 59 = Merchant Name, 60 = Merchant City
    pais = _tlv("58", "BR")
    nome = _tlv("59", merchant_name[:25].upper())
    cidade = _tlv("60", merchant_city[:15].upper())

    # 62 = Additional Data Field Template (TxID)
    # ✅ TxID max 25 chars
    safe_txid = (txid or "***")[:25]
    add = _tlv("62", _tlv("05", safe_txid))

    payload = pfi + pim + mai + mcc + moeda + valor + pais + nome + cidade + add

    # 63 = CRC
    payload_crc = payload + "6304"
    crc = _crc16_ccitt(payload_crc)
    return payload_crc + crc
