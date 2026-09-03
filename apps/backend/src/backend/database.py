import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# .env.local é gerado automaticamente pelo CLI da Neon (neon link/config);
# .env é para overrides manuais. Carregamos os dois, .env por último para
# poder sobrescrever o que vier da Neon se necessário.
load_dotenv(".env.local")
load_dotenv(".env")

# Sem DATABASE_URL configurada (ambiente novo, sem Neon linkado), cai para
# um SQLite local — assim o projeto roda de primeira sem depender de nuvem.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./academia.db")

# A Neon (e a maioria dos provedores) entrega a URL como "postgresql://",
# que o SQLAlchemy interpreta com o driver psycopg2 por padrão. Instalamos
# psycopg (v3), então normalizamos o esquema para forçar esse driver.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

# check_same_thread só é necessário/válido para SQLite (permite usar a mesma
# conexão em threads diferentes, como o FastAPI faz por padrão).
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """Dependency do FastAPI: abre uma sessão por requisição e garante o close."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
