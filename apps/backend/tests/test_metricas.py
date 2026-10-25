from datetime import date, timedelta

import pytest
from backend import crud, models
from dados_metricas import COMPETENCIAS, do_resumo, montar_dataset, referencia

HOJE = date(2026, 10, 20)
# Datas "de virada": 29/02 em ano bissexto, dia seguinte, 1º de janeiro etc.
DATAS_DE_REFERENCIA = [
    HOJE,
    date(2028, 2, 29),
    date(2027, 3, 1),
    date(2024, 2, 29),
    date(2026, 1, 1),
]


def _comparar(esperado: dict, obtido: dict) -> None:
    assert obtido["alunos_ativos"] == esperado["alunos_ativos"]
    assert obtido["receita_prevista"] == pytest.approx(esperado["receita_prevista"])
    for grupo in ("por_status", "por_competencia", "por_faixa", "por_modalidade"):
        assert obtido[grupo].keys() == esperado[grupo].keys(), grupo
        for chave, (quantidade, valor) in esperado[grupo].items():
            assert obtido[grupo][chave][0] == quantidade, (grupo, chave)
            assert obtido[grupo][chave][1] == pytest.approx(valor), (grupo, chave)
    assert obtido["por_turno_dia"].keys() == esperado["por_turno_dia"].keys()
    for chave, valor in esperado["por_turno_dia"].items():
        assert obtido["por_turno_dia"][chave] == pytest.approx(valor), chave


@pytest.mark.parametrize("hoje", DATAS_DE_REFERENCIA)
def test_resumo_geral_identico_a_logica_por_linha(db, hoje):
    montar_dataset(db, hoje)
    obtido = do_resumo(crud.resumo_metricas(db, None, hoje))
    _comparar(referencia(db, hoje, None), obtido)


@pytest.mark.parametrize("competencia", [*COMPETENCIAS, "2026"])
def test_resumo_filtrado_por_competencia(db, competencia):
    montar_dataset(db, HOJE)
    obtido = do_resumo(crud.resumo_metricas(db, competencia, HOJE))
    _comparar(referencia(db, HOJE, competencia), obtido)


def test_faixas_nas_viradas_de_idade(db):
    montar_dataset(db, HOJE)
    resumo = crud.resumo_metricas(db, None, HOJE)
    faixas = {i["faixa_etaria"] for i in resumo["por_faixa_etaria"]}
    assert faixas == set(crud.ORDEM_FAIXAS_ETARIAS)


def test_aluno_que_faz_25_hoje_muda_de_faixa(db):
    def cobrar(nascimento):
        aluno = models.Aluno(
            nome="X",
            valor_mensalidade=100,
            dia_vencimento=5,
            data_nascimento=nascimento,
        )
        db.add(aluno)
        db.flush()
        db.add(
            models.Cobranca(
                aluno_id=aluno.id,
                competencia="2026-10",
                valor=100,
                data_vencimento=date(2026, 11, 5),
            )
        )

    cobrar(date(2001, 10, 20))  # faz 25 hoje
    cobrar(date(2001, 10, 21))  # faz 25 amanhã
    cobrar(HOJE + timedelta(days=1))  # nascimento no futuro
    db.commit()
    resumo = crud.resumo_metricas(db, None, HOJE)
    por_faixa = {i["faixa_etaria"]: i["quantidade"] for i in resumo["por_faixa_etaria"]}
    assert por_faixa == {"25-34": 1, "Até 24": 1, "Não informada": 1}


def test_banco_vazio(db):
    resumo = crud.resumo_metricas(db, None, HOJE)
    assert resumo["competencias"] == []
    assert resumo["alunos_ativos"] == 0
    assert resumo["receita_prevista"] == 0
    assert resumo["por_status"] == []
    assert resumo["por_competencia"] == []
    assert resumo["por_faixa_etaria"] == []
    assert resumo["por_modalidade"] == []
    assert resumo["por_turno_dia"] == []


def test_competencias_decrescentes_e_alunos_ativos_nao_dependem_do_filtro(db):
    montar_dataset(db, HOJE)
    geral = crud.resumo_metricas(db, None, HOJE)
    filtrado = crud.resumo_metricas(db, "2026-09", HOJE)
    assert geral["competencias"] == sorted(COMPETENCIAS, reverse=True)
    assert filtrado["competencias"] == geral["competencias"]
    assert filtrado["alunos_ativos"] == geral["alunos_ativos"]
    assert filtrado["receita_prevista"] == geral["receita_prevista"]


def test_detalhamento_limita_ordena_e_conta_o_total(db):
    montar_dataset(db, HOJE)
    total_no_banco = db.query(models.Cobranca).count()
    detalhe = crud.detalhar_cobrancas(db, None, 25)
    assert detalhe["total"] == total_no_banco
    assert len(detalhe["itens"]) == 25
    chaves = [
        (i["competencia"], i["data_vencimento"], i["id"]) for i in detalhe["itens"]
    ]
    assert chaves == sorted(chaves, reverse=True)
    assert all(i["aluno_nome"] for i in detalhe["itens"])


def test_detalhamento_filtrado_por_competencia(db):
    montar_dataset(db, HOJE)
    detalhe = crud.detalhar_cobrancas(db, "2026-08", 1000)
    esperado = db.query(models.Cobranca).filter_by(competencia="2026-08").count()
    assert detalhe["total"] == esperado == len(detalhe["itens"])
    assert {i["competencia"] for i in detalhe["itens"]} == {"2026-08"}


def test_endpoints_respondem_e_validam_parametros(db, client):
    montar_dataset(db, HOJE)
    resposta = client.get("/metricas/resumo")
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["ordem_faixas_etarias"][-1] == "Não informada"
    assert {i["status"] for i in corpo["por_status"]} <= {
        "pendente",
        "pago",
        "atrasado",
        "inadimplente",
    }
    assert client.get("/metricas/resumo?competencia=2026-10").status_code == 200
    assert client.get("/metricas/resumo?competencia=2026").status_code == 200
    assert client.get("/metricas/resumo?competencia=outubro").status_code == 422
    assert client.get("/metricas/resumo?competencia=26").status_code == 422
    detalhe = client.get("/metricas/detalhamento?limite=5")
    assert detalhe.status_code == 200
    assert len(detalhe.json()["itens"]) == 5
    assert client.get("/metricas/detalhamento?limite=0").status_code == 422
    assert client.get("/metricas/detalhamento?limite=1001").status_code == 422
