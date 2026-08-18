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
        parent_id=form.parent_id.data or None,
        order=form.order.data or 0,
    )
    database.session.add(link)
    log_audit(actor_user_id=actor_user_id, action="cms_nav_link_created", details=f"label={link.label}")
    database.session.commit()
    return link


def update_nav_link(link: NavLink, form, actor_user_id) -> NavLink:
    link.label = form.label.data.strip()
    link.url = (form.url.data or "").strip() or None
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
