from src import database
from src.controllers.slugify import gerar_slug
from src.models import Ministry, MinistryMember, MinistrySocialLink
from src.services.audit import log_audit
from src.services.portal.photos import track_image
from src.services.portal.sanitizer import sanitize_body
from src.services.portal.uploads import save_image_upload


def _slug_taken(slug: str, ignore_id: int | None) -> bool:
    query = Ministry.query.filter_by(slug=slug)
    if ignore_id:
        query = query.filter(Ministry.id != ignore_id)
    return query.first() is not None


def _unique_slug(name: str, ignore_id: int | None = None) -> str:
    base = gerar_slug(name) or "ministerio"
    slug = base
    suffix = 2
    while _slug_taken(slug, ignore_id):
        slug = f"{base}-{suffix}"
        suffix += 1
    return slug


def list_ministries():
    return Ministry.query.order_by(Ministry.name).all()


def list_active_ministries():
    return Ministry.query.filter_by(is_active=True).order_by(Ministry.name).all()


def get_active_ministry_by_slug(slug: str):
    return Ministry.query.filter_by(slug=slug, is_active=True).first()


def create_ministry(form, actor_user_id) -> Ministry:
    cover_image_key = None
    if form.cover_image.data:
        cover_image_key = save_image_upload(form.cover_image.data, folder="cms/ministries")

    name = form.name.data.strip()
    ministry = Ministry(
        name=name,
        slug=_unique_slug(name),
        description=sanitize_body(form.description.data),
        cover_image_key=cover_image_key,
    )
    database.session.add(ministry)
    log_audit(actor_user_id=actor_user_id, action="cms_ministry_created", details=f"name={name}")
    database.session.commit()

    if cover_image_key:
        track_image(cover_image_key, caption=f"Capa: {name}", album="Ministérios")

    return ministry


def update_ministry(ministry: Ministry, form, actor_user_id) -> Ministry:
    new_name = form.name.data.strip()
    if new_name != ministry.name:
        ministry.slug = _unique_slug(new_name, ignore_id=ministry.id)
    ministry.name = new_name
    ministry.description = sanitize_body(form.description.data)

    new_cover_key = None
    if form.cover_image.data:
        new_cover_key = save_image_upload(form.cover_image.data, folder="cms/ministries")
        ministry.cover_image_key = new_cover_key

    log_audit(actor_user_id=actor_user_id, action="cms_ministry_updated", details=f"ministry_id={ministry.id}")
    database.session.commit()

    if new_cover_key:
        track_image(new_cover_key, caption=f"Capa: {ministry.name}", album="Ministérios")

    return ministry


def set_ministry_active(ministry: Ministry, is_active: bool, actor_user_id) -> None:
    ministry.is_active = is_active
    log_audit(
        actor_user_id=actor_user_id,
        action="cms_ministry_visibility_changed",
        details=f"ministry_id={ministry.id} is_active={is_active}",
    )
    database.session.commit()


# ===== membros =====

def list_members(ministry: Ministry):
    return (
        MinistryMember.query
        .filter_by(ministry_id=ministry.id)
        .order_by(MinistryMember.order, MinistryMember.name)
        .all()
    )


def list_active_members(ministry: Ministry):
    return (
        MinistryMember.query
        .filter_by(ministry_id=ministry.id, is_active=True)
        .order_by(MinistryMember.order, MinistryMember.name)
        .all()
    )


def create_member(ministry: Ministry, form, actor_user_id) -> MinistryMember:
    member = MinistryMember(
        ministry_id=ministry.id,
        user_id=form.user_id.data or None,
        name=form.name.data.strip(),
        role=form.role.data.strip(),
        order=form.order.data or 0,
    )
    database.session.add(member)
    log_audit(
        actor_user_id=actor_user_id,
        action="cms_ministry_member_created",
        details=f"ministry_id={ministry.id} name={member.name}",
    )
    database.session.commit()
    return member


def update_member(member: MinistryMember, form, actor_user_id) -> MinistryMember:
    member.user_id = form.user_id.data or None
    member.name = form.name.data.strip()
    member.role = form.role.data.strip()
    member.order = form.order.data or 0

    log_audit(actor_user_id=actor_user_id, action="cms_ministry_member_updated", details=f"member_id={member.id}")
    database.session.commit()
    return member


def set_member_active(member: MinistryMember, is_active: bool, actor_user_id) -> None:
    member.is_active = is_active
    log_audit(
        actor_user_id=actor_user_id,
        action="cms_ministry_member_visibility_changed",
        details=f"member_id={member.id} is_active={is_active}",
    )
    database.session.commit()


# ===== redes sociais do ministério =====

def list_ministry_social_links(ministry: Ministry):
    return MinistrySocialLink.query.filter_by(ministry_id=ministry.id).order_by(MinistrySocialLink.order).all()


def list_active_ministry_social_links(ministry: Ministry):
    return (
        MinistrySocialLink.query
        .filter_by(ministry_id=ministry.id, is_active=True)
        .order_by(MinistrySocialLink.order)
        .all()
    )


def create_ministry_social_link(ministry: Ministry, form, actor_user_id) -> MinistrySocialLink:
    link = MinistrySocialLink(
        ministry_id=ministry.id,
        platform=form.platform.data,
        url=form.url.data.strip(),
        order=form.order.data or 0,
    )
    database.session.add(link)
    log_audit(
        actor_user_id=actor_user_id,
        action="cms_ministry_social_link_created",
        details=f"ministry_id={ministry.id} platform={link.platform}",
    )
    database.session.commit()
    return link


def update_ministry_social_link(link: MinistrySocialLink, form, actor_user_id) -> MinistrySocialLink:
    link.platform = form.platform.data
    link.url = form.url.data.strip()
    link.order = form.order.data or 0

    log_audit(actor_user_id=actor_user_id, action="cms_ministry_social_link_updated", details=f"link_id={link.id}")
    database.session.commit()
    return link


def set_ministry_social_link_active(link: MinistrySocialLink, is_active: bool, actor_user_id) -> None:
    link.is_active = is_active
    log_audit(
        actor_user_id=actor_user_id,
        action="cms_ministry_social_link_visibility_changed",
        details=f"link_id={link.id} is_active={is_active}",
    )
    database.session.commit()
