import hashlib

from requests import session
from sqlalchemy.orm import Session

from backend import models, schemas


def login_criacao(db: Session, data: schemas.LoginRequisicao) -> models.LoginRequisicao:
    data.password = hashlib.sha256(data.password.encode()).hexdigest()
    login = models.LoginRequisicao(**data.models.dumb())
    db.add(login)
    db.commit()
    db.refresh(login)

    return login


def is_authenticated(session) -> bool:
    """Verifica se o usuário está autenticado na sessão atual."""
    return bool(session.get("authenticated") and session.get("user"))


def login_verificacao(db: Session, data: schemas.LoginRequisicao) -> bool:
    """Verifica se o usuario e senha estão corretos."""
    user = (
        db.query(models.LoginRequisicao)
        .filter_by(nome_de_usuario=data.nomde_de_usuario)
        .first()
    )
    if not user:
        return False

    if user and user.senha_hash == hashlib.sha256(data.senha_hash.encode()).hexdigest():
        session["authenticated"] = True
        session["user"] = user.nome_de_usuario
        return True
    else:
        session["authenticated"] = False
        session["user"] = None
        return False
