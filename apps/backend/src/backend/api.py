from contextlib import asynccontextmanager
from datetime import date

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import crud, models, schemas
from .database import SessionLocal, get_db
from .init_db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Garante que as tabelas existam ao subir o servidor (útil em bancos
    # novos, como um Neon recém-linkado, sem precisar rodar init_db.py à parte).

    # Faz todas as as cobranças do mês corrente para os alunos ativos sempre que iniciar
    # caso ainda não existam.
    init_db()
    hoje = date.today()
    db = SessionLocal()
    try:
        regua = crud.obter_configuracao_regua(db)
        taxa_diaria = 0.0
        if regua and regua.porcentagem_juros_por_dia:
            try:
                taxa_str = (
                    str(regua.porcentagem_juros_por_dia).replace(",", ".").strip()
                )
                taxa_diaria = float(taxa_str) / 100.0 if taxa_str else 0.0
            except ValueError:
                taxa_diaria = 0.0

        for aluno in crud.listar_alunos(db, apenas_ativos=True):
            valor_de_juros = 0.0
            vencidas = list(
                db.scalars(
                    select(models.Cobranca).where(
                        models.Cobranca.aluno_id == aluno.id,
                        models.Cobranca.status.in_(
                            [
                                models.StatusCobranca.ATRASADO,
                                models.StatusCobranca.INADIMPLENTE,
                            ]
                        ),
                    )
                )
            )
            # NÂO ESTÀ FAZENDO NOVA COBRANCA, MESMO COM MENSALIDADE ATRADADA
            if vencidas and taxa_diaria > 0:
                for cobranca_vencida in vencidas:
                    dias_de_atraso = max(
                        0, (hoje - cobranca_vencida.data_vencimento).days
                    )
                    if dias_de_atraso > 0:
                        valor_base = float(cobranca_vencida.valor)
                        valor_de_juros += valor_base * (
                            ((1.0 + taxa_diaria) ** dias_de_atraso) - 1.0
                        )
                valor_de_juros = round(valor_de_juros, 2)

            crud.gerar_cobranca_para_competencia(
                db, aluno, hoje.year, hoje.month, valor_de_juros=valor_de_juros
            )
    finally:
        db.close()
    yield


app = FastAPI(title="Sistema de Cobrança - PagControl", lifespan=lifespan)


@app.post("/alunos", response_model=schemas.AlunoOut, status_code=201)
def criar_aluno(dados: schemas.AlunoCreate, db: Session = Depends(get_db)):
    try:
        return crud.criar_aluno(db, dados)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


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
def atualizar_aluno(
    aluno_id: int, dados: schemas.AlunoUpdate, db: Session = Depends(get_db)
):
    aluno = crud.obter_aluno(db, aluno_id)
    if not aluno:
        raise HTTPException(404, "Aluno não encontrado")
    try:
        return crud.atualizar_aluno(db, aluno, dados)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.delete("/alunos/{aluno_id}", status_code=204)
def desativar_aluno(aluno_id: int, db: Session = Depends(get_db)):
    """Soft delete: marca ativo=False em vez de apagar a linha, preservando
    o histórico de cobranças do aluno."""
    aluno = crud.obter_aluno(db, aluno_id)
    if not aluno:
        raise HTTPException(404, "Aluno não encontrado")
    crud.desativar_aluno(db, aluno)


@app.post(
    "/alunos/{aluno_id}/cobrancas", response_model=schemas.CobrancaOut, status_code=201
)
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


@app.get("/configuracao-regua", response_model=schemas.ConfiguracaoReguaOut)
def obter_configuracao_regua(db: Session = Depends(get_db)):
    regua = crud.obter_configuracao_regua(db)
    if not regua:
        raise HTTPException(404, "Configuração da régua não encontrada")
    return regua


@app.patch("/configuracao-regua", response_model=schemas.ConfiguracaoReguaOut)
def atualizar_configuracao_regua(
    dados: schemas.ConfiguracaoReguaUpdate, db: Session = Depends(get_db)
):
    regua = crud.obter_configuracao_regua(db)
    if not regua:
        raise HTTPException(404, "Configuração da régua não encontrada")
    return crud.atualizar_configuracao_regua(db, regua, dados)
