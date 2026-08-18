from src import database
from src.models import SocialLink
from src.services.audit import log_audit

# ícones SVG inline (24x24, monocromático via currentColor) — sem CDN de biblioteca
# de ícones só pra um punhado de logos fixas que nunca mudam.
PLATFORM_ICONS = {
    "instagram": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="2" width="20" height="20" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r="1"/></svg>',
    "facebook": '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M13.5 21v-8h2.7l.4-3.2h-3.1V7.7c0-.9.3-1.6 1.6-1.6h1.7V3.2C16.5 3.1 15.4 3 14.2 3c-2.6 0-4.4 1.6-4.4 4.5v2.3H7v3.2h2.8V21h3.7z"/></svg>',
    "youtube": '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M21.6 7.2a2.7 2.7 0 0 0-1.9-1.9C18 5 12 5 12 5s-6 0-7.7.3A2.7 2.7 0 0 0 2.4 7.2 28 28 0 0 0 2 12a28 28 0 0 0 .4 4.8 2.7 2.7 0 0 0 1.9 1.9C6 19 12 19 12 19s6 0 7.7-.3a2.7 2.7 0 0 0 1.9-1.9A28 28 0 0 0 22 12a28 28 0 0 0-.4-4.8zM10 15V9l5.2 3-5.2 3z"/></svg>',
    "whatsapp": '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2zm0 18a8 8 0 0 1-4.1-1.1l-.3-.2-3 .8.8-2.9-.2-.3A8 8 0 1 1 12 20zm4.4-6c-.2-.1-1.4-.7-1.6-.8-.2-.1-.4-.1-.5.1l-.8.9c-.1.2-.3.2-.5.1-.7-.3-1.5-.8-2.1-1.5-.5-.6-.8-1-.9-1.2-.1-.2 0-.3.1-.4l.4-.5c.1-.1.1-.3.1-.4 0-.1-.5-1.3-.7-1.7-.2-.5-.4-.4-.5-.4h-.4c-.2 0-.4.1-.6.3-.2.2-.8.8-.8 1.9s.8 2.2.9 2.4c.1.2 1.6 2.5 4 3.5.6.2 1 .4 1.3.5.6.2 1.1.1 1.5 0 .5-.1 1.4-.6 1.6-1.1.2-.5.2-1 .1-1.1l-.4-.2z"/></svg>',
    "tiktok": '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M16.5 2h-3v13.6a2.7 2.7 0 1 1-2-2.6V9.8a6 6 0 1 0 5 5.9V9.2a7.6 7.6 0 0 0 4 1.2V7.1a4.6 4.6 0 0 1-4-3.6V2z"/></svg>',
    "x": '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M3 3l7.4 9.6L3.3 21H6l5.8-6.7L16.5 21H21l-7.8-10.1L20.7 3H18l-5.4 6.2L8 3H3z"/></svg>',
    "outro": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 13a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1 1"/><path d="M14 11a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1-1"/></svg>',
}


def get_icon(platform: str) -> str:
    return PLATFORM_ICONS.get(platform, PLATFORM_ICONS["outro"])


def list_social_links():
    return SocialLink.query.order_by(SocialLink.order).all()


def list_active_social_links():
    return SocialLink.query.filter_by(is_active=True).order_by(SocialLink.order).all()


def create_social_link(form, actor_user_id) -> SocialLink:
    link = SocialLink(
        platform=form.platform.data,
        url=form.url.data.strip(),
        order=form.order.data or 0,
    )
    database.session.add(link)
    log_audit(actor_user_id=actor_user_id, action="cms_social_link_created", details=f"platform={link.platform}")
    database.session.commit()
    return link


def update_social_link(link: SocialLink, form, actor_user_id) -> SocialLink:
    link.platform = form.platform.data
    link.url = form.url.data.strip()
    link.order = form.order.data or 0

    log_audit(actor_user_id=actor_user_id, action="cms_social_link_updated", details=f"social_link_id={link.id}")
    database.session.commit()
    return link


def set_social_link_active(link: SocialLink, is_active: bool, actor_user_id) -> None:
    link.is_active = is_active
    log_audit(
        actor_user_id=actor_user_id,
        action="cms_social_link_visibility_changed",
        details=f"social_link_id={link.id} is_active={is_active}",
    )
    database.session.commit()
