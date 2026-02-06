import re
from wtforms import ValidationError


def only_digits(s: str) -> str:
    return re.sub(r"\D", "", s or "")


def is_valid_cpf(cpf: str) -> bool:
    cpf = only_digits(cpf)

    if len(cpf) != 11:
        return False
    if cpf == cpf[0] * 11:
        return False

    # 1º dígito
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    d1 = (soma * 10) % 11
    d1 = 0 if d1 == 10 else d1

    # 2º dígito
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    d2 = (soma * 10) % 11
    d2 = 0 if d2 == 10 else d2

    return d1 == int(cpf[9]) and d2 == int(cpf[10])


def validate_cpf(form, field):
    if not is_valid_cpf(field.data):
        raise ValidationError("CPF inválido.")
