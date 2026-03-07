# src/utils/texto.py
import re
import unicodedata


def normalizar_nome(texto: str) -> str:
    if not texto:
        return ""

    texto = texto.strip()
    texto = " ".join(texto.split())

    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = texto.lower()
    texto = re.sub(r"[^a-z0-9\s]", "", texto)
    texto = re.sub(r"\s+", " ", texto)

    return texto.strip()
