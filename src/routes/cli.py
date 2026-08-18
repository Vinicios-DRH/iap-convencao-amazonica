from src import app, database
from src.models import Role, User
from src.services.audit import log_audit


@app.cli.command("seed_roles")
def seed_roles():
    """
    flask seed_roles
    """
    def upsert(name, **kwargs):
        role = Role.query.filter_by(name=name).first()
        if not role:
            role = Role(name=name, **kwargs)
            database.session.add(role)
        else:
            for key, value in kwargs.items():
                setattr(role, key, value)

    upsert("SUPER", is_super=True, can_access_admin=True, can_review_payments=True)
    upsert("ADMIN", is_super=False, can_access_admin=True, can_review_payments=True)
    upsert("REVISOR_PAGAMENTOS", is_super=False, can_access_admin=True, can_review_payments=True)
    upsert("GESTOR_CMS", is_super=False, can_access_admin=False, can_review_payments=False)
    database.session.commit()
    print("Roles criadas/atualizadas.")


@app.cli.command("create_cms_tables")
def create_cms_tables():
    """
    flask create_cms_tables

    Cria só as tabelas novas do CMS (cms_authors, cms_posts, cms_downloads,
    cms_photos, cms_nav_links) sem tocar nas tabelas existentes — database.create_all()
    nunca altera uma tabela que já existe, só cria as que faltam.
    """
    database.create_all()
    print("Tabelas do CMS criadas/confirmadas.")


@app.cli.command("make_super")
def make_super():
    """
    Uso:
      flask make_super admin@teste.com
    """
    import sys

    if len(sys.argv) < 3:
        print("Uso: flask make_super email@dominio.com")
        return

    email = sys.argv[2].strip().lower()
    user = User.query.filter_by(email=email).first()
    if not user:
        print(f"Usuário não encontrado: {email}")
        return

    role_super = Role.query.filter_by(name="SUPER").first()
    if not role_super:
        print("Role SUPER não existe. Rode: flask seed_roles")
        return

    if role_super not in user.roles:
        user.roles.append(role_super)

    log_audit(action="cli_make_super", details=f"email={email}")
    database.session.commit()

    print(f"OK! {email} agora é SUPER.")
