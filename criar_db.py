from src import database, bcrypt, app
from src.models import User

with app.app_context():
    senha = bcrypt.generate_password_hash("admin123").decode('utf-8')

    novo_admin = User(
        nome="Administrador",
        email="admin@conferencia.com",
        senha=senha,
        iap_local="Central",
        telefone="(92) 98623-4547",
        funcao_user_id=1  # DIRETOR
    )

    database.session.add(novo_admin)
    database.session.commit()
