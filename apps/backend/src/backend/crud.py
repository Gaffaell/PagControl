import calendar
from datetime import date

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from . import models, schemas

# Regras de negócio do sistema de cobrança, separadas das rotas (app/api.py)
# para poder testar/reutilizar sem depender do FastAPI.

# Modalidades que disputam o mesmo horário/professor e por isso não podem
# cair no mesmo dia da semana para alunos diferentes. Modalidades fora
# dessas listas (ex.: Natação, Musculação) não têm essa restrição.
GRUPOS_EXCLUSIVOS_MODALIDADE = [
    frozenset({"Boxe", "Jiu-jitsu"}),
    frozenset({"Pilates", "Yoga"}),
    frozenset({"Aeróbico", "Fit Dance"}),
]

DIA_SEMANA_LABELS = {
    models.DiaSemana.SEGUNDA: "segunda-feira",
    models.DiaSemana.TERCA: "terça-feira",
    models.DiaSemana.QUARTA: "quarta-feira",
    models.DiaSemana.QUINTA: "quinta-feira",
    models.DiaSemana.SEXTA: "sexta-feira",
    models.DiaSemana.SABADO: "sábado",
    models.DiaSemana.DOMINGO: "domingo",
}


def _partes_modalidade(modalidade: str | None) -> set[str]:
    return {p.strip() for p in (modalidade or "").split("/") if p.strip()}


def _grupo_exclusivo(partes: set[str]) -> frozenset[str] | None:
    for grupo in GRUPOS_EXCLUSIVOS_MODALIDADE:
        if partes & grupo:
            return grupo
    return None


def verificar_conflito_dia(
    db: Session,
    modalidade: str | None,
    dia_semana: models.DiaSemana | None,
    ignorar_aluno_id: int | None = None,
) -> models.Aluno | None:
    """Retorna o aluno ativo que já ocupa o mesmo dia dentro do mesmo grupo de
    modalidades exclusivas (ex.: Boxe e Jiu-jitsu não podem cair no mesmo
    dia), ou None se não houver conflito."""
    if not dia_semana:
        return None
    grupo = _grupo_exclusivo(_partes_modalidade(modalidade))
    if not grupo:
        return None
    candidatos = db.scalars(
        select(models.Aluno).where(
            models.Aluno.ativo.is_(True),
            models.Aluno.dia_semana == dia_semana,
        )
    )
    for candidato in candidatos:
        if ignorar_aluno_id is not None and candidato.id == ignorar_aluno_id:
            continue
        if _partes_modalidade(candidato.modalidade) & grupo:
            return candidato
    return None


def _erro_conflito(conflito: models.Aluno, dia_semana: models.DiaSemana) -> ValueError:
    dia_label = DIA_SEMANA_LABELS.get(dia_semana, dia_semana.value)
    return ValueError(
        f"Conflito de agenda: {conflito.nome} já tem aula de "
        f"{conflito.modalidade} na {dia_label}. Escolha outro dia."
    )


def criar_aluno(db: Session, dados: schemas.AlunoCreate) -> models.Aluno:
    if dados.dia_semana:
        conflito = verificar_conflito_dia(db, dados.modalidade, dados.dia_semana)
        if conflito:
            raise _erro_conflito(conflito, dados.dia_semana)
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
    alteracoes = dados.model_dump(exclude_unset=True)
    modalidade_efetiva = alteracoes.get("modalidade", aluno.modalidade)
    dia_semana_efetivo = alteracoes.get("dia_semana", aluno.dia_semana)
    if dia_semana_efetivo:
        conflito = verificar_conflito_dia(
            db, modalidade_efetiva, dia_semana_efetivo, ignorar_aluno_id=aluno.id
        )
        if conflito:
            raise _erro_conflito(conflito, dia_semana_efetivo)
    for campo, valor in alteracoes.items():
        setattr(aluno, campo, valor)
    db.commit()
    db.refresh(aluno)
    return aluno


def desativar_aluno(db: Session, aluno: models.Aluno) -> None:
    aluno.ativo = False
    db.commit()


def _proxima_competencia_e_vencimento(
    dia_vencimento: int, a_partir_de: date
) -> tuple[str, date]:
    """Calcula a competência atual e o vencimento do próximo mês.

    A competência representa o mês em curso, enquanto a data de vencimento
    aponta para o mês seguinte. Quando o dia de vencimento não existe no mês de
    cobrança (ex.: dia 31 em fevereiro), usamos o último dia disponível do mês.
    """
    ano, mes = a_partir_de.year, a_partir_de.month
    competencia = f"{ano:04d}-{mes:02d}"

    ano_vencimento, mes_vencimento = ano, mes + 1
    if mes_vencimento > 12:
        mes_vencimento = 1
        ano_vencimento += 1

    ultimo_dia_do_mes = calendar.monthrange(ano_vencimento, mes_vencimento)[1]
    dia = min(dia_vencimento, ultimo_dia_do_mes)
    vencimento = date(ano_vencimento, mes_vencimento, dia)
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


