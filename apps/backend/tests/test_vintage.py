import random
from collections import defaultdict
from datetime import date

import pytest
from backend import crud, models


def _competencia(ano: int, mes: int) -> str:
    return f"{ano:04d}-{mes:02d}"


def _somar_meses(ano: int, mes: int, meses: int) -> tuple[int, int]:
    total = ano * 12 + (mes - 1) + meses
    return total // 12, total % 12 + 1


def _novo_aluno(db, matricula: date) -> models.Aluno:
    aluno = models.Aluno(
        nome="Aluno",
        valor_mensalidade=100,
        dia_vencimento=10,
        data_matricula=matricula,
    )
    db.add(aluno)
    db.flush()
    return aluno


def _cobrar(db, aluno, meses_de_vida: int, status: models.StatusCobranca) -> None:
    ano, mes = _somar_meses(
        aluno.data_matricula.year, aluno.data_matricula.month, meses_de_vida
    )
    db.add(
        models.Cobranca(
            aluno_id=aluno.id,
            competencia=_competencia(ano, mes),
            valor=100,
            data_vencimento=date(ano, mes, 10),
            status=status,
        )
    )


def test_exemplo_pequeno_calculado_a_mao(db):
    pago, inad = models.StatusCobranca.PAGO, models.StatusCobranca.INADIMPLENTE
    # Safra 2026-01: A fica inadimplente no mês 2; B nunca fica.
    a = _novo_aluno(db, date(2026, 1, 31))
    b = _novo_aluno(db, date(2026, 1, 2))
    for mes, status in [(0, pago), (1, pago), (2, inad), (3, pago)]:
        _cobrar(db, a, mes, status)
    for mes in range(4):
        _cobrar(db, b, mes, pago)
    # Safra 2026-02: C inadimplente já no mês 0.
    c = _novo_aluno(db, date(2026, 2, 15))
    _cobrar(db, c, 0, inad)
    db.commit()

    curva = crud.curva_vintage(db)
    por_ponto = {(p["safra"], p["mes_de_vida"]): p for p in curva["safras"]}

    assert por_ponto[("2026-01", 0)]["percentual"] == 0
    assert por_ponto[("2026-01", 1)]["percentual"] == 0
    # Acumulado: o aluno A continua contando no mês 3, mesmo pago.
    assert por_ponto[("2026-01", 2)]["percentual"] == 50
    assert por_ponto[("2026-01", 3)]["percentual"] == 50
    assert por_ponto[("2026-02", 0)]["percentual"] == 100
    media_mes_0 = next(p for p in curva["media"] if p["mes_de_vida"] == 0)
    assert (media_mes_0["alunos"], media_mes_0["inadimplentes"]) == (3, 1)
    assert media_mes_0["percentual"] == pytest.approx(100 / 3)


def test_ignora_meses_fora_de_0_a_12_e_banco_vazio(db):
    assert crud.curva_vintage(db) == {"meses": 12, "safras": [], "media": []}

    pago, inad = models.StatusCobranca.PAGO, models.StatusCobranca.INADIMPLENTE
    aluno = _novo_aluno(db, date(2026, 3, 10))
    _cobrar(db, aluno, -1, inad)  # competência anterior à matrícula
    _cobrar(db, aluno, 0, pago)
    _cobrar(db, aluno, 12, pago)
    _cobrar(db, aluno, 13, inad)
    db.commit()
    meses = {p["mes_de_vida"] for p in crud.curva_vintage(db)["safras"]}
    assert meses == {0, 12}
    # O default do mês -1 existe, então vale já no mês 0 (o aluno "estreou").
    ponto_0 = next(p for p in crud.curva_vintage(db)["safras"] if p["mes_de_vida"] == 0)
    assert ponto_0["inadimplentes"] == 1


def _referencia(db) -> dict:
    alunos = {a.id: a for a in db.query(models.Aluno)}
    cobrancas = db.query(models.Cobranca).all()

    def mes_de_vida(c):
        a = alunos[c.aluno_id]
        ano, mes = int(c.competencia[:4]), int(c.competencia[5:7])
        return (ano * 12 + mes) - (a.data_matricula.year * 12 + a.data_matricula.month)

    primeiro = {}
    for c in cobrancas:
        if c.status == models.StatusCobranca.INADIMPLENTE:
            m = mes_de_vida(c)
            primeiro[c.aluno_id] = min(m, primeiro.get(c.aluno_id, m))

    presentes = {
        (c.aluno_id, mes_de_vida(c))
        for c in cobrancas
        if 0 <= mes_de_vida(c) <= crud.MESES_VINTAGE
    }
    por_safra: dict = defaultdict(lambda: [0, 0])
    for aluno_id, m in presentes:
        a = alunos[aluno_id]
        grupo = por_safra[(f"{a.data_matricula:%Y-%m}", m)]
        grupo[0] += 1
        grupo[1] += aluno_id in primeiro and primeiro[aluno_id] <= m
    return {chave: tuple(valor) for chave, valor in por_safra.items()}


def test_confere_com_calculo_linha_a_linha_em_massa_aleatoria(db):
    gerador = random.Random(3)
    status_possiveis = list(models.StatusCobranca)
    pesos = [3, 1, 1, 1] if len(status_possiveis) == 4 else None
    for _ in range(220):
        matricula = date(
            gerador.choice([2024, 2025, 2026]),
            gerador.randint(1, 12),
            gerador.randint(1, 28),
        )
        aluno = _novo_aluno(db, matricula)
        for mes in gerador.sample(range(-1, 16), gerador.randint(1, 14)):
            status = gerador.choices(status_possiveis, weights=pesos)[0]
            _cobrar(db, aluno, mes, status)
    db.commit()

    esperado = _referencia(db)
    curva = crud.curva_vintage(db)
    obtido = {
        (p["safra"], p["mes_de_vida"]): (p["alunos"], p["inadimplentes"])
        for p in curva["safras"]
    }
    assert obtido == esperado

    # Média geral = soma dos inadimplentes / soma dos alunos, mês a mês.
    for ponto in curva["media"]:
        mes = ponto["mes_de_vida"]
        alunos = sum(v[0] for (_, m), v in esperado.items() if m == mes)
        inadimplentes = sum(v[1] for (_, m), v in esperado.items() if m == mes)
        assert (ponto["alunos"], ponto["inadimplentes"]) == (alunos, inadimplentes)
        assert ponto["percentual"] == pytest.approx(100 * inadimplentes / alunos)

    # A curva só cresce ao longo da vida da conta *para o mesmo conjunto de
    # alunos*; aqui basta checar que o percentual fica entre 0 e 100.
    assert all(0 <= p["percentual"] <= 100 for p in curva["safras"])


def test_endpoint_vintage(db, client):
    aluno = _novo_aluno(db, date(2026, 1, 5))
    _cobrar(db, aluno, 0, models.StatusCobranca.INADIMPLENTE)
    db.commit()
    resposta = client.get("/metricas/vintage")
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["meses"] == 12
    assert corpo["safras"][0]["safra"] == "2026-01"
    assert corpo["media"][0]["percentual"] == 100
