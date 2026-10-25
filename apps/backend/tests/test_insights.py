from datetime import date

import pytest
from backend import crud, insights, models

HOJE = date(2026, 10, 15)  # meses fechados: até 2026-09
MESES = ["2026-04", "2026-05", "2026-06", "2026-07", "2026-08", "2026-09"]


def _serie(modalidade, valores, situacao="pago", quantidade=30):
    return [
        (modalidade, mes, situacao, v, quantidade)
        for mes, v in zip(MESES, valores, strict=True)
    ]


def _por_codigo(resultado):
    return {(i["codigo"], i["assunto"]): i for i in resultado["itens"]}


def test_modalidade_em_alta_queda_e_estavel():
    linhas = (
        _serie("Natação", [100, 108, 117, 125, 134, 150])
        + _serie("Yoga", [100, 92, 84, 76, 68, 58])
        + _serie("Boxe", [100, 101, 99, 100, 101, 100])
    )
    achados = _por_codigo(insights.gerar_insights(linhas, HOJE))
    assert ("modalidade_alta", "Natação") in achados
    assert ("modalidade_queda", "Yoga") in achados
    assert not any(a == "Boxe" for _, a in achados)
    alta = achados[("modalidade_alta", "Natação")]["dados"]
    # último mês 150 contra média de (117+125+134)/3
    assert alta["variacao"] == pytest.approx(150 / ((117 + 125 + 134) / 3) - 1)
    assert alta["mes"] == "2026-09"


def test_mes_corrente_nao_entra_na_analise():
    linhas = _serie("Boxe", [100, 101, 99, 100, 101, 100])
    linhas.append(("Boxe", "2026-10", "pendente", 5000.0, 30))  # mês em andamento
    resultado = insights.gerar_insights(linhas, HOJE)
    assert resultado["referencia"] == "2026-09"
    assert not any(i["codigo"].startswith("modalidade_") for i in resultado["itens"])


def test_historico_curto_nao_gera_alertas():
    linhas = [("Boxe", mes, "pago", 100.0, 10) for mes in MESES[-3:]]
    resultado = insights.gerar_insights(linhas, HOJE)
    assert resultado["itens"] == []
    assert resultado["meses_analisados"] == 3


def test_oscilacao_sem_tendencia_nao_vira_alerta():
    # último mês alto, mas a série em si não tem tendência (R² baixo)
    linhas = _serie("Pilates", [100, 140, 100, 140, 100, 140])
    codigos = [i["codigo"] for i in insights.gerar_insights(linhas, HOJE)["itens"]]
    assert "modalidade_alta" not in codigos


def test_modalidade_pequena_e_ignorada():
    linhas = _serie("Natação", [1000] * 6) + _serie("Pequena", [1, 2, 3, 4, 5, 9])
    achados = _por_codigo(insights.gerar_insights(linhas, HOJE))
    assert ("modalidade_alta", "Pequena") not in achados


def test_nomes_de_modalidade_sao_normalizados():
    linhas = _serie(" boxe ", [100, 108, 117, 125, 134, 150]) + _serie(
        "BOXE", [100, 108, 117, 125, 134, 150]
    )
    achados = _por_codigo(insights.gerar_insights(linhas, HOJE))
    assert ("modalidade_alta", "Boxe") in achados


def test_inadimplencia_subindo_e_recebimento_baixo():
    linhas = []
    for mes, em_atraso in zip(MESES, [5, 5, 5, 5, 5, 20], strict=True):
        linhas.append(("Boxe", mes, "pago", 100.0 - em_atraso, 50))
        linhas.append(("Boxe", mes, "inadimplente", float(em_atraso), 5))
    achados = _por_codigo(insights.gerar_insights(linhas, HOJE))
    sobe = achados[("inadimplencia_subindo", None)]
    assert sobe["tipo"] == "atencao"
    assert sobe["dados"]["taxa_ultimo"] == pytest.approx(0.20)
    assert sobe["dados"]["taxa_base"] == pytest.approx(0.05)
    recebimento = achados[("recebimento", None)]
    assert recebimento["tipo"] == "atencao"  # 80% < meta de 90%
    assert recebimento["dados"]["taxa"] == pytest.approx(0.80)


