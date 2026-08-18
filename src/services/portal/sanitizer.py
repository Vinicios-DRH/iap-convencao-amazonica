import re

import bleach
from bleach.css_sanitizer import CSSSanitizer

ALLOWED_TAGS = [
    "p", "br", "strong", "em", "u", "h2", "h3", "h4",
    "ul", "ol", "li", "a", "img", "blockquote", "code",
]

# blocos que o Quill pode alinhar (justificar/centralizar/direita/esquerda)
_ALIGNABLE_TAGS = ["p", "h2", "h3", "h4", "li", "blockquote"]
_ALIGN_CLASSES = {"ql-align-center", "ql-align-right", "ql-align-justify"}


def _allow_align_attr(tag, name, value):
    # o Quill marca alinhamento ou com classe (ql-align-*) ou com style (text-align) —
    # aceita os dois formatos, mas nada além disso: classe só as 3 conhecidas, e o
    # conteúdo do style é filtrado à parte pelo CSSSanitizer (só permite text-align).
    if name == "class":
        return all(c in _ALIGN_CLASSES for c in value.split())
    if name == "style":
        return True
    return False


ALLOWED_ATTRS = {
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt"],
}
for _tag in _ALIGNABLE_TAGS:
    ALLOWED_ATTRS[_tag] = _allow_align_attr

_CSS_SANITIZER = CSSSanitizer(allowed_css_properties=["text-align"])

_SCRIPT_OR_STYLE_BLOCK = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)


def sanitize_body(html: str) -> str:
    # bleach remove a tag mas mantém o texto interno por padrão — errado pra script/style,
    # cujo "texto" é código, não conteúdo pra exibir. Remove o bloco inteiro antes de limpar o resto.
    without_scripts = _SCRIPT_OR_STYLE_BLOCK.sub("", html or "")
    return bleach.clean(
        without_scripts,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        css_sanitizer=_CSS_SANITIZER,
        strip=True,
    )
