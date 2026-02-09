import re
from decimal import Decimal, InvalidOperation


def _tlv(tag: str, value: str) -> str:
    # PIX usa comprimento em bytes (UTF-8) – mais compatível
    ln = f"{len(value.encode('utf-8')):02d}"
    return f"{tag}{ln}{value}"


def _crc16_ccitt(payload: str) -> str:
    crc = 0xFFFF
    for char in payload:
        crc ^= ord(char) << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc = crc << 1
            crc &= 0xFFFF
    return f"{crc:04X}"


def _format_amount(amount) -> str | None:
    if amount is None:
        return None
    try:
        s = str(amount).strip().replace(",", ".")
        d = Decimal(s).quantize(Decimal("0.00"))
        return format(d, "f")  # "90.09"
    except (InvalidOperation, ValueError):
        return None


def build_pix_payload(
    pix_key: str,
    merchant_name: str = "CONVENCAO_AMAZONICA",
    merchant_city: str = "MANAUS",
    amount=None,
    txid: str = "***",
) -> str:
    # Limpa a chave (apenas números se for CPF/CNPJ)
    key = re.sub(r"\D", "", pix_key).strip()

    # Payload Format Indicator e Merchant Account Information
    pfi = "000201"
    # O campo 26 (MAI) precisa ser montado com precisão
    gui = _tlv("00", "br.gov.bcb.pix")
    chave = _tlv("01", key)
    mai = _tlv("26", gui + chave)

    mcc = _tlv("52", "0000")
    moeda = _tlv("53", "986")

    # Valor: Nubank exige ponto decimal e duas casas
    amt = _format_amount(amount)
    valor = _tlv("54", amt) if amt else ""

    pais = _tlv("58", "BR")

    # Nome e Cidade: Sem caracteres especiais e em maiúsculas
    # O Nubank às vezes falha com espaços. Tente "CONVENCAOAMAZONICA" se persistir.
    nome = _tlv("59", merchant_name[:25].upper())
    cidade = _tlv("60", merchant_city[:15].upper())

    # Campo 62: O TXID não pode ser vazio. Se não tiver, use obrigatoriamente ***
    safe_txid = re.sub(r"[^A-Za-z0-9]", "", txid) if txid != "***" else "***"
    if not safe_txid:
        safe_txid = "***"

    # Montagem do campo adicional
    campo_62 = _tlv("05", safe_txid)
    add = _tlv("62", campo_62)

    # Concatenação na ordem correta do manual do BACEN
    payload = pfi + mai + mcc + moeda + valor + pais + nome + cidade + add

    # O 6304 indica que o próximo dado é o CRC de 4 dígitos
    payload_com_final_crc = payload + "6304"

    crc_gerado = _crc16_ccitt(payload_com_final_crc)

    return payload_com_final_crc + crc_gerado
