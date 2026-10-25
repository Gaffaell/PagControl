"""Massa de dados e referência em Python puro para validar crud.resumo_metricas.

A "referência" reproduz, linha a linha, a lógica que a página de Métricas
aplicava sobre as listas completas de alunos e cobranças. O resumo agrupado
no banco precisa dar exatamente o mesmo resultado.
"""

import random
from collections import defaultdict
from datetime import date, timedelta

from backend import crud, models
from sqlalchemy import select

MODALIDADES = [
    "Natação",
    " boxe ",
    "BOXE",
    "",
    "   ",
    None,
    "Pilates/Yoga",
    "yoga",
    "Musculação",
]
COMPETENCIAS = ["2026-08", "2026-09", "2026-10"]


def _limite_aproximado(hoje: date, idade: int) -> date:
    try:
        return hoje.replace(year=hoje.year - idade)
    except ValueError:
        return hoje.replace(year=hoje.year - idade, day=28)


def nascimentos_de_teste(hoje: date) -> list[date | None]:
    """Datas em volta de cada virada de faixa (±3 dias), futuras, bissextas,
    muito antigas e espalhadas ao acaso."""
    gerador = random.Random(5)
    datas: list[date | None] = [None]
    for idade in (0, 24, 25, 34, 35, 44, 45, 54, 55, 64, 65, 200, 201):
        base = _limite_aproximado(hoje, idade)
        datas += [base + timedelta(days=ajuste) for ajuste in range(-3, 4)]
    datas += [hoje + timedelta(days=1), hoje + timedelta(days=400)]
    datas += [date(1996, 2, 29), date(2000, 2, 29), date(2004, 2, 29)]
    datas += [hoje - timedelta(days=gerador.randint(0, 75 * 365)) for _ in range(60)]
    return datas


def montar_dataset(db, hoje: date) -> None:
    gerador = random.Random(11)
    for nascimento in nascimentos_de_teste(hoje):
        aluno = models.Aluno(
            nome=f"Aluno {gerador.randint(1, 10**6)}",
            valor_mensalidade=round(gerador.uniform(60, 260), 2),
            dia_vencimento=gerador.randint(1, 28),
            modalidade=gerador.choice(MODALIDADES),
            turno=gerador.choice([None, *models.Turno]),
            dia_semana=gerador.choice([None, *models.DiaSemana]),
            data_nascimento=nascimento,
            ativo=gerador.random() > 0.2,
        )
        db.add(aluno)
        db.flush()
        for competencia in gerador.sample(COMPETENCIAS, gerador.randint(1, 3)):
            status = gerador.choice(list(models.StatusCobranca))
            db.add(
                models.Cobranca(
                    aluno_id=aluno.id,
                    competencia=competencia,
                    valor=round(gerador.uniform(60, 320), 2),
                    data_vencimento=date(2026, 10, gerador.randint(1, 28)),
                    status=status,
                    data_pagamento=hoje
                    if status == models.StatusCobranca.PAGO
                    else None,
                    forma_pagamento=(
                        gerador.choice(list(models.FormaPagamento))
                        if status == models.StatusCobranca.PAGO
                        else None
                    ),
                )
            )
    db.commit()


def faixa_referencia(data_nascimento: date | None, hoje: date) -> str:
    if not data_nascimento:
        return crud.FAIXA_ETARIA_NAO_INFORMADA
    idade = (
        hoje.year
        - data_nascimento.year
        - ((hoje.month, hoje.day) < (data_nascimento.month, data_nascimento.day))
    )
    for minimo, maximo, label in crud.FAIXAS_ETARIAS:
        if minimo <= idade <= maximo:
            return label
    return crud.FAIXA_ETARIA_NAO_INFORMADA


def normalizar_modalidade(valor: str | None) -> str:
    if not valor or not valor.strip():
        return "Não informada"
    return valor.strip().title()


def _somar(linhas, chave):
    agrupado: dict = defaultdict(lambda: [0, 0.0])
    for linha in linhas:
        grupo = agrupado[chave(linha)]
        grupo[0] += 1
        grupo[1] += linha["valor"]
    return {k: (q, v) for k, (q, v) in agrupado.items()}


def referencia(db, hoje: date, competencia: str | None) -> dict:
    alunos = {a.id: a for a in db.scalars(select(models.Aluno))}
    linhas = []
    todas = []
    for c in db.scalars(select(models.Cobranca)):
        todas.append(
            {"valor": float(c.valor), "status": c.status, "competencia": c.competencia}
        )
        if competencia and not c.competencia.startswith(competencia):
            continue
        aluno = alunos.get(c.aluno_id)
        linhas.append(
            {
                "valor": float(c.valor),
                "status": c.status,
                "competencia": c.competencia,
                "faixa": faixa_referencia(
                    aluno.data_nascimento if aluno else None, hoje
                ),
                "modalidade": normalizar_modalidade(
                    aluno.modalidade if aluno else None
                ),
                "turno": aluno.turno if aluno else None,
                "dia": aluno.dia_semana if aluno else None,
            }
        )
    ativos = [a for a in alunos.values() if a.ativo]
    return {
        "alunos_ativos": len(ativos),
        "receita_prevista": sum(float(a.valor_mensalidade) for a in ativos),
        "por_status": _somar(linhas, lambda linha: linha["status"]),
        "por_competencia": _somar(
            todas, lambda linha: (linha["competencia"], linha["status"])
        ),
        "por_faixa": _somar(linhas, lambda linha: (linha["faixa"], linha["status"])),
        "por_modalidade": _somar(
            linhas, lambda linha: (linha["modalidade"], linha["competencia"])
        ),
        "por_turno_dia": {
            k: v
            for k, (_, v) in _somar(
                linhas,
                lambda linha: (linha["competencia"], linha["turno"], linha["dia"]),
            ).items()
        },
    }


def do_resumo(resumo: dict) -> dict:
    """Converte o resumo do banco para o mesmo formato da referência."""
    por_modalidade: dict = defaultdict(lambda: [0, 0.0])
    for item in resumo["por_modalidade"]:
        chave = (normalizar_modalidade(item["modalidade"]), item["competencia"])
        por_modalidade[chave][0] += item["quantidade"]
        por_modalidade[chave][1] += item["valor"]
    return {
        "alunos_ativos": resumo["alunos_ativos"],
        "receita_prevista": resumo["receita_prevista"],
        "por_status": {
            i["status"]: (i["quantidade"], i["valor"]) for i in resumo["por_status"]
        },
        "por_competencia": {
            (i["competencia"], i["status"]): (i["quantidade"], i["valor"])
            for i in resumo["por_competencia"]
        },
        "por_faixa": {
            (i["faixa_etaria"], i["status"]): (i["quantidade"], i["valor"])
            for i in resumo["por_faixa_etaria"]
        },
        "por_modalidade": {k: (q, v) for k, (q, v) in por_modalidade.items()},
        "por_turno_dia": {
            (i["competencia"], i["turno"], i["dia_semana"]): i["valor"]
            for i in resumo["por_turno_dia"]
        },
    }