def test_inadimplencia_caindo_e_recebimento_ok():
    linhas = []
    for mes, em_atraso in zip(MESES, [20, 20, 20, 20, 20, 5], strict=True):
        linhas.append(("Boxe", mes, "pago", 100.0 - em_atraso, 50))
        linhas.append(("Boxe", mes, "inadimplente", float(em_atraso), 5))
    achados = _por_codigo(insights.gerar_insights(linhas, HOJE))
    assert achados[("inadimplencia_caindo", None)]["tipo"] == "alta"
    assert achados[("recebimento", None)]["tipo"] == "info"


def test_modalidade_com_inadimplencia_acima_da_media():
    linhas = []
    for mes in MESES:
        linhas.append(("Boxe", mes, "pago", 95.0, 40))
        linhas.append(("Boxe", mes, "inadimplente", 5.0, 40))
        linhas.append(("Crossfit", mes, "pago", 70.0, 40))
        linhas.append(("Crossfit", mes, "inadimplente", 30.0, 40))
    achados = _por_codigo(insights.gerar_insights(linhas, HOJE))
    assert ("modalidade_inadimplencia", "Crossfit") in achados
    assert ("modalidade_inadimplencia", "Boxe") not in achados


def test_alertas_de_atencao_vem_primeiro():
    linhas = _serie("Natação", [100, 108, 117, 125, 134, 150])
    linhas += [("Natação", "2026-09", "inadimplente", 400.0, 30)]
    tipos = [i["tipo"] for i in insights.gerar_insights(linhas, HOJE)["itens"]]
    assert tipos == sorted(
        tipos, key={"atencao": 0, "queda": 1, "alta": 2, "info": 3}.get
    )


def test_endpoint_e_consulta_ao_banco(db, client):
    # banco vazio: sem histórico, sem alertas
    vazio = client.get("/metricas/insights")
    assert vazio.status_code == 200
    assert vazio.json() == {"referencia": None, "meses_analisados": 0, "itens": []}

    aluno = models.Aluno(
        nome="A", valor_mensalidade=100, dia_vencimento=5, modalidade="natação"
    )
    db.add(aluno)
    db.flush()
    hoje = date.today()
    competencias = []
    for deslocamento, valor in enumerate([100, 110, 120, 130, 140, 160], start=1):
        total = hoje.year * 12 + (hoje.month - 1) - (7 - deslocamento)
        competencia = f"{total // 12:04d}-{total % 12 + 1:02d}"
        competencias.append(competencia)
        db.add(
            models.Cobranca(
                aluno_id=aluno.id,
                competencia=competencia,
                valor=valor,
                data_vencimento=hoje,
                status=models.StatusCobranca.PAGO,
            )
        )
    db.commit()
    resultado = crud.insights_metricas(db, hoje=hoje)
    assert resultado["meses_analisados"] == 6
    assert any(
        i["codigo"] == "modalidade_alta" and i["assunto"] == "Natação"
        for i in resultado["itens"]
    )
    resposta = client.get("/metricas/insights")
    assert resposta.status_code == 200
    assert resposta.json()["meses_analisados"] == 6

    # filtro por mês: a análise termina nesse mês (o 5º dos 6)
    ate_quinto = client.get(
        "/metricas/insights", params={"competencia": competencias[4]}
    ).json()
    assert ate_quinto["referencia"] == competencias[4]
    assert ate_quinto["meses_analisados"] == 5

    # filtro por ano: considera só as competências até dezembro daquele ano
    ano_do_primeiro = competencias[0][:4]
    ate_o_ano = client.get(
        "/metricas/insights", params={"competencia": ano_do_primeiro}
    ).json()
    esperadas = [c for c in competencias if c[:4] <= ano_do_primeiro]
    assert ate_o_ano["meses_analisados"] == len(esperadas)
    assert ate_o_ano["referencia"] == esperadas[-1]
