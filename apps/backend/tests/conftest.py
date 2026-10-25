import os

# Trava: nenhum teste conecta a um banco real (a Neon, por exemplo). Os testes
# criam o próprio SQLite temporário e substituem a dependência get_db.
os.environ["DATABASE_URL"] = "sqlite://"

import pytest
from backend import api
from backend.database import Base, get_db
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'teste.db'}")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine, autoflush=False)() as sessao:
        yield sessao
    engine.dispose()


@pytest.fixture
def client(db):
    def _get_db():
        yield db

    api.app.dependency_overrides[get_db] = _get_db
    # Sem `with`: o lifespan (que usaria o banco padrão) não é executado.
    yield TestClient(api.app)
    api.app.dependency_overrides.clear()
