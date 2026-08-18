from src import database
from src.models import AuditLog


def log_audit(action: str, details: str | None = None, actor_user_id: int | None = None) -> None:
    database.session.add(AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        details=details,
    ))