def _taxa_diaria(regua: models.ConfiguracaoRegua | None) -> float:
    """Converte porcentagem_juros_por_dia (texto, ex.: "0,033") em fração diária.

    Referência para o valor configurado: na ausência de taxa de mora pactuada
    em contrato, o art. 406 do Código Civil remete à taxa legal (usada por
    analogia como 1% ao mês, art. 161, §1º do CTN) e o art. 52, §1º do CDC
    limita a multa de mora a 2% sobre o valor da parcela em relações de
    consumo. 1% a.m. equivale a aproximadamente 0,033% ao dia, que é o valor
    padrão esperado aqui.
    """
    if not regua or not regua.porcentagem_juros_por_dia:
        return 0.0
    try:
        texto = str(regua.porcentagem_juros_por_dia).replace(",", ".").strip()
        return float(texto) / 100.0 if texto else 0.0
    except ValueError:
        return 0.0


def gerar_cobrancas_do_mes(db: Session, hoje: date) -> None:
    """Garante a cobrança do mês corrente de todos os alunos ativos, já com o
    juros composto sobre as faturas em atraso/inadimplentes.

    Roda a cada subida do servidor, por isso é feita em lote (poucas
    consultas, uma única transação): consultar aluno por aluno multiplicava as
    idas ao banco — e a transferência de rede cobrada pela Neon — pelo número
    de alunos. Idempotente: não duplica a cobrança da competência; se ela já
    existir e ainda não tiver sido paga, o valor é atualizado com o juros
    atual (antes o juros era calculado e descartado quando a cobrança já
    existia).
    """
    competencia = f"{hoje.year:04d}-{hoje.month:02d}"
    taxa_diaria = _taxa_diaria(obter_configuracao_regua(db))

    alunos = db.execute(
        select(
            models.Aluno.id,
            models.Aluno.valor_mensalidade,
            models.Aluno.dia_vencimento,
        ).where(models.Aluno.ativo.is_(True))
    ).all()

    existentes: dict[int, tuple[int, object, models.StatusCobranca]] = {}
    for cobranca_id, aluno_id, valor, status in db.execute(
        select(
            models.Cobranca.id,
            models.Cobranca.aluno_id,
            models.Cobranca.valor,
            models.Cobranca.status,
        ).where(models.Cobranca.competencia == competencia)
    ):
        existentes.setdefault(aluno_id, (cobranca_id, valor, status))

    juros_por_aluno: dict[int, float] = {}
    if taxa_diaria > 0:
        vencidas = db.execute(
            select(
                models.Cobranca.aluno_id,
                models.Cobranca.valor,
                models.Cobranca.data_vencimento,
            )
            .join(models.Aluno, models.Aluno.id == models.Cobranca.aluno_id)
            .where(
                models.Aluno.ativo.is_(True),
                models.Cobranca.status.in_(
                    [models.StatusCobranca.ATRASADO, models.StatusCobranca.INADIMPLENTE]
                ),
            )
        )
        for aluno_id, valor, vencimento in vencidas:
            dias_de_atraso = (hoje - vencimento).days
            if dias_de_atraso > 0:
                juros_por_aluno[aluno_id] = juros_por_aluno.get(aluno_id, 0.0) + float(
                    valor
                ) * ((1.0 + taxa_diaria) ** dias_de_atraso - 1.0)

    novas: list[models.Cobranca] = []
    atualizacoes: list[dict[str, object]] = []
    for aluno_id, mensalidade, dia_vencimento in alunos:
        juros = round(juros_por_aluno.get(aluno_id, 0.0), 2)
        valor_total = round(float(mensalidade) + juros, 2)
        existente = existentes.get(aluno_id)
        if existente:
            cobranca_id, valor_atual, status = existente
            if status != models.StatusCobranca.PAGO and valor_total != float(
                valor_atual
            ):
                atualizacoes.append({"id": cobranca_id, "valor": valor_total})
        else:
            _, vencimento = _proxima_competencia_e_vencimento(dia_vencimento, hoje)
            novas.append(
                models.Cobranca(
                    aluno_id=aluno_id,
                    competencia=competencia,
                    valor=valor_total,
                    data_vencimento=vencimento,
                )
            )

    if atualizacoes:
        db.execute(update(models.Cobranca), atualizacoes)
    db.add_all(novas)
    db.commit()


def listar_cobrancas(
    db: Session,
    aluno_id: int | None = None,
    status: models.StatusCobranca | None = None,
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


def obter_configuracao_regua(db: Session) -> models.ConfiguracaoRegua | None:
    return db.scalar(select(models.ConfiguracaoRegua))


def atualizar_configuracao_regua(
    db: Session, regua: models.ConfiguracaoRegua, dados: schemas.ConfiguracaoReguaUpdate
) -> models.ConfiguracaoRegua:
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(regua, campo, valor)
    db.commit()
    db.refresh(regua)
    return regua


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
