from datetime import datetime

from sqlalchemy import func, or_

from src import database
from src.models import Registration, User
from src.services.audit import log_audit

STATUS_AGUARDANDO = "AGUARDANDO_CONFIRMACAO"
STATUS_CONFIRMADA = "CONFIRMADA"
STATUS_NEGADA = "NEGADA"


def email_already_registered(email: str) -> bool:
    return User.query.filter_by(email=email).first() is not None


def create_registration(form) -> tuple[User, Registration]:
    user = User(email=form.email.data.strip().lower())
    user.set_password(form.password.data)

    registration = Registration(
        user=user,
        full_name=form.full_name.data.strip(),
        cpf=form.cpf.data.strip(),
        phone=form.phone.data.strip(),
        iap_local=form.iap_local.data.strip(),
        transport=form.transport.data,
        payment_type=form.payment_type.data,
        installments=int(form.installments.data),
        lot_name="LOTE_UNICO",
        lot_value_cents=20000,
        status=STATUS_AGUARDANDO,
        status_message="Aguardando confirmação do pagamento.",
        age=form.age.data,
        has_kids_u5=(form.has_kids_u5.data == "sim"),
        kids_u5_names=(form.kids_u5_names.data or "").strip() or None,
        is_church_member=(form.is_church_member.data == "sim"),
        agree_no_refund=bool(form.agree_no_refund.data),
    )

    database.session.add(user)
    database.session.add(registration)
    log_audit(action="user_signup_and_register", details=f"email={user.email}")
    database.session.commit()

    return user, registration


def review_registration(registration: Registration, decision: str, note: str, reviewer_id: int) -> None:
    registration.status = decision
    registration.status_message = (
        "Inscrição confirmada. Seja bem-vindo(a)!"
        if decision == STATUS_CONFIRMADA
        else "Inscrição negada. Entre em contato para ajustes."
    )
    registration.review_note = note or None
    registration.reviewed_by_user_id = reviewer_id
    registration.reviewed_at = datetime.utcnow()

    log_audit(
        actor_user_id=reviewer_id,
        action="review_registration",
        details=f"registration_id={registration.id} decision={decision}",
    )
    database.session.commit()


def search_registrations(status: str, query_text: str, page: int, per_page: int):
    query = Registration.query

    if status:
        query = query.filter(Registration.status == status)

    if query_text:
        like = f"%{query_text}%"
        query = query.filter(or_(
            Registration.full_name.ilike(like),
            Registration.cpf.ilike(like),
            Registration.phone.ilike(like),
            Registration.iap_local.ilike(like),
        ))

    query = query.order_by(Registration.created_at.desc())
    return query.paginate(page=page, per_page=per_page, error_out=False)


def _count_by_status(status: str) -> int:
    return (
        database.session.query(func.count(Registration.id))
        .filter(Registration.status == status)
        .scalar()
        or 0
    )


def get_kpis() -> dict:
    pendentes_comprovante = (
        database.session.query(func.count(Registration.id))
        .filter(
            Registration.payment_type == "pix",
            Registration.status == STATUS_AGUARDANDO,
            Registration.proof_file_path.isnot(None),
        )
        .scalar()
        or 0
    )

    return {
        "total": database.session.query(func.count(Registration.id)).scalar() or 0,
        "aguardando": _count_by_status(STATUS_AGUARDANDO),
        "confirmadas": _count_by_status(STATUS_CONFIRMADA),
        "negadas": _count_by_status(STATUS_NEGADA),
        "pendentes_comprovante": pendentes_comprovante,
    }


def get_recent_registrations(limit: int = 8):
    return (
        Registration.query
        .order_by(Registration.created_at.desc())
        .limit(limit)
        .all()
    )
