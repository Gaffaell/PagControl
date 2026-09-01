from app import models
from app.database import Base, SessionLocal, engine


def init_db() -> None:
    """Cria as tabelas se não existirem e semeia a régua padrão.
    Idempotente: seguro chamar toda vez que a API sobe (ver app/api.py lifespan)."""
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        if db.query(models.ConfiguracaoRegua).first() is None:
            db.add(models.ConfiguracaoRegua())
            db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
    print("Banco de dados inicializado: academia.db")
