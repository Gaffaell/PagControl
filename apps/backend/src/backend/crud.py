import calendar
from datetime import date

from sqlalchemy import (
    Date,
    Integer,
    case,
    cast,
    desc,
    extract,
    func,
    literal,
    select,
    update,
)
from sqlalchemy.orm import Session

from . import insights, models, schemas

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


FAIXAS_ETARIAS = [
    (0, 24, "Até 24"),
    (25, 34, "25-34"),
    (35, 44, "35-44"),
    (45, 54, "45-54"),
    (55, 64, "55-64"),
    (65, 200, "65+"),
]
FAIXA_ETARIA_NAO_INFORMADA = "Não informada"
ORDEM_FAIXAS_ETARIAS = [label for _, _, label in FAIXAS_ETARIAS] + [
    FAIXA_ETARIA_NAO_INFORMADA
]


def _nascimento_limite(hoje: date, idade: int) -> date:
    """Data de nascimento mais recente de quem já completou `idade` anos em
    `hoje` (nascido nessa data ou antes tem `idade` anos ou mais)."""
    try:
        return hoje.replace(year=hoje.year - idade)
    except ValueError:  # 29/02 em ano não bissexto
        return hoje.replace(year=hoje.year - idade, day=28)


def _faixa_etaria_sql(hoje: date):
    """Faixa etária calculada no próprio banco, comparando a data de
    nascimento com datas-limite (sem funções de data específicas de um
    SGBD). As datas entram inline para o GROUP BY casar com o SELECT."""
    nascimento = models.Aluno.data_nascimento

    def limite(idade: int):
        return literal(
            _nascimento_limite(hoje, idade), type_=Date, literal_execute=True
        )

    casos = [
        (nascimento.is_(None), FAIXA_ETARIA_NAO_INFORMADA),
        (nascimento > limite(0), FAIXA_ETARIA_NAO_INFORMADA),
    ]
    casos += [
        (nascimento > limite(maximo + 1), label) for _, maximo, label in FAIXAS_ETARIAS
    ]
    return case(*casos, else_=FAIXA_ETARIA_NAO_INFORMADA)


def _filtro_periodo(periodo: str | None) -> list:
    """Filtro por mês ("AAAA-MM") ou por ano inteiro ("AAAA"); sem período, nada."""
    if not periodo:
        return []
    if len(periodo) == 4:
        return [models.Cobranca.competencia.like(f"{periodo}-%")]
    return [models.Cobranca.competencia == periodo]


def resumo_metricas(
    db: Session, competencia: str | None = None, hoje: date | None = None
) -> dict:
    """Totais para a página de Métricas, agrupados no banco.

    Com `competencia`, só as cobranças desse mês entram nos agrupamentos;
    a lista de competências, a contagem de alunos ativos, a receita prevista e
    a evolução por competência (`por_competencia`) são sempre globais.
    """
    hoje = hoje or date.today()
    filtro = _filtro_periodo(competencia)
    quantidade = func.count(models.Cobranca.id)
    valor = func.coalesce(func.sum(models.Cobranca.valor), 0)
    com_aluno = models.Aluno.id == models.Cobranca.aluno_id

    competencias = db.scalars(
        select(models.Cobranca.competencia)
        .distinct()
        .order_by(desc(models.Cobranca.competencia))
    ).all()
    alunos_ativos, receita_prevista = db.execute(
        select(
            func.count(models.Aluno.id),
            func.coalesce(func.sum(models.Aluno.valor_mensalidade), 0),
        ).where(models.Aluno.ativo.is_(True))
    ).one()

    por_status = db.execute(
        select(models.Cobranca.status, quantidade, valor)
        .where(*filtro)
        .group_by(models.Cobranca.status)
    ).all()

    # Evolução mensal: sempre global (os meses aparecem lado a lado no gráfico).
    por_competencia = db.execute(
        select(models.Cobranca.competencia, models.Cobranca.status, quantidade, valor)
        .group_by(models.Cobranca.competencia, models.Cobranca.status)
        .order_by(models.Cobranca.competencia)
    ).all()

    faixa = _faixa_etaria_sql(hoje)
    por_faixa = db.execute(
        select(faixa, models.Cobranca.status, quantidade, valor)
        .select_from(models.Cobranca)
        .outerjoin(models.Aluno, com_aluno)
        .where(*filtro)
        .group_by(faixa, models.Cobranca.status)
    ).all()

    por_modalidade = db.execute(
        select(models.Aluno.modalidade, models.Cobranca.competencia, quantidade, valor)
        .select_from(models.Cobranca)
        .outerjoin(models.Aluno, com_aluno)
        .where(*filtro)
        .group_by(models.Aluno.modalidade, models.Cobranca.competencia)
    ).all()

    por_turno_dia = db.execute(
        select(
            models.Cobranca.competencia,
            models.Aluno.turno,
            models.Aluno.dia_semana,
            valor,
        )
        .select_from(models.Cobranca)
        .outerjoin(models.Aluno, com_aluno)
        .where(*filtro)
        .group_by(
            models.Cobranca.competencia, models.Aluno.turno, models.Aluno.dia_semana
        )
    ).all()

    return {
        "competencias": list(competencias),
        "ordem_faixas_etarias": ORDEM_FAIXAS_ETARIAS,
        "alunos_ativos": alunos_ativos,
        "receita_prevista": float(receita_prevista),
        "por_status": [
            {"status": s, "quantidade": q, "valor": float(v)} for s, q, v in por_status
        ],
        "por_faixa_etaria": [
            {"faixa_etaria": f, "status": s, "quantidade": q, "valor": float(v)}
            for f, s, q, v in por_faixa
        ],
        "por_modalidade": [
            {"modalidade": m, "competencia": c, "quantidade": q, "valor": float(v)}
            for m, c, q, v in por_modalidade
        ],
        "por_competencia": [
            {"competencia": c, "status": s, "quantidade": q, "valor": float(v)}
            for c, s, q, v in por_competencia
        ],
        "por_turno_dia": [
            {"competencia": c, "turno": t, "dia_semana": d, "valor": float(v)}
            for c, t, d, v in por_turno_dia
        ],
    }


