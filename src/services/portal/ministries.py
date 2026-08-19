from src import database
from src.controllers.slugify import gerar_slug
from src.models import Ministry, MinistryMandate, MinistryMandateMember, MinistrySocialLink
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


# ===== mandatos de liderança =====
# Cada troca de liderança (a cada ~4 anos) vira um mandato novo em vez de sobrescrever o
# anterior -- o antigo fica no painel como histórico, só o mandato is_current=True aparece
# pro público (ver list_active_members, chamada por src/routes/portal/public.py).

def list_mandates(ministry: Ministry):
    return MinistryMandate.query.filter_by(ministry_id=ministry.id).order_by(MinistryMandate.created_at.desc()).all()


def get_current_mandate(ministry: Ministry):
    return MinistryMandate.query.filter_by(ministry_id=ministry.id, is_current=True).first()


def create_mandate(ministry: Ministry, form, actor_user_id) -> MinistryMandate:
    mandate = MinistryMandate(ministry_id=ministry.id, label=form.label.data.strip())
    database.session.add(mandate)
    log_audit(
        actor_user_id=actor_user_id,
        action="cms_ministry_mandate_created",
        details=f"ministry_id={ministry.id} label={mandate.label}",
    )
    database.session.commit()
    return mandate


def set_current_mandate(ministry: Ministry, mandate: MinistryMandate, actor_user_id) -> None:
    MinistryMandate.query.filter_by(ministry_id=ministry.id).update({"is_current": False})
    mandate.is_current = True
    log_audit(
        actor_user_id=actor_user_id,
        action="cms_ministry_mandate_set_current",
        details=f"ministry_id={ministry.id} mandate_id={mandate.id}",
    )
    database.session.commit()


# ===== membros (dentro de um mandato) =====

def list_members(mandate: MinistryMandate):
    return (
        MinistryMandateMember.query
        .filter_by(mandate_id=mandate.id)
        .order_by(MinistryMandateMember.order, MinistryMandateMember.name)
        .all()
    )


def list_active_members(ministry: Ministry):
    """Membros do mandato ATUAL do ministério -- é o que a página pública mostra.
    Sem mandato atual ainda cadastrado, ou se as tabelas de mandato ainda não existirem
    (deploy antes de rodar o SQL no Supabase), degrada pra lista vazia em vez de derrubar
    a página do ministério."""
    try:
        mandate = get_current_mandate(ministry)
        if not mandate:
            return []
        return (
            MinistryMandateMember.query
            .filter_by(mandate_id=mandate.id, is_active=True)
            .order_by(MinistryMandateMember.order, MinistryMandateMember.name)
            .all()
        )
    except Exception:
        database.session.rollback()
        return []


def create_member(mandate: MinistryMandate, form, actor_user_id) -> MinistryMandateMember:
    photo_key = None
    if getattr(form, "photo", None) and form.photo.data:
        photo_key = save_image_upload(form.photo.data, folder="cms/ministries/mandatos")

    member = MinistryMandateMember(
        mandate_id=mandate.id,
        user_id=form.user_id.data or None,
        name=form.name.data.strip(),
        role=form.role.data.strip(),
        photo_key=photo_key,
        order=form.order.data or 0,
    )
    database.session.add(member)
    log_audit(
        actor_user_id=actor_user_id,
        action="cms_ministry_mandate_member_created",
        details=f"mandate_id={mandate.id} name={member.name}",
    )
    database.session.commit()

    if photo_key:
        track_image(photo_key, caption=f"{member.name} ({member.role})", album="Ministérios")

    return member


def update_member(member: MinistryMandateMember, form, actor_user_id) -> MinistryMandateMember:
    member.user_id = form.user_id.data or None
    member.name = form.name.data.strip()
    member.role = form.role.data.strip()
    member.order = form.order.data or 0

    new_photo_key = None
    if getattr(form, "photo", None) and form.photo.data:
        new_photo_key = save_image_upload(form.photo.data, folder="cms/ministries/mandatos")
        member.photo_key = new_photo_key

    log_audit(
        actor_user_id=actor_user_id,
        action="cms_ministry_mandate_member_updated",
        details=f"member_id={member.id}",
    )
    database.session.commit()

    if new_photo_key:
        track_image(new_photo_key, caption=f"{member.name} ({member.role})", album="Ministérios")

    return member


def set_member_active(member: MinistryMandateMember, is_active: bool, actor_user_id) -> None:
    member.is_active = is_active
    log_audit(
        actor_user_id=actor_user_id,
        action="cms_ministry_mandate_member_visibility_changed",
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
