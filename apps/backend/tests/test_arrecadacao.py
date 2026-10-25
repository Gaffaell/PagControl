from collections import defaultdict
from datetime import date

import pytest
from backend import crud, models
from dados_metricas import COMPETENCIAS, montar_dataset

HOJE = date(2026, 10, 20)


def _por(linhas: list[dict], chave: str, campo: str) -> dict:
    totais: dict = defaultdict(float)
    for linha in linhas:
        totais[linha[chave]] += linha[campo]
    return totais


@pytest.mark.parametrize("periodo", [None, "2026", *COMPETENCIAS])
def test_totais_batem_com_o_resumo_e_com_as_cobrancas(db, periodo):
    montar_dataset(db, HOJE)
    resultado = crud.analise_arrecadacao(db, periodo, HOJE)
    linhas = resultado["linhas"]

    cobrancas = [
        c
        for c in db.query(models.Cobranca).all()
        if not periodo or c.competencia.startswith(periodo)
    ]
    assert sum(linha["cobrancas"] for linha in linhas) == len(cobrancas)
    assert sum(linha["valor_cobrado"] for linha in linhas) == pytest.approx(
        sum(float(c.valor) for c in cobrancas)
    )
    recebido = sum(
        float(c.valor) for c in cobrancas if c.status == models.StatusCobranca.PAGO
    )
    assert sum(linha["valor_recebido"] for linha in linhas) == pytest.approx(recebido)

    # a faixa etária deve coincidir com a do resumo (mesma regra de cálculo)
    resumo = crud.resumo_metricas(db, periodo, HOJE)
    pago_por_faixa: dict = defaultdict(float)
    for item in resumo["por_faixa_etaria"]:
        if item["status"] == models.StatusCobranca.PAGO:
            pago_por_faixa[item["faixa_etaria"]] += item["valor"]
    obtido = {
        faixa: valor
        for faixa, valor in _por(linhas, "faixa_etaria", "valor_recebido").items()
        if valor
    }
    assert obtido.keys() == pago_por_faixa.keys()
    for faixa, valor in pago_por_faixa.items():
        assert obtido[faixa] == pytest.approx(valor)


def test_recebido_nunca_passa_do_cobrado_e_alunos_nao_se_repetem(db):
    montar_dataset(db, HOJE)
    linhas = crud.analise_arrecadacao(db, None, HOJE)["linhas"]
    assert all(
        linha["valor_recebido"] <= linha["valor_cobrado"] + 1e-6 for linha in linhas
    )
    # cada aluno tem um único perfil: a soma dos alunos por linha é o total de
    # alunos que têm ao menos uma cobrança
    com_cobranca = {c.aluno_id for c in db.query(models.Cobranca).all()}
    assert sum(linha["alunos"] for linha in linhas) == len(com_cobranca)


def test_endpoint(db, client):
    vazio = client.get("/metricas/arrecadacao")
    assert vazio.status_code == 200
    assert vazio.json()["linhas"] == []
    montar_dataset(db, date.today())
    resposta = client.get("/metricas/arrecadacao", params={"competencia": "2026"})
    assert resposta.status_code == 200
    assert resposta.json()["linhas"]
    assert client.get("/metricas/arrecadacao?competencia=abc").status_code == 422