def analise_arrecadacao(
    db: Session, periodo: str | None = None, hoje: date | None = None
) -> dict:
    """Perfil de quem paga: valor cobrado e valor recebido (cobranças pagas) por
    modalidade, faixa etária, turno e dia da semana — uma linha por combinação.

    `periodo` é "AAAA", "AAAA-MM" ou nada (carteira inteira). A página de
    Análise soma as linhas conforme a característica que está mostrando.
    """
    hoje = hoje or date.today()
    faixa = _faixa_etaria_sql(hoje)
    pago = models.Cobranca.status == models.StatusCobranca.PAGO
    linhas = db.execute(
        select(
            models.Aluno.modalidade,
            faixa,
            models.Aluno.turno,
            models.Aluno.dia_semana,
            func.coalesce(func.sum(models.Cobranca.valor), 0),
            func.coalesce(func.sum(case((pago, models.Cobranca.valor), else_=0)), 0),
            func.count(models.Cobranca.id),
            func.count(func.distinct(models.Cobranca.aluno_id)),
        )
        .select_from(models.Cobranca)
        .outerjoin(models.Aluno, models.Aluno.id == models.Cobranca.aluno_id)
        .where(*_filtro_periodo(periodo))
        .group_by(
            models.Aluno.modalidade,
            faixa,
            models.Aluno.turno,
            models.Aluno.dia_semana,
        )
    ).all()
    return {
        "ordem_faixas_etarias": ORDEM_FAIXAS_ETARIAS,
        "linhas": [
            {
                "modalidade": modalidade,
                "faixa_etaria": faixa_etaria,
                "turno": turno,
                "dia_semana": dia_semana,
                "valor_cobrado": float(cobrado),
                "valor_recebido": float(recebido),
                "cobrancas": cobrancas,
                "alunos": alunos,
            }
            for modalidade, faixa_etaria, turno, dia_semana, cobrado, recebido, cobrancas, alunos in linhas
        ],
    }


def detalhar_cobrancas(
    db: Session, competencia: str | None = None, limite: int = 200
) -> dict:
    """Cobranças mais recentes (competência e vencimento decrescentes) com o
    nome do aluno, limitadas a `limite`, e o total que atende ao filtro."""
    filtro = _filtro_periodo(competencia)
    total = db.scalar(select(func.count(models.Cobranca.id)).where(*filtro)) or 0
    linhas = db.execute(
        select(models.Cobranca, models.Aluno.nome)
        .outerjoin(models.Aluno, models.Aluno.id == models.Cobranca.aluno_id)
        .where(*filtro)
        .order_by(
            desc(models.Cobranca.competencia),
            desc(models.Cobranca.data_vencimento),
            desc(models.Cobranca.id),
        )
        .limit(limite)
    ).all()
    itens = [
        {
            "id": c.id,
            "aluno_id": c.aluno_id,
            "aluno_nome": nome,
            "competencia": c.competencia,
            "valor": float(c.valor),
            "data_vencimento": c.data_vencimento,
            "status": c.status,
            "data_pagamento": c.data_pagamento,
            "forma_pagamento": c.forma_pagamento,
        }
        for c, nome in linhas
    ]
    return {"total": total, "itens": itens}


MESES_VINTAGE = 12


