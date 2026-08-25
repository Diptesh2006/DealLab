from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
import sqlite3

from backend.app.core.config import get_settings


def _sqlite_path() -> Path:
    database_url = get_settings().database_url
    if not database_url.startswith("sqlite:///"):
        raise ValueError("Only sqlite:/// DATABASE_URL values are supported in the MVP")
    return Path(database_url.replace("sqlite:///", "", 1))


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    path = _sqlite_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()
