from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from . import crud, models, schemas
from .database import get_db
from .init_db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Garante que as tabelas existam ao subir o servidor (útil em bancos
    # novos, como um Neon recém-linkado, sem precisar rodar init_db.py à parte).
    init_db()
    yield


app = FastAPI(title="Sistema de Cobrança - PagControl", lifespan=lifespan)


@app.post("/alunos", response_model=schemas.AlunoOut, status_code=201)
def criar_aluno(dados: schemas.AlunoCreate, db: Session = Depends(get_db)):
    return crud.criar_aluno(db, dados)


@app.get("/alunos", response_model=list[schemas.AlunoOut])
def listar_alunos(apenas_ativos: bool = False, db: Session = Depends(get_db)):
    return crud.listar_alunos(db, apenas_ativos)


@app.get("/alunos/{aluno_id}", response_model=schemas.AlunoOut)
def obter_aluno(aluno_id: int, db: Session = Depends(get_db)):
    aluno = crud.obter_aluno(db, aluno_id)
    if not aluno:
        raise HTTPException(404, "Aluno não encontrado")
    return aluno


@app.patch("/alunos/{aluno_id}", response_model=schemas.AlunoOut)
def atualizar_aluno(aluno_id: int, dados: schemas.AlunoUpdate, db: Session = Depends(get_db)):
    aluno = crud.obter_aluno(db, aluno_id)
    if not aluno:
        raise HTTPException(404, "Aluno não encontrado")
    return crud.atualizar_aluno(db, aluno, dados)


@app.delete("/alunos/{aluno_id}", status_code=204)
def desativar_aluno(aluno_id: int, db: Session = Depends(get_db)):
    """Soft delete: marca ativo=False em vez de apagar a linha, preservando
    o histórico de cobranças do aluno."""
    aluno = crud.obter_aluno(db, aluno_id)
    if not aluno:
        raise HTTPException(404, "Aluno não encontrado")
    crud.desativar_aluno(db, aluno)


@app.post("/alunos/{aluno_id}/cobrancas", response_model=schemas.CobrancaOut, status_code=201)
def gerar_cobranca(aluno_id: int, db: Session = Depends(get_db)):
    aluno = crud.obter_aluno(db, aluno_id)
    if not aluno:
        raise HTTPException(404, "Aluno não encontrado")
    return crud.gerar_cobranca(db, aluno)


@app.get("/cobrancas", response_model=list[schemas.CobrancaOut])
def listar_cobrancas(
    aluno_id: int | None = None,
    status: models.StatusCobranca | None = None,
    db: Session = Depends(get_db),
):
    return crud.listar_cobrancas(db, aluno_id, status)


@app.post("/cobrancas/{cobranca_id}/pagar", response_model=schemas.CobrancaOut)
def registrar_pagamento(
    cobranca_id: int, dados: schemas.PagamentoRequest, db: Session = Depends(get_db)
):
    cobranca = crud.obter_cobranca(db, cobranca_id)
    if not cobranca:
        raise HTTPException(404, "Cobrança não encontrada")
    return crud.registrar_pagamento(db, cobranca, dados)


@app.post("/cobrancas/atualizar-status")
def atualizar_status_atrasos(db: Session = Depends(get_db)):
    """Roda a régua de cobrança sob demanda. Em produção isso rodaria num
    agendador (cron/scheduler) diário; por ora é disparado manualmente."""
    total = crud.atualizar_status_atrasos(db)
    return {"cobrancas_atualizadas": total}