def curva_vintage(db: Session) -> dict:
    """Curva de vintage: por safra (mês de matrícula) e mês de vida da conta, o
    % ACUMULADO de alunos que já ficaram inadimplentes ao menos uma vez.

    - mês de vida = diferença em meses entre a competência da cobrança e o mês
      de matrícula (0 = mês da matrícula), limitado aos primeiros 12;
    - inadimplente = cobrança com status `inadimplente` (a régua já separa
      'atrasado', que ainda é recuperável);
    - em cada mês só entram os alunos que têm cobrança naquele mês. Para um
      mesmo aluno o indicador nunca desfaz (quem estreou inadimplente continua
      contando), mas a curva da safra pode oscilar quando o conjunto de alunos
      com cobrança muda de um mês para o outro (safras pequenas ou recentes).

    A média geral pondera cada safra pelo número de alunos (soma de
    inadimplentes dividida pela soma de alunos, mês a mês)."""
    mes_da_cobranca = cast(
        func.substr(models.Cobranca.competencia, 1, 4), Integer
    ) * 12 + cast(func.substr(models.Cobranca.competencia, 6, 2), Integer)
    ano_matricula = extract("year", models.Aluno.data_matricula)
    mes_matricula = extract("month", models.Aluno.data_matricula)
    mes_de_vida = mes_da_cobranca - (ano_matricula * 12 + mes_matricula)

    linhas = (
        select(
            models.Cobranca.aluno_id.label("aluno_id"),
            models.Cobranca.status.label("status"),
            ano_matricula.label("ano"),
            mes_matricula.label("mes"),
            mes_de_vida.label("mes_de_vida"),
        )
        .join(models.Aluno, models.Aluno.id == models.Cobranca.aluno_id)
        .cte("linhas")
    )
    primeiro_default = (
        select(
            linhas.c.aluno_id.label("aluno_id"),
            func.min(linhas.c.mes_de_vida).label("primeiro"),
        )
        .where(linhas.c.status == models.StatusCobranca.INADIMPLENTE)
        .group_by(linhas.c.aluno_id)
        .cte("primeiro_default")
    )
    base = (
        select(
            linhas.c.aluno_id,
            linhas.c.ano,
            linhas.c.mes,
            linhas.c.mes_de_vida,
        )
        .where(linhas.c.mes_de_vida >= 0, linhas.c.mes_de_vida <= MESES_VINTAGE)
        .distinct()
        .cte("base")
    )
    ja_inadimplente = case(
        (primeiro_default.c.primeiro <= base.c.mes_de_vida, 1), else_=0
    )
    resultado = db.execute(
        select(
            base.c.ano,
            base.c.mes,
            base.c.mes_de_vida,
            func.count().label("alunos"),
            func.sum(ja_inadimplente).label("inadimplentes"),
        )
        .select_from(base)
        .outerjoin(primeiro_default, primeiro_default.c.aluno_id == base.c.aluno_id)
        .group_by(base.c.ano, base.c.mes, base.c.mes_de_vida)
        .order_by(base.c.ano, base.c.mes, base.c.mes_de_vida)
    ).all()

    safras = []
    totais: dict[int, list[int]] = {}
    for ano, mes, mes_vida, alunos, inadimplentes in resultado:
        inadimplentes = int(inadimplentes or 0)
        safras.append(
            {
                "safra": f"{int(ano):04d}-{int(mes):02d}",
                "mes_de_vida": int(mes_vida),
                "alunos": alunos,
                "inadimplentes": inadimplentes,
                "percentual": 100 * inadimplentes / alunos,
            }
        )
        total = totais.setdefault(int(mes_vida), [0, 0])
        total[0] += alunos
        total[1] += inadimplentes
    media = [
        {
            "mes_de_vida": mes_vida,
            "alunos": alunos,
            "inadimplentes": inadimplentes,
            "percentual": 100 * inadimplentes / alunos,
        }
        for mes_vida, (alunos, inadimplentes) in sorted(totais.items())
    ]
    return {"meses": MESES_VINTAGE, "safras": safras, "media": media}


def insights_metricas(
    db: Session, periodo: str | None = None, hoje: date | None = None
) -> dict:
    """Resumo analítico da carteira (ver `insights.gerar_insights`).

    `periodo` ("AAAA" ou "AAAA-MM") limita a análise às competências até o fim
    desse período, como se a carteira terminasse ali.
    """
    hoje = hoje or date.today()
    consulta = (
        select(
            models.Aluno.modalidade,
            models.Cobranca.competencia,
            models.Cobranca.status,
            func.coalesce(func.sum(models.Cobranca.valor), 0),
            func.count(models.Cobranca.id),
        )
        .select_from(models.Cobranca)
        .outerjoin(models.Aluno, models.Aluno.id == models.Cobranca.aluno_id)
        .group_by(
            models.Aluno.modalidade, models.Cobranca.competencia, models.Cobranca.status
        )
    )
    if periodo:
        # "AAAA" vira "AAAA-12": a comparação de texto cobre o ano inteiro.
        limite = periodo if len(periodo) == 7 else f"{periodo}-12"
        consulta = consulta.where(models.Cobranca.competencia <= limite)
    linhas = db.execute(consulta).all()
    return insights.gerar_insights(
        [
            (modalidade, competencia, status.value, float(valor), quantidade)
            for modalidade, competencia, status, valor, quantidade in linhas
        ],
        hoje,
    )

def login_verificacao(db: Session, usuario: str, senha: str) -> bool:
    """Verifica se o usuário e senha estão corretos."""
    # Aqui você pode implementar a lógica de verificação de login, por exemplo:
    # - Consultar uma tabela de usuários no banco de dados
    # - Comparar a senha fornecida com a senha armazenada (hash)
    # Para fins de exemplo, vamos supor que temos um usuário "admin" com senha "senha123"
    if usuario == "admin" and senha == "senha123":
        return True
    return False