from src import app, database
from src.models import Registration, AppSetting, AuditLog


def run_migration():
    with app.app_context():
        print("Iniciando migração de parcelamentos (4x -> 2x)...")

        # 1. Localizar inscrições em 4x
        regs_4x = Registration.query.filter(Registration.installments == 4).all()
        confirmed = [r for r in regs_4x if r.status == "CONFIRMADA"]
        to_update = [r for r in regs_4x if r.status != "CONFIRMADA"]

        print(f"\nTotal de inscrições em 4x encontradas: {len(regs_4x)}")
        print(f"- Confirmadas (permanecem em 4x): {len(confirmed)}")
        for r in confirmed:
            print(f"   [MANTIDO 4x] ID {r.id}: {r.full_name} ({r.status})")

        print(f"\n- Não confirmadas a serem atualizadas para 2x: {len(to_update)}")
        updated_ids = []
        for r in to_update:
            print(f"   [ATUALIZANDO 4x -> 2x] ID {r.id}: {r.full_name} ({r.status})")
            r.installments = 2
            updated_ids.append(r.id)

            audit = AuditLog(
                actor_user_id=None,
                action="adjust_installments_4x_to_2x",
                details=(
                    f"Registro ID {r.id} ({r.full_name}) teve parcelas alteradas de 4x para 2x "
                    f"devido a status '{r.status}' e proximidade do evento."
                ),
            )
            database.session.add(audit)

        # 2. Salvar lista de IDs em AppSetting
        if updated_ids:
            setting_key = "downgraded_4x_to_2x_ids"
            setting = AppSetting.query.filter_by(key=setting_key).first()
            new_ids_str = ",".join(str(i) for i in updated_ids)

            if setting:
                # Se já havia algum, unifica
                existing_ids = [int(x.strip()) for x in setting.value.split(",") if x.strip().isdigit()]
                merged = sorted(list(set(existing_ids + updated_ids)))
                setting.value = ",".join(str(i) for i in merged)
            else:
                setting = AppSetting(key=setting_key, value=new_ids_str)
                database.session.add(setting)

        database.session.commit()
        print(f"\nSucesso! {len(to_update)} inscrições foram atualizadas para 2x no banco de dados.")
        print(f"IDs salvos em AppSetting: {updated_ids}")


if __name__ == "__main__":
    run_migration()
