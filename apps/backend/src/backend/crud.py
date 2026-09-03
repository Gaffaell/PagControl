import calendar
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models, schemas

# Regras de negócio do sistema de cobrança, separadas das rotas (app/api.py)
# para poder testar/reutilizar sem depender do FastAPI.


def criar_aluno(db: Session, dados: schemas.AlunoCreate) -> models.Aluno:
    aluno = models.Aluno(**dados.model_dump())
    db.add(aluno)
    db.commit()
    db.refresh(aluno)
    return aluno


def listar_alunos(db: Session, apenas_ativos: bool = False) -> list[models.Aluno]:
    stmt = select(models.Aluno)
    if apenas_ativos:
        stmt = stmt.where(models.Aluno.ativo.is_(True))
    return list(db.scalars(stmt))


def obter_aluno(db: Session, aluno_id: int) -> models.Aluno | None:
    return db.get(models.Aluno, aluno_id)


def atualizar_aluno(
    db: Session, aluno: models.Aluno, dados: schemas.AlunoUpdate
) -> models.Aluno:
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(aluno, campo, valor)
    db.commit()
    db.refresh(aluno)
    return aluno


def desativar_aluno(db: Session, aluno: models.Aluno) -> None:
    aluno.ativo = False
    db.commit()


def _proxima_competencia_e_vencimento(dia_vencimento: int, a_partir_de: date) -> tuple[str, date]:
    """Calcula a competência (mês) e o vencimento da próxima fatura.

    Trata meses com menos dias que o dia de vencimento cadastrado (ex.:
    vencimento dia 31 em um mês de 30 dias) usando o último dia do mês.
    """
    ano, mes = a_partir_de.year, a_partir_de.month + 1
    if mes > 12:
        mes = 1
        ano += 1
    ultimo_dia_do_mes = calendar.monthrange(ano, mes)[1]
    dia = min(dia_vencimento, ultimo_dia_do_mes)
    vencimento = date(ano, mes, dia)
    competencia = f"{ano:04d}-{mes:02d}"
    return competencia, vencimento


def gerar_cobranca(db: Session, aluno: models.Aluno) -> models.Cobranca:
    """Gera a fatura do próximo mês (ciclo de cobrança da proposta, seção 2.1).

    Idempotente: se já existir uma cobrança para essa competência, retorna a
    existente em vez de duplicar (permite chamar de novo sem efeito colateral).
    """
    competencia, vencimento = _proxima_competencia_e_vencimento(
        aluno.dia_vencimento, date.today()
    )

    existente = db.scalar(
        select(models.Cobranca).where(
            models.Cobranca.aluno_id == aluno.id,
            models.Cobranca.competencia == competencia,
        )
    )
    if existente:
        return existente

    cobranca = models.Cobranca(
        aluno_id=aluno.id,
        competencia=competencia,
        valor=aluno.valor_mensalidade,
        data_vencimento=vencimento,
    )
    db.add(cobranca)
    db.commit()
    db.refresh(cobranca)
    return cobranca


def listar_cobrancas(
    db: Session, aluno_id: int | None = None, status: models.StatusCobranca | None = None
) -> list[models.Cobranca]:
    stmt = select(models.Cobranca)
    if aluno_id is not None:
        stmt = stmt.where(models.Cobranca.aluno_id == aluno_id)
    if status is not None:
        stmt = stmt.where(models.Cobranca.status == status)
    return list(db.scalars(stmt))


def obter_cobranca(db: Session, cobranca_id: int) -> models.Cobranca | None:
    return db.get(models.Cobranca, cobranca_id)


def registrar_pagamento(
    db: Session, cobranca: models.Cobranca, dados: schemas.PagamentoRequest
) -> models.Cobranca:
    cobranca.status = models.StatusCobranca.PAGO
    cobranca.forma_pagamento = dados.forma_pagamento
    cobranca.data_pagamento = dados.data_pagamento or date.today()
    db.commit()
    db.refresh(cobranca)
    return cobranca


def atualizar_status_atrasos(db: Session) -> int:
    """Aplica a régua de cobrança: marca 'atrasado' após o vencimento e
    'inadimplente' após o maior intervalo de atraso configurado."""
    regua = db.scalar(select(models.ConfiguracaoRegua))
    dias_limite_inadimplencia = max(regua.lista_dias_cobranca_atraso()) if regua else 7

    hoje = date.today()
    pendentes = db.scalars(
        select(models.Cobranca).where(
            models.Cobranca.status.in_(
                [models.StatusCobranca.PENDENTE, models.StatusCobranca.ATRASADO]
            )
        )
    )

    atualizadas = 0
    for cobranca in pendentes:
        dias_atraso = (hoje - cobranca.data_vencimento).days
        novo_status = cobranca.status
        if dias_atraso >= dias_limite_inadimplencia:
            novo_status = models.StatusCobranca.INADIMPLENTE
        elif dias_atraso > 0:
            novo_status = models.StatusCobranca.ATRASADO

        if novo_status != cobranca.status:
            cobranca.status = novo_status
            atualizadas += 1

    if atualizadas:
        db.commit()
    return atualizadas
