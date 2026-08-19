from src import database
from src.models import BoardMandate, BoardMember
from src.services.audit import log_audit
from src.services.portal.photos import track_image
from src.services.portal.uploads import save_image_upload

# Mesmo padrão de mandato/histórico de src/services/portal/ministries.py, só que sem
# ministry_id -- a Diretoria da Convenção é única, não uma lista de entidades.


def list_mandates():
    return BoardMandate.query.order_by(BoardMandate.created_at.desc()).all()


def get_current_mandate():
    return BoardMandate.query.filter_by(is_current=True).first()


def create_mandate(form, actor_user_id) -> BoardMandate:
    mandate = BoardMandate(label=form.label.data.strip())
    database.session.add(mandate)
    log_audit(actor_user_id=actor_user_id, action="cms_board_mandate_created", details=f"label={mandate.label}")
    database.session.commit()
    return mandate


def set_current_mandate(mandate: BoardMandate, actor_user_id) -> None:
    BoardMandate.query.update({"is_current": False})
    mandate.is_current = True
    log_audit(actor_user_id=actor_user_id, action="cms_board_mandate_set_current", details=f"mandate_id={mandate.id}")
    database.session.commit()


def list_members(mandate: BoardMandate):
    return BoardMember.query.filter_by(mandate_id=mandate.id).order_by(BoardMember.order, BoardMember.name).all()


def list_current_members():
    """Membros do mandato ATUAL da Diretoria -- é o que a página pública mostra.
    Sem mandato atual ainda cadastrado, ou se as tabelas ainda não existirem (deploy antes
    de rodar o SQL no Supabase), degrada pra lista vazia em vez de derrubar a página."""
    try:
        mandate = get_current_mandate()
        if not mandate:
            return []
        return (
            BoardMember.query
            .filter_by(mandate_id=mandate.id, is_active=True)
            .order_by(BoardMember.order, BoardMember.name)
            .all()
        )
    except Exception:
        database.session.rollback()
        return []


def create_member(mandate: BoardMandate, form, actor_user_id) -> BoardMember:
    photo_key = None
    if form.photo.data:
        photo_key = save_image_upload(form.photo.data, folder="cms/diretoria")

    member = BoardMember(
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
        action="cms_board_member_created",
        details=f"mandate_id={mandate.id} name={member.name}",
    )
    database.session.commit()

    if photo_key:
        track_image(photo_key, caption=f"{member.name} ({member.role})", album="Diretoria")

    return member


def update_member(member: BoardMember, form, actor_user_id) -> BoardMember:
    member.user_id = form.user_id.data or None
    member.name = form.name.data.strip()
    member.role = form.role.data.strip()
    member.order = form.order.data or 0

    new_photo_key = None
    if form.photo.data:
        new_photo_key = save_image_upload(form.photo.data, folder="cms/diretoria")
        member.photo_key = new_photo_key

    log_audit(actor_user_id=actor_user_id, action="cms_board_member_updated", details=f"member_id={member.id}")
    database.session.commit()

    if new_photo_key:
        track_image(new_photo_key, caption=f"{member.name} ({member.role})", album="Diretoria")

    return member


def set_member_active(member: BoardMember, is_active: bool, actor_user_id) -> None:
    member.is_active = is_active
    log_audit(
        actor_user_id=actor_user_id,
        action="cms_board_member_visibility_changed",
        details=f"member_id={member.id} is_active={is_active}",
    )
    database.session.commit()
