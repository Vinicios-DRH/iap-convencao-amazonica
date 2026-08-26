from src import database
from src.models import Banner
from src.services.audit import log_audit
from src.services.portal.colors import extract_accent_color
from src.services.portal.photos import track_image
from src.services.portal.uploads import save_image_upload

# o banner ocupa a largura inteira da tela (ver .pt-banner-carousel em portal/home.html) --
# usa um teto maior que o padrão de imagens (1600px) pra não borrar em monitores grandes.
BANNER_MAX_DIMENSION = 1920


def list_banners():
    return Banner.query.order_by(Banner.order, Banner.created_at.desc()).all()


def list_active_banners():
    # a home publica chama isso direto -- se a tabela ainda nao existir (deploy antes
    # de rodar o SQL no Supabase), degrada pra lista vazia em vez de derrubar a home.
    try:
        return Banner.query.filter_by(is_active=True).order_by(Banner.order, Banner.created_at.desc()).all()
    except Exception:
        database.session.rollback()
        return []


def create_banner(form, actor_user_id) -> Banner:
    accent_color = extract_accent_color(form.image.data)
    image_key = save_image_upload(form.image.data, folder="cms/banners", max_dimension=BANNER_MAX_DIMENSION)

    banner = Banner(
        image_key=image_key,
        description=form.description.data.strip(),
        link_url=(form.link_url.data or "").strip() or None,
        order=form.order.data or 0,
        accent_color=accent_color,
    )
    database.session.add(banner)
    log_audit(actor_user_id=actor_user_id, action="cms_banner_created", details=f"description={banner.description}")
    database.session.commit()

    track_image(image_key, caption=banner.description, album="Banners")
    return banner


def update_banner(banner: Banner, form, actor_user_id) -> Banner:
    banner.description = form.description.data.strip()
    banner.link_url = (form.link_url.data or "").strip() or None
    banner.order = form.order.data or 0

    new_image_key = None
    if form.image.data:
        banner.accent_color = extract_accent_color(form.image.data)
        new_image_key = save_image_upload(form.image.data, folder="cms/banners", max_dimension=BANNER_MAX_DIMENSION)
        banner.image_key = new_image_key

    log_audit(actor_user_id=actor_user_id, action="cms_banner_updated", details=f"banner_id={banner.id}")
    database.session.commit()

    if new_image_key:
        track_image(new_image_key, caption=banner.description, album="Banners")
    return banner


def set_banner_active(banner: Banner, is_active: bool, actor_user_id) -> None:
    banner.is_active = is_active
    log_audit(
        actor_user_id=actor_user_id,
        action="cms_banner_visibility_changed",
        details=f"banner_id={banner.id} is_active={is_active}",
    )
    database.session.commit()
