from src import database
from src.models import AppSetting

FOOTER_ENDERECO_KEY = "PORTAL_FOOTER_ENDERECO"
FOOTER_TELEFONE_KEY = "PORTAL_FOOTER_TELEFONE"


def get_setting(key: str, default: str = "") -> str:
    setting = AppSetting.query.filter_by(key=key).first()
    return (setting.value if setting else default) or default


def set_setting(key: str, value: str) -> None:
    setting = AppSetting.query.filter_by(key=key).first()
    if not setting:
        setting = AppSetting(key=key, value=value)
        database.session.add(setting)
    else:
        setting.value = value


def inscricoes_status() -> str:
    return get_setting("INSCRICOES_STATUS", "embreve").strip().lower()


def get_footer_settings() -> dict:
    return {
        "endereco": get_setting(FOOTER_ENDERECO_KEY, ""),
        "telefone": get_setting(FOOTER_TELEFONE_KEY, ""),
    }


def update_footer_settings(endereco: str, telefone: str) -> None:
    set_setting(FOOTER_ENDERECO_KEY, (endereco or "").strip())
    set_setting(FOOTER_TELEFONE_KEY, (telefone or "").strip())
    database.session.commit()
