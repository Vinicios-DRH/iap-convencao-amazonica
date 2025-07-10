from src import database, bcrypt, app
from src.models import User, ComprovantesPagamento

with app.app_context():
    usuarios = User.query.all()

    for usuario in usuarios:
        # Verifica se já existe um comprovante pra evitar duplicação
        if not ComprovantesPagamento.query.filter_by(id_user=usuario.id).first():
            comprovante = ComprovantesPagamento(
                id_user=usuario.id,
                status="PENDENTE",
                parcela="1ª PARCELA"
            )
            database.session.add(comprovante)

    database.session.commit()
    print("Comprovantes criados com sucesso!")
