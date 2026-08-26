from src import database
from src.models import NavLink
from src.services.audit import log_audit


def list_top_level_links():
    return NavLink.query.filter_by(parent_id=None).order_by(NavLink.order).all()


def list_active_top_level_links():
    return NavLink.query.filter_by(parent_id=None, is_active=True).order_by(NavLink.order).all()


def list_parent_options():
    """Só links de topo podem virar pai — garante no máximo 1 nível de aninhamento."""
    return NavLink.query.filter_by(parent_id=None).order_by(NavLink.order).all()


def create_nav_link(form, actor_user_id) -> NavLink:
    link = NavLink(
        label=form.label.data.strip(),
        url=(form.url.data or "").strip() or None,
        page_id=form.page_id.data or None,
        parent_id=form.parent_id.data or None,
        order=form.order.data or 0,
    )
    database.session.add(link)
    log_audit(actor_user_id=actor_user_id, action="cms_nav_link_created", details=f"label={link.label}")
    database.session.commit()
    return link


def create_dropdown(label: str, order: int, children: list[dict], actor_user_id) -> NavLink:
    """Cria o item de topo (dropdown) e seus submenus juntos, numa tacada só -- em vez de
    criar o pai, salvar, e só depois voltar pra criar cada filho separado.

    `children` é uma lista de dicts com label/page_id/url/order; linhas sem label são
    ignoradas (sobra de linha vazia deixada no formulário)."""
    parent = NavLink(label=label.strip(), order=order or 0)
    database.session.add(parent)
    database.session.flush()  # garante parent.id antes de criar os filhos

    created = 0
    for child in children:
        child_label = (child.get("label") or "").strip()
        if not child_label:
            continue
        database.session.add(NavLink(
            label=child_label,
            url=(child.get("url") or "").strip() or None,
            page_id=child.get("page_id") or None,
            parent_id=parent.id,
            order=child.get("order") or 0,
        ))
        created += 1

    log_audit(
        actor_user_id=actor_user_id,
        action="cms_nav_dropdown_created",
        details=f"label={parent.label} children={created}",
    )
    database.session.commit()
    return parent


def update_nav_link(link: NavLink, form, actor_user_id) -> NavLink:
    link.label = form.label.data.strip()
    link.url = (form.url.data or "").strip() or None
    link.page_id = form.page_id.data or None
    link.order = form.order.data or 0

    new_parent_id = form.parent_id.data or None
    if new_parent_id == link.id or link.children:
        # nunca pode ser pai de si mesmo, nem virar filho se já tem filhos (1 nível só)
        new_parent_id = None
    link.parent_id = new_parent_id

    log_audit(actor_user_id=actor_user_id, action="cms_nav_link_updated", details=f"nav_link_id={link.id}")
    database.session.commit()
    return link


def set_nav_link_active(link: NavLink, is_active: bool, actor_user_id) -> None:
    link.is_active = is_active
    log_audit(
        actor_user_id=actor_user_id,
        action="cms_nav_link_visibility_changed",
        details=f"nav_link_id={link.id} is_active={is_active}",
    )
    database.session.commit()
