import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config import Config

os.makedirs("logs", exist_ok=True)

IS_SQLITE = Config.DB_URL.startswith("sqlite")
connect_args = (
    {"check_same_thread": False} if IS_SQLITE else {"options": f"-csearch_path={Config.DB_SCHEMA}"}
)
engine = create_engine(
    Config.DB_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    pool_recycle=280,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def create_tables():
    import models  # noqa: F401 -- registers models on Base.metadata before create_all

    if not IS_SQLITE:
        from sqlalchemy import text

        with engine.begin() as conn:
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {Config.DB_SCHEMA}"))

    Base.metadata.create_all(bind=engine)
    _add_missing_help_columns()


def _add_missing_help_columns():
    """create_all never alters an existing table, so DBs created before
    block_code/indicator existed get them added here (existing rows -> B)."""
    from sqlalchemy import inspect, text

    existing = {c["name"] for c in inspect(engine).get_columns("poc_help_metadata")}
    with engine.begin() as conn:
        if "block_code" not in existing:
            conn.execute(text("ALTER TABLE poc_help_metadata ADD COLUMN block_code VARCHAR(30)"))
        if "indicator" not in existing:
            conn.execute(
                text("ALTER TABLE poc_help_metadata ADD COLUMN indicator VARCHAR(1) NOT NULL DEFAULT 'B'")
            )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
