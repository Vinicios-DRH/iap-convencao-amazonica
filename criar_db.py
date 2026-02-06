from src import app, database
from src.models import User, Role, AuditLog

EMAIL_SUPER = "7519957@gmail.com".strip().lower()

with app.app_context():
    user = User.query.filter_by(email=EMAIL_SUPER).first()
    if not user:
        raise SystemExit(
            f"Usuário não encontrado: {EMAIL_SUPER} (crie pelo /inscricao primeiro)")

    role_super = Role.query.filter_by(name="SUPER").first()
    if not role_super:
        raise SystemExit(
            "Role SUPER não existe. Rode primeiro: python seed_roles.py (ou flask seed_roles)")

    if role_super not in user.roles:
        user.roles.append(role_super)

    database.session.add(AuditLog(
        actor_user_id=None,
        action="make_super",
        details=f"email={EMAIL_SUPER}"
    ))
    database.session.commit()

    print(f"OK! {EMAIL_SUPER} agora é SUPER.")
