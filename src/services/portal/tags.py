from src import database
from src.controllers.slugify import gerar_slug
from src.models import Tag


def parse_tag_names(raw: str) -> list[str]:
    """'louvor, Jovens,  testemunho' -> ['louvor', 'Jovens', 'testemunho'] (sem duplicar por caixa)."""
    if not raw:
        return []
    seen = set()
    names = []
    for part in raw.split(","):
        name = part.strip()
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        names.append(name)
    return names


def get_or_create_tags(raw: str) -> list[Tag]:
    """Encontra pelo slug ou cria — evita 'Jovens' e 'jovens' virarem tags diferentes."""
    tags = []
    for name in parse_tag_names(raw):
        slug = gerar_slug(name)
        if not slug:
            continue
        tag = Tag.query.filter_by(slug=slug).first()
        if not tag:
            tag = Tag(name=name, slug=slug)
            database.session.add(tag)
            database.session.flush()
        tags.append(tag)
    return tags


def tags_to_text(tags) -> str:
    return ", ".join(t.name for t in tags)
