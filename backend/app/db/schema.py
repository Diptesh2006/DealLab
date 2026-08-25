from backend.app.db.connection import get_connection


SCHEMA = """
CREATE TABLE IF NOT EXISTS contracts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT,
    raw_text TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS deal_terms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contract_id INTEGER NOT NULL,
    customer_name TEXT,
    annual_contract_value REAL NOT NULL,
    term_months INTEGER NOT NULL,
    discount_percent REAL NOT NULL,
    usage_commitment REAL NOT NULL,
    variable_cost_percent REAL NOT NULL,
    support_cost REAL NOT NULL,
    payment_terms_days INTEGER NOT NULL,
    auto_renewal INTEGER NOT NULL,
    liability_cap_multiplier REAL NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(contract_id) REFERENCES contracts(id)
);

CREATE TABLE IF NOT EXISTS simulation_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_terms_id INTEGER NOT NULL,
    health_score INTEGER NOT NULL,
    recommendation_summary TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(deal_terms_id) REFERENCES deal_terms(id)
);

CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    evidence TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def init_db() -> None:
    with get_connection() as connection:
        connection.executescript(SCHEMA)
