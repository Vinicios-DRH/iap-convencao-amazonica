from src import app, database
from src.models import Role, User, AppSetting


def upsert_role(name, **kwargs):
    r = Role.query.filter_by(name=name).first()
    if not r:
        r = Role(name=name, **kwargs)
        database.session.add(r)
    else:
        for k, v in kwargs.items():
            setattr(r, k, v)


def ensure_setting(key, value):
    s = AppSetting.query.filter_by(key=key).first()
    if not s:
        database.session.add(AppSetting(key=key, value=value))


with app.app_context():
    database.create_all()

    # Settings básicos pra não quebrar a landing
    ensure_setting("INSCRICOES_STATUS", "embreve")

    # Roles do seu seed_roles
    upsert_role("SUPER", is_super=True, can_access_admin=True,
                can_review_payments=True)
    upsert_role("ADMIN", is_super=False, can_access_admin=True,
                can_review_payments=True)
    upsert_role("REVISOR_PAGAMENTOS", is_super=False,
                can_access_admin=True, can_review_payments=True)

    # Super user inicial (ajusta email/senha aqui)
    email = "admin@teste.com"
    senha = "12345678"

    u = User.query.filter_by(email=email).first()
    if not u:
        u = User(email=email)
        u.set_password(senha)
        database.session.add(u)
        database.session.flush()  # garante id

    role_super = Role.query.filter_by(name="SUPER").first()
    if role_super and role_super not in u.roles:
        u.roles.append(role_super)

    database.session.commit()
    print("OK: SQLite app.db criado, roles criadas e SUPER pronto:",
          email, "senha:", senha)
