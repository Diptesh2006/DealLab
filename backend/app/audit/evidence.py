from backend.app.db.connection import get_connection


def record_event(entity_type: str, entity_id: int, action: str, evidence: str) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO audit_events (entity_type, entity_id, action, evidence)
            VALUES (?, ?, ?, ?)
            """,
            (entity_type, entity_id, action, evidence),
        )
