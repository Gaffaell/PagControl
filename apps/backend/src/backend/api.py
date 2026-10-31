from contextlib import asynccontextmanager
from datetime import date

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy.orm import Session

from . import crud, models, schemas
from .database import SessionLocal, get_db
from .init_db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Garante que as tabelas existam ao subir o servidor (útil em bancos
    # novos, como um Neon recém-linkado, sem precisar rodar init_db.py à parte).
    init_db()
    # Gera a cobrança do mês corrente dos alunos ativos (se ainda não existir)
    # e aplica o juros de atraso — em lote, ver crud.gerar_cobrancas_do_mes.
    db = SessionLocal()
    try:
        crud.gerar_cobrancas_do_mes(db, date.today())
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


@app.get("/metricas/resumo", response_model=schemas.ResumoMetricas)
def resumo_metricas(
    competencia: str | None = Query(None, pattern=r"^\d{4}(-\d{2})?$"),
    db: Session = Depends(get_db),
):
    """Totais agrupados para a página de Métricas (opcionalmente de um mês)."""
    return crud.resumo_metricas(db, competencia)


@app.get("/metricas/insights", response_model=schemas.InsightsMetricas)
def insights_metricas(
    competencia: str | None = Query(None, pattern=r"^\d{4}(-\d{2})?$"),
    db: Session = Depends(get_db),
):
    """Resumo analítico até o fim do período (mês ou ano) escolhido."""
    return crud.insights_metricas(db, competencia)


@app.get("/metricas/arrecadacao", response_model=schemas.AnaliseArrecadacao)
def analise_arrecadacao(
    competencia: str | None = Query(None, pattern=r"^\d{4}(-\d{2})?$"),
    db: Session = Depends(get_db),
):
    """Valor cobrado e recebido por modalidade, faixa etária, turno e dia."""
    return crud.analise_arrecadacao(db, competencia)


@app.get("/metricas/vintage", response_model=schemas.CurvaVintage)
def curva_vintage(db: Session = Depends(get_db)):
    return crud.curva_vintage(db)


@app.get("/metricas/detalhamento", response_model=schemas.DetalhamentoMetricas)
def detalhamento_metricas(
    competencia: str | None = Query(None, pattern=r"^\d{4}(-\d{2})?$"),
    limite: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Cobranças mais recentes com o nome do aluno, limitadas a `limite`."""
    return crud.detalhar_cobrancas(db, competencia, limite)

@app.post("/login")
def login_requisicao(dados: schemas.LoginRequisicao, db: Session = Depends(get_db)):
    """Verifica se o usuário e senha estão corretos."""
    if crud.login_verificacao(db, dados):
        return {"authenticated": True}
    else:
        raise HTTPException(401, "Usuário ou senha incorretos")

@app.post("/login/verificacao")
def login_verificacao(dados: schemas.LoginRequisicao, db: Session = Depends(get_db)):
    """Verifica se o usuário e senha estão corretos."""
    if crud.login_verificacao(db, dados):
        return {"authenticated": True}
    else:
        raise HTTPException(401, "Usuário ou senha incorretos")