import math

import altair as alt
import pandas as pd
import streamlit as st
from frontend.api.cliente import (
    APIError,
    limpar_cache_metricas,
    obter_curva_vintage,
    obter_detalhamento_metricas,
    obter_insights,
    obter_resumo_metricas,
)
from frontend.ui import (
    EIXO_MESES_EXPR,
    EIXO_NUMERO_EXPR,
    abreviar_numero,
    api_status,
    apply_theme,
    formatar_competencia,
    formatar_inteiro,
    formatar_moeda,
    formatar_moeda_inteira,
    insights_box,
    metric_grid,
    page_header,
    paleta_atual,
    rotulo_mes,
    section_title,
    sidebar_brand,
)

STATUS_LABELS = {
    "pago": "Pagas",
    "pendente": "Pendentes",
    "atrasado": "Atrasadas",
    "inadimplente": "Inadimplentes",
}
# Cores vêm da paleta escolhida no seletor da barra lateral (ui.PALETAS).
PALETA = paleta_atual()
STATUS_COLORS = {
    "Pagas": PALETA["pago"],
    "Pendentes": PALETA["pendente"],
    "Atrasadas": PALETA["atrasado"],
    "Inadimplentes": PALETA["inadimplente"],
}
LIMITE_DETALHAMENTO = 200
COR_PREVISTO = PALETA["previsto"]
COR_RECEBIDO = PALETA["recebido"]
MESES_NA_EVOLUCAO = 12
# Eixo dos meses: todos os rótulos aparecem (sem esconder alternados), em negrito
# e com marca no eixo; só o primeiro mês e janeiro mostram o ano ("Nov 2025",
# "Dez", "Jan 2026", "Fev"), para caber em janelas estreitas. O ano vai numa
# segunda linha, sob o mês.
EIXO_MESES = alt.Axis(
    labelAngle=0,
    labelOverlap=False,
    labelFontWeight="bold",
    labelFontSize=10,
    ticks=True,
    tickSize=5,
    labelExpr=EIXO_MESES_EXPR,
)
LIMIAR_RECEBIMENTO_BOM = 90
LIMIAR_RECEBIMENTO_ATENCAO = 70


def _passo_do_eixo(maximo: float, marcas: int = 5) -> float:
    """Passo "redondo" (1, 2, 2,5 ou 5 x 10^n) para ~`marcas` divisões do eixo."""
    bruto = maximo / marcas
    potencia = 10 ** math.floor(math.log10(bruto)) if bruto > 0 else 1
    for fator in (1, 2, 2.5, 5, 10):
        if bruto <= fator * potencia:
            return fator * potencia
    return 10 * potencia


st.set_page_config(
    page_title="Métricas Financeiras - PagControl",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="auto",
)

apply_theme()
sidebar_brand()

page_header(
    "Desempenho financeiro",
    "Métricas e inadimplência",
    (
        "Indicadores calculados com os dados atuais de alunos e cobranças "
        "registrados na API do PagControl."
    ),
)

if st.sidebar.button("🔄 Atualizar dados", width="stretch"):
    limpar_cache_metricas()
    st.rerun()

# Os totais chegam já agrupados pelo banco (GET /metricas/resumo): a página
# não baixa mais a tabela de cobranças inteira, só os números que desenha.
try:
    resumo_geral = obter_resumo_metricas()
except APIError as exc:
    api_status(False)
    st.error(str(exc))
    st.info(
        "Inicie o backend com `uv run --package backend uvicorn backend.api:app --reload` "
        "e recarregue esta página."
    )
    st.stop()

api_status(True)
st.caption("Dados carregados diretamente da API · nenhuma métrica demonstrativa")

competencias_disponiveis = resumo_geral["competencias"]
anos_disponiveis = sorted({c[:4] for c in competencias_disponiveis}, reverse=True)
opcoes_periodo = ["Período completo"] + [f"Acumulado {ano}" for ano in anos_disponiveis]

# Dois filtros lado a lado: o 1º escolhe o período (tudo ou o acumulado de um ano);
# o 2º escolhe só um mês e, quando usado, vale no lugar do 1º.
coluna_periodo, coluna_mes = st.columns(2, gap="medium")
with coluna_periodo:
    periodo_selecionado = st.selectbox(
        "Período",
        options=opcoes_periodo,
        key="filtro_periodo",
        help=(
            "'Período completo' soma todas as cobranças já geradas; 'Acumulado' soma "
            "as competências de um ano. Para ver um único mês, use o filtro ao lado."
        ),
    )
ano_selecionado = (
    periodo_selecionado.removeprefix("Acumulado ")
    if periodo_selecionado.startswith("Acumulado ")
    else None
)
meses_do_filtro = [
    c
    for c in competencias_disponiveis
    if ano_selecionado is None or c.startswith(ano_selecionado)
]
mes_por_opcao = {formatar_competencia(c): c for c in meses_do_filtro}
with coluna_mes:
    mes_selecionado = st.selectbox(
        "Mês",
        options=["Todos os meses", *mes_por_opcao],
        key="filtro_mes",
        help=(
            "Filtra por um único mês cobrado (competência). Com 'Todos os meses', "
            "vale o filtro de período. Se o período for um acumulado, só aparecem os "
            "meses daquele ano."
        ),
    )

# periodo_filtro: "AAAA-MM" (um mês), "AAAA" (acumulado do ano) ou None (tudo).
competencia_filtro = mes_por_opcao.get(mes_selecionado)
periodo_filtro = competencia_filtro or ano_selecionado
try:
    resumo = obter_resumo_metricas(periodo_filtro) if periodo_filtro else resumo_geral
    detalhamento = obter_detalhamento_metricas(periodo_filtro, LIMITE_DETALHAMENTO)
    vintage = obter_curva_vintage()
    insights = obter_insights(periodo_filtro)
except APIError as exc:
    st.error(str(exc))
    st.stop()

por_status = {item["status"]: item for item in resumo["por_status"]}
total_cobrancas = sum(item["quantidade"] for item in resumo["por_status"])

if competencia_filtro:
    st.caption(
        f"Exibindo apenas a competência **{mes_selecionado}** "
        f"({formatar_inteiro(total_cobrancas)} cobrança(s))."
    )
elif periodo_filtro:
    st.caption(
        f"Exibindo o acumulado de **{periodo_filtro}**: todas as "
        f"{formatar_inteiro(total_cobrancas)} cobranças das competências desse ano."
    )
else:
    st.caption(
        f"Exibindo o período completo: todas as {formatar_inteiro(total_cobrancas)} cobranças já "
        "geradas, de qualquer competência."
    )

alunos_ativos = resumo["alunos_ativos"]
receita_prevista = resumo["receita_prevista"]
total_inadimplentes = sum(
    por_status[status]["quantidade"]
    for status in ("atrasado", "inadimplente")
    if status in por_status
)
taxa_inadimplencia = (
    (total_inadimplentes / total_cobrancas) * 100 if total_cobrancas else 0.0
)

metric_grid(
    [
        {
            "label": "Alunos ativos",
            "value": formatar_inteiro(alunos_ativos),
            "delta": "Dados da API",
        },
        {
            "label": "Receita mensal prevista",
            "value": formatar_moeda_inteira(receita_prevista),
            "delta": "Mensalidades ativas",
            "accent": PALETA["card_2"],
        },
        {
            "label": "Cobranças registradas",
            "value": formatar_inteiro(total_cobrancas),
            "delta": "Carteira completa",
            "accent": PALETA["card_3"],
        },
        {
            "label": "Taxa de inadimplência",
            "value": f"{taxa_inadimplencia:.1f}%".replace(".", ","),
            "delta": "Atrasadas + inadimplentes",
            "accent": PALETA["card_4"],
            "attention": total_inadimplentes > 0,
        },
    ]
)


def _pct(valor: float) -> str:
    return f"{valor * 100:.1f}%".replace(".", ",")


def montar_insights(dados: dict) -> list[dict]:
    """Converte os números do resumo analítico em frases prontas para a caixa."""
    frases = []
    for item in dados["itens"]:
        d = item["dados"]
        mes = formatar_competencia(d["mes"]) if "mes" in d else ""
        assunto = item["assunto"]
        match item["codigo"]:
            case "modalidade_alta":
                titulo = f"{assunto} em alta"
                texto = (
                    f"faturou {abreviar_numero(d['ultimo'], moeda=True)} em {mes}, "
                    f"{_pct(abs(d['variacao']))} acima da média dos 3 meses anteriores "
                    f"({abreviar_numero(d['base'], moeda=True)}), com tendência de "
                    f"crescimento nos últimos {int(d['meses'])} meses."
                )
            case "modalidade_queda":
                titulo = f"{assunto} em queda"
                texto = (
                    f"faturou {abreviar_numero(d['ultimo'], moeda=True)} em {mes}, "
                    f"{_pct(abs(d['variacao']))} abaixo da média dos 3 meses anteriores "
                    f"({abreviar_numero(d['base'], moeda=True)}), com tendência de "
                    f"queda nos últimos {int(d['meses'])} meses."
                )
            case "inadimplencia_subindo":
                titulo = "Atenção com a inadimplência"
                texto = (
                    f"a taxa de cobranças atrasadas e inadimplentes subiu de "
                    f"{_pct(d['taxa_base'])} (média dos 3 meses anteriores) para "
                    f"{_pct(d['taxa_ultimo'])} em {mes}."
                )
            case "inadimplencia_caindo":
                titulo = "Inadimplência em queda"
                texto = (
                    f"a taxa de cobranças atrasadas e inadimplentes caiu de "
                    f"{_pct(d['taxa_base'])} (média dos 3 meses anteriores) para "
                    f"{_pct(d['taxa_ultimo'])} em {mes}."
                )
            case "recebimento":
                abaixo = d["taxa"] < d["meta"]
                titulo = "Atenção ao recebimento" if abaixo else "Recebimento do mês"
                texto = (
                    f"em {mes}, {_pct(d['taxa'])} do valor cobrado foi recebido "
                    f"({abreviar_numero(d['valor_pago'], moeda=True)}), "
                    + (
                        f"abaixo da meta de {_pct(d['meta'])}."
                        if abaixo
                        else f"dentro da meta de {_pct(d['meta'])}."
                    )
                )
            case "modalidade_inadimplencia":
                titulo = f"Atenção com {assunto}"
                texto = (
                    f"{_pct(d['taxa'])} do valor cobrado está em atraso ou inadimplente, "
                    f"acima da média geral de {_pct(d['taxa_geral'])} nos últimos 3 meses "
                    f"fechados ({formatar_inteiro(d['cobrancas'])} cobranças)."
                )
            case _:
                continue
        frases.append({"tipo": item["tipo"], "titulo": titulo, "texto": texto})
    return frases


frases_insights = montar_insights(insights)
if insights["meses_analisados"] < 4:
    frases_insights = [
        {
            "tipo": "info",
            "titulo": "Histórico curto",
            "texto": "ainda não há 4 meses fechados para comparar tendências.",
        }
    ]
    rodape_insights = "A análise começa quando houver ao menos 4 meses fechados."
else:
    if not frases_insights:
        frases_insights = [
            {
                "tipo": "info",
                "titulo": "Sem alertas",
                "texto": "nenhuma variação relevante nos últimos meses fechados.",
            }
        ]
    rodape_insights = (
        f"Baseado em {insights['meses_analisados']} meses fechados, até "
        f"{formatar_competencia(insights['referencia'])}: compara o último mês com a "
        "média dos 3 anteriores e confere a tendência linear. É um indicativo para "
        "apoiar decisões, não uma previsão."
    )
insights_box(frases_insights, rodape_insights)

section_title("Distribuição das cobranças")

resumo_status = [
    {
        "Status": status_label,
        "Quantidade": por_status.get(status_api, {}).get("quantidade", 0),
        "Valor (R$)": por_status.get(status_api, {}).get("valor", 0.0),
    }
    for status_api, status_label in STATUS_LABELS.items()
]

dados_cobranca = pd.DataFrame(resumo_status).sort_values("Valor (R$)", ascending=False)
dados_cobranca["Quantidade_txt"] = dados_cobranca["Quantidade"].apply(formatar_inteiro)
dados_cobranca["Valor_txt"] = dados_cobranca["Valor (R$)"].apply(formatar_moeda)
dados_cobranca["Rótulo"] = dados_cobranca.apply(
    lambda linha: (
        f"{abreviar_numero(linha['Valor (R$)'], moeda=True)}"
        f" · {formatar_inteiro(linha['Quantidade'])}"
    ),
    axis=1,
)

if not total_cobrancas:
    st.info(
        "Ainda não existem cobranças registradas. Os indicadores financeiros "
        "serão preenchidos assim que o backend possuir dados."
    )
else:
    ordem_status = dados_cobranca["Status"].tolist()
    eixo_valor_status = alt.Axis(
        gridColor="#eef2f6", titlePadding=14, labelExpr=EIXO_NUMERO_EXPR
    )
    barras_status = (
        alt.Chart(dados_cobranca)
        .mark_bar(
            cornerRadiusTopLeft=7,
            cornerRadiusTopRight=7,
            width=alt.RelativeBandSize(0.6),
        )
        .encode(
            x=alt.X(
                "Status:N",
                sort=ordem_status,
                title=None,
                axis=alt.Axis(labelAngle=0, labelPadding=12),
            ),
            y=alt.Y(
                "Valor (R$):Q",
                title="Valor (R$)",
                axis=eixo_valor_status,
            ),
            color=alt.Color(
                "Status:N",
                scale=alt.Scale(
                    domain=list(STATUS_COLORS),
                    range=list(STATUS_COLORS.values()),
                ),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("Status:N", title="Situação"),
                alt.Tooltip("Quantidade_txt:N", title="Cobranças"),
                alt.Tooltip("Valor_txt:N", title="Valor"),
            ],
        )
    )
    rotulos_status = (
        alt.Chart(dados_cobranca)
        .mark_text(baseline="bottom", dy=-4, fontWeight="bold", fontSize=11)
        .encode(
            x=alt.X("Status:N", sort=ordem_status),
            y=alt.Y("Valor (R$):Q", title="Valor (R$)", axis=eixo_valor_status),
            text="Rótulo:N",
            color=alt.value("#334155"),
        )
    )
    st.altair_chart(
        (barras_status + rotulos_status)
        .properties(height=340)
        .configure_view(strokeWidth=0),
        width="stretch",
    )
    st.caption(
        "Valor e quantidade de cobranças (R$ · nº de cobranças) em cada situação "
        "da carteira atual."
    )

section_title("Evolução mensal — previsto x recebido")

# Previsto = tudo o que foi cobrado na competência (já com juros); recebido =
# só o que está pago. Usa o resumo geral: os meses aparecem lado a lado.
por_mes: dict[str, dict[str, float]] = {}
for item in resumo_geral["por_competencia"]:
    mes = por_mes.setdefault(item["competencia"], {"previsto": 0.0, "recebido": 0.0})
    mes["previsto"] += item["valor"]
    if item["status"] == "pago":
        mes["recebido"] += item["valor"]
meses_evolucao = sorted(por_mes)[-MESES_NA_EVOLUCAO:]

if not meses_evolucao:
    st.caption("Ainda não há cobranças suficientes para a evolução mensal.")
else:
    ordem_meses = [rotulo_mes(c) for c in meses_evolucao]
    destaque = rotulo_mes(competencia_filtro or meses_evolucao[-1])
    linhas_evolucao = []
    linhas_percentual = []
    for competencia in meses_evolucao:
        previsto = por_mes[competencia]["previsto"]
        recebido = por_mes[competencia]["recebido"]
        percentual = recebido / previsto * 100 if previsto else 0.0
        faixa_cor = (
            "bom"
            if percentual >= LIMIAR_RECEBIMENTO_BOM
            else "atencao"
            if percentual >= LIMIAR_RECEBIMENTO_ATENCAO
            else "baixo"
        )
        for serie, valor_mes in (("Previsto", previsto), ("Recebido", recebido)):
            linhas_evolucao.append(
                {
                    "Mês": rotulo_mes(competencia),
                    "Série": serie,
                    "Valor": valor_mes,
                    "Valor_txt": formatar_moeda(valor_mes),
                    "Rótulo": abreviar_numero(valor_mes),
                    "Percentual": percentual,
                }
            )
        linhas_percentual.append(
            {
                "Mês": rotulo_mes(competencia),
                "Texto": f"{percentual:.0f}%",
                "Faixa": faixa_cor,
            }
        )
    df_evolucao = pd.DataFrame(linhas_evolucao)
    df_percentual = pd.DataFrame(linhas_percentual)
    altura_evolucao = 340
    topo = df_evolucao["Valor"].max() * 1.18 or 1.0
    # A linha de % fica logo abaixo do zero, dentro do mesmo gráfico (assim ele
    # acompanha a largura da janela, o que um gráfico empilhado não faz).
    recuo = topo * 0.09
    escala_y = alt.Scale(domain=[-recuo, topo])
    passo = _passo_do_eixo(topo)
    marcas_y = [passo * i for i in range(int(topo // passo) + 1)]
    eixo_y = alt.Axis(
        values=marcas_y,
        gridColor="#eef2f6",
        labelExpr=EIXO_NUMERO_EXPR,
    )

    df_percentual["Y"] = -recuo / 2
    df_percentual["Cor"] = df_percentual["Faixa"].map(
        {"bom": "#2f855a", "atencao": "#b7791f", "baixo": "#c53030"}
    )
    eixo_mes = alt.X("Mês:N", sort=ordem_meses, title=None, axis=EIXO_MESES)
    fundo_destaque = (
        alt.Chart(pd.DataFrame({"Mês": [destaque], "Início": [-recuo], "Fim": [topo]}))
        .mark_bar(color=PALETA["realce"], width=alt.RelativeBandSize(1), cornerRadius=6)
        .encode(
            x=alt.X("Mês:N", sort=ordem_meses),
            y=alt.Y("Início:Q", title="R$", scale=escala_y, axis=eixo_y),
            y2="Fim:Q",
        )
    )
    linha_zero = (
        alt.Chart(pd.DataFrame({"zero": [0]}))
        .mark_rule(color="#cbd5e1")
        .encode(y=alt.Y("zero:Q", title="R$", scale=escala_y, axis=eixo_y))
    )
    barras_evolucao = (
        alt.Chart(df_evolucao)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=eixo_mes,
            xOffset=alt.XOffset("Série:N", sort=["Previsto", "Recebido"]),
            y=alt.Y("Valor:Q", title="R$", scale=escala_y, axis=eixo_y),
            color=alt.Color(
                "Série:N",
                scale=alt.Scale(
                    domain=["Previsto", "Recebido"], range=[COR_PREVISTO, COR_RECEBIDO]
                ),
                legend=alt.Legend(title=None, orient="top-left"),
            ),
            tooltip=[
                alt.Tooltip("Mês:N"),
                alt.Tooltip("Série:N"),
                alt.Tooltip("Valor_txt:N", title="Valor"),
                alt.Tooltip("Percentual:Q", title="% recebido", format=".1f"),
            ],
        )
    )
    # Rótulos só no "Recebido" e no mês destacado: com 12 meses e 2 barras cada, rotular
    # tudo sobrepõe os textos em janelas estreitas (o previsto fica no tooltip).
    df_rotulos = df_evolucao[
        (df_evolucao["Série"] == "Recebido") | (df_evolucao["Mês"] == destaque)
    ]
    valores_evolucao = (
        alt.Chart(df_rotulos)
        .mark_text(angle=270, align="left", baseline="middle", fontSize=10, dy=-4)
        .encode(
            x=eixo_mes,
            xOffset=alt.XOffset("Série:N", sort=["Previsto", "Recebido"]),
            y=alt.Y("Valor:Q", title="R$", scale=escala_y, axis=eixo_y),
            text="Rótulo:N",
            color=alt.value("#475569"),
        )
    )
    percentuais = (
        alt.Chart(df_percentual)
        .mark_text(fontWeight="bold", fontSize=12)
        .encode(
            x=eixo_mes,
            y=alt.Y("Y:Q", title="R$", scale=escala_y, axis=eixo_y),
            text="Texto:N",
            color=alt.Color("Cor:N", scale=None, legend=None),
        )
    )
    st.altair_chart(
        (fundo_destaque + linha_zero + barras_evolucao + valores_evolucao + percentuais)
        .properties(height=altura_evolucao)
        .configure_view(strokeWidth=0),
        width="stretch",
    )

    acumulado_previsto = sum(por_mes[c]["previsto"] for c in meses_evolucao)
    acumulado_recebido = sum(por_mes[c]["recebido"] for c in meses_evolucao)
    percentual_acumulado = (
        acumulado_recebido / acumulado_previsto * 100 if acumulado_previsto else 0.0
    )
    texto_acumulado = (
        f"Acumulado dos {len(meses_evolucao)} meses: previsto "
        f"{abreviar_numero(acumulado_previsto, moeda=True)} · recebido "
        f"{abreviar_numero(acumulado_recebido, moeda=True)} "
        f"({percentual_acumulado:.0f}%). A linha de % sob cada mês é recebido ÷ previsto "
        f"(verde ≥ {LIMIAR_RECEBIMENTO_BOM}%, amarelo ≥ {LIMIAR_RECEBIMENTO_ATENCAO}%, "
        "vermelho abaixo). O mês destacado segue o filtro de período — sem filtro, "
        "é o mais recente, que ainda está em andamento."
    )
    st.caption(texto_acumulado.replace("$", r"\$"))

section_title("Da carteira ao recebido")

if not total_cobrancas:
    st.caption("Ainda não há cobranças suficientes para a cascata da carteira.")
else:
    valor_status = {
        status: por_status.get(status, {}).get("valor", 0.0) for status in STATUS_LABELS
    }
    total_carteira = sum(valor_status.values())
    restante = total_carteira
    # Quando as quedas são pequenas perto do total, o eixo parte de um valor
    # próximo ao recebido (e a legenda avisa): senão as duas barras grandes
    # ocupam o gráfico todo e as quedas viram faixas finas.
    queda_total = total_carteira - valor_status["pago"]
    destacar_quedas = total_carteira > 0 and queda_total / total_carteira < 0.25
    piso_eixo = 0.0
    topo_eixo = total_carteira * 1.08 or 1.0
    if destacar_quedas:
        passo_eixo = _passo_do_eixo(
            topo_eixo - max(0.0, valor_status["pago"] - queda_total * 3)
        )
        piso_eixo = max(
            0.0,
            math.floor((valor_status["pago"] - queda_total * 3) / passo_eixo)
            * passo_eixo,
        )
    else:
        passo_eixo = _passo_do_eixo(topo_eixo)
    marcas_cascata = [
        piso_eixo + passo_eixo * i
        for i in range(int((topo_eixo - piso_eixo) // passo_eixo) + 1)
    ]
    escala_cascata = alt.Scale(domain=[piso_eixo, topo_eixo], nice=False)
    eixo_cascata = alt.Axis(
        values=marcas_cascata, gridColor="#eef2f6", labelExpr=EIXO_NUMERO_EXPR
    )
    linhas_cascata = [
        {
            "Etapa": "Carteira",
            "Início": piso_eixo,
            "Fim": total_carteira,
            "Rótulo": abreviar_numero(total_carteira, moeda=True),
            "Cor": "Carteira",
        }
    ]
    for status in ("pendente", "atrasado", "inadimplente"):
        queda = valor_status[status]
        linhas_cascata.append(
            {
                "Etapa": STATUS_LABELS[status],
                "Início": restante - queda,
                "Fim": restante,
                "Rótulo": "-" + abreviar_numero(queda, moeda=True),
                "Cor": STATUS_LABELS[status],
            }
        )
        restante -= queda
    linhas_cascata.append(
        {
            "Etapa": "Recebido",
            "Início": piso_eixo,
            "Fim": valor_status["pago"],
            "Rótulo": abreviar_numero(valor_status["pago"], moeda=True),
            "Cor": "Recebido",
        }
    )
    df_cascata = pd.DataFrame(linhas_cascata)
    ordem_cascata = df_cascata["Etapa"].tolist()
    cores_cascata = {
        "Carteira": COR_PREVISTO,
        "Pendentes": STATUS_COLORS["Pendentes"],
        "Atrasadas": STATUS_COLORS["Atrasadas"],
        "Inadimplentes": STATUS_COLORS["Inadimplentes"],
        "Recebido": STATUS_COLORS["Pagas"],
    }
    base_cascata = alt.Chart(df_cascata).encode(
        x=alt.X("Etapa:N", sort=ordem_cascata, title=None, axis=alt.Axis(labelAngle=0))
    )
    barras_cascata = base_cascata.mark_bar(
        cornerRadius=4, width=alt.RelativeBandSize(0.45), clip=True
    ).encode(
        y=alt.Y(
            "Início:Q",
            title="R$",
            scale=escala_cascata,
            axis=eixo_cascata,
        ),
        y2="Fim:Q",
        color=alt.Color(
            "Cor:N",
            scale=alt.Scale(
                domain=list(cores_cascata), range=list(cores_cascata.values())
            ),
            legend=None,
        ),
        tooltip=[
            alt.Tooltip("Etapa:N"),
            alt.Tooltip("Rótulo:N", title="Valor"),
        ],
    )
    rotulos_cascata = base_cascata.mark_text(
        baseline="bottom", dy=-4, fontWeight="bold", fontSize=12
    ).encode(
        y=alt.Y("Fim:Q", title="R$", scale=escala_cascata, axis=eixo_cascata),
        text="Rótulo:N",
        color=alt.value("#334155"),
    )

    taxa_recebimento = (
        valor_status["pago"] / total_carteira * 100 if total_carteira else 0.0
    )
    a_receber = (
        valor_status["pendente"]
        + valor_status["atrasado"]
        + valor_status["inadimplente"]
    )
    # Métricas em linha e gráfico em largura total: lado a lado, o gráfico ficava
    # espremido (rótulos sobrepostos) em janelas estreitas.
    metrica_taxa, metrica_aberto = st.columns(2, gap="medium")
    metrica_taxa.metric(
        "Taxa de recebimento", f"{taxa_recebimento:.1f}%".replace(".", ",")
    )
    metrica_aberto.metric("Ainda a receber", abreviar_numero(a_receber, moeda=True))
    st.altair_chart(
        (barras_cascata + rotulos_cascata)
        .properties(height=300)
        .configure_view(strokeWidth=0),
        width="stretch",
    )
    aviso_eixo = (
        f" O eixo vertical começa em {abreviar_numero(piso_eixo, moeda=True)} "
        "(não em zero) para destacar as quedas."
        if piso_eixo > 0
        else ""
    )
    st.caption(
        "Parte do total cobrado e desce pelo que ainda está pendente, atrasado "
        "ou inadimplente, até chegar ao que já foi recebido." + aviso_eixo
    )

section_title("Inadimplência por faixa etária")

# A faixa de cada aluno é calculada no banco (crud.resumo_metricas); a página
# só recebe a ordem de exibição das faixas.
ORDEM_FAIXAS_ETARIAS = resumo["ordem_faixas_etarias"]

if not total_cobrancas:
    st.caption("Ainda não há cobranças suficientes para cruzar com faixa etária.")
else:
    resumo_idade = pd.DataFrame(
        [
            {
                "Faixa etária": item["faixa_etaria"],
                "Situação": STATUS_LABELS.get(item["status"], item["status"].title()),
                "Inadimplente": item["status"] in {"atrasado", "inadimplente"},
                "Quantidade": item["quantidade"],
                "Valor": item["valor"],
            }
            for item in resumo["por_faixa_etaria"]
        ]
    )

    resumo_idade["Quantidade_txt"] = resumo_idade["Quantidade"].apply(formatar_inteiro)
    resumo_idade["Valor_txt"] = resumo_idade["Valor"].apply(formatar_moeda)
    resumo_idade["Inadimplentes"] = resumo_idade["Quantidade"].where(
        resumo_idade["Inadimplente"], 0
    )
    taxa_por_faixa = (
        resumo_idade.groupby("Faixa etária")
        .agg(Total=("Quantidade", "sum"), Inadimplentes=("Inadimplentes", "sum"))
        .reset_index()
    )
    taxa_por_faixa["Taxa"] = (
        taxa_por_faixa["Inadimplentes"] / taxa_por_faixa["Total"] * 100
    )
    taxa_por_faixa["Rótulo"] = taxa_por_faixa["Taxa"].apply(
        lambda v: f"{v:.1f}%".replace(".", ",")
    )

    eixo_cobrancas = alt.Axis(labelExpr=EIXO_NUMERO_EXPR)
    eixo_faixa = alt.X("Faixa etária:N", sort=ORDEM_FAIXAS_ETARIAS, title=None)
    barras_idade = (
        alt.Chart(resumo_idade)
        .mark_bar()
        .encode(
            x=eixo_faixa,
            y=alt.Y("Quantidade:Q", title="Cobranças", axis=eixo_cobrancas),
            color=alt.Color(
                "Situação:N",
                scale=alt.Scale(
                    domain=list(STATUS_COLORS), range=list(STATUS_COLORS.values())
                ),
                legend=alt.Legend(title=None, orient="bottom"),
            ),
            tooltip=[
                alt.Tooltip("Faixa etária:N"),
                alt.Tooltip("Situação:N", title="Situação"),
                alt.Tooltip("Quantidade_txt:N", title="Cobranças"),
                alt.Tooltip("Valor_txt:N", title="Valor"),
            ],
        )
    )
    # Taxa de inadimplência (atrasadas + inadimplentes ÷ total) no topo de cada barra.
    taxas_idade = (
        alt.Chart(taxa_por_faixa)
        .mark_text(baseline="bottom", dy=-4, fontWeight="bold", fontSize=11)
        .encode(
            x=eixo_faixa,
            y=alt.Y("Total:Q", title="Cobranças", axis=eixo_cobrancas),
            text="Rótulo:N",
            color=alt.value("#334155"),
        )
    )
    st.altair_chart(
        (barras_idade + taxas_idade)
        .properties(height=340)
        .configure_view(strokeWidth=0),
        width="stretch",
    )
    st.caption(
        "O percentual no topo de cada barra é a taxa de inadimplência da faixa "
        "(atrasadas + inadimplentes sobre o total de cobranças). Alunos sem data de "
        "nascimento cadastrada aparecem em 'Não informada' — preencha esse campo na "
        "edição do aluno para refinar a análise."
    )

section_title("Faturamento por modalidade")

MODALIDADE_COR_PRINCIPAL = PALETA["recebido"]
MODALIDADE_COR_SECUNDARIA = PALETA["previsto"]


def normalizar_modalidade(valor: str | None) -> str:
    if not valor or not valor.strip():
        return "Não informada"
    return valor.strip().title()


mes_atual = pd.Timestamp.today().strftime("%Y-%m")
mes_anterior = (pd.Timestamp.today().replace(day=1) - pd.Timedelta(days=1)).strftime(
    "%Y-%m"
)

if not total_cobrancas:
    st.caption(
        "Ainda não há cobranças suficientes para calcular faturamento por modalidade."
    )
else:
    # O banco agrupa pelo texto cru da modalidade; a normalização (espaços e
    # maiúsculas) é feita aqui e os grupos que colidem são somados de novo.
    df_modalidade = pd.DataFrame(
        [
            {
                "Modalidade": normalizar_modalidade(item["modalidade"]),
                "Competência": item["competencia"],
                "Quantidade": item["quantidade"],
                "Valor": item["valor"],
            }
            for item in resumo["por_modalidade"]
        ]
    )

    faturamento_total = (
        df_modalidade.groupby("Modalidade", as_index=False)
        .agg(Quantidade=("Quantidade", "sum"), Faturamento=("Valor", "sum"))
        .sort_values("Faturamento", ascending=False)
    )

    atual_por_modalidade = (
        df_modalidade[df_modalidade["Competência"] == mes_atual]
        .groupby("Modalidade")["Valor"]
        .sum()
    )
    anterior_por_modalidade = (
        df_modalidade[df_modalidade["Competência"] == mes_anterior]
        .groupby("Modalidade")["Valor"]
        .sum()
    )

    def calcular_variacao(modalidade: str) -> float | None:
        valor_atual = atual_por_modalidade.get(modalidade, 0.0)
        valor_anterior = anterior_por_modalidade.get(modalidade, 0.0)
        if valor_anterior == 0:
            return None
        return ((valor_atual - valor_anterior) / valor_anterior) * 100

    faturamento_total["Variação (%)"] = faturamento_total["Modalidade"].apply(
        calcular_variacao
    )

    # Destaca só a modalidade de maior faturamento; o resto fica num tom
    # neutro, pra não competir visualmente numa lista com muitas categorias.
    maior_modalidade = faturamento_total.iloc[0]["Modalidade"]
    faturamento_total["Destaque"] = faturamento_total["Modalidade"] == maior_modalidade

    # Barras horizontais: com muitas modalidades, rótulos verticais não
    # colidem quando a coluna estreita (só a altura do gráfico cresce),
    # ao contrário de barras verticais com o eixo de categorias apertado.
    altura_grafico = max(220, 34 * len(faturamento_total))

    ordem_modalidades = faturamento_total["Modalidade"].tolist()
    total_modalidades = faturamento_total["Faturamento"].sum() or 1.0
    faturamento_total["Participação"] = (
        faturamento_total["Faturamento"] / total_modalidades * 100
    )
    faturamento_total["Rótulo"] = faturamento_total.apply(
        lambda linha: (
            f"{abreviar_numero(linha['Faturamento'], moeda=True)} · "
            + f"{linha['Participação']:.1f}%".replace(".", ",")
        ),
        axis=1,
    )
    faturamento_total["Quantidade_txt"] = faturamento_total["Quantidade"].apply(
        formatar_inteiro
    )
    faturamento_total["Faturamento_txt"] = faturamento_total["Faturamento"].apply(
        formatar_moeda
    )
    faturamento_total["Variação_txt"] = faturamento_total["Variação (%)"].apply(
        lambda v: "—" if v is None or pd.isna(v) else f"{v:+.1f}%".replace(".", ",")
    )
    limite_x_modalidade = faturamento_total["Faturamento"].max() * 1.45
    barras_modalidade = (
        alt.Chart(faturamento_total)
        .mark_bar(cornerRadiusTopRight=6, cornerRadiusBottomRight=6, size=22)
        .encode(
            y=alt.Y(
                "Modalidade:N",
                sort=ordem_modalidades,
                title=None,
                axis=alt.Axis(labelPadding=8),
            ),
            x=alt.X(
                "Faturamento:Q",
                title="Faturamento (R$)",
                scale=alt.Scale(domain=[0, limite_x_modalidade]),
                axis=alt.Axis(
                    gridColor="#eef2f6", titlePadding=10, labelExpr=EIXO_NUMERO_EXPR
                ),
            ),
            color=alt.Color(
                "Destaque:N",
                scale=alt.Scale(
                    domain=[True, False],
                    range=[MODALIDADE_COR_PRINCIPAL, MODALIDADE_COR_SECUNDARIA],
                ),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("Modalidade:N"),
                alt.Tooltip("Quantidade_txt:N", title="Cobranças"),
                alt.Tooltip("Faturamento_txt:N", title="Faturamento"),
                alt.Tooltip("Variação_txt:N", title="Var. vs mês anterior"),
            ],
        )
        .properties(height=altura_grafico)
    )
    rotulos_modalidade = (
        alt.Chart(faturamento_total)
        .mark_text(align="left", dx=6, fontSize=11, color="#475569")
        .encode(
            y=alt.Y("Modalidade:N", sort=ordem_modalidades),
            x=alt.X("Faturamento:Q", scale=alt.Scale(domain=[0, limite_x_modalidade])),
            text="Rótulo:N",
        )
    )
    chart_modalidade = (barras_modalidade + rotulos_modalidade).configure_view(
        strokeWidth=0
    )

    st.altair_chart(chart_modalidade, width="stretch")
    st.caption(
        "Valor faturado e participação de cada modalidade. Passe o mouse sobre a "
        "barra para ver a variação em relação ao mês anterior (calculada comparando "
        "o mês atual com o anterior); modalidades sem cobrança no mês anterior "
        "aparecem sem variação (—)."
    )

TURNO_LABELS = {
    "manha": "Manhã (06h-12h)",
    "tarde": "Tarde (12h-18h)",
    "noite": "Noite (18h-00h)",
}


def normalizar_turno(valor: str | None) -> str:
    return TURNO_LABELS.get(valor or "", "Não informado")


section_title("Mapa de calor — faturamento por mês")

DIA_SEMANA_CURTO = {
    "domingo": "Dom",
    "segunda": "Seg",
    "terca": "Ter",
    "quarta": "Qua",
    "quinta": "Qui",
    "sexta": "Sex",
    "sabado": "Sáb",
}
ORDEM_DIAS_MAPA = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Não informado"]
ORDEM_TURNOS_MAPA = [
    "Manhã (06h-12h)",
    "Tarde (12h-18h)",
    "Noite (18h-00h)",
    "Não informado",
]
MESES_NO_MAPA = 12


# O mapa mostra os meses lado a lado, então usa o resumo geral (sem o filtro
# de período) e fica com os MESES_NO_MAPA mais recentes.
meses_do_mapa = sorted(resumo_geral["competencias"])[-MESES_NO_MAPA:]
if not meses_do_mapa:
    st.caption("Ainda não há cobranças suficientes para o mapa de calor.")
else:
    cruzar_com = st.radio(
        "Cruzar os meses com",
        ["Dia da semana", "Turno"],
        horizontal=True,
        help="Cada linha do mapa é um dia da semana ou um turno das aulas.",
    )
    por_dia = cruzar_com == "Dia da semana"
    mapa_agrupado = (
        pd.DataFrame(
            [
                {
                    "Mês": rotulo_mes(item["competencia"]),
                    "Grupo": (
                        DIA_SEMANA_CURTO.get(item["dia_semana"], "Não informado")
                        if por_dia
                        else normalizar_turno(item["turno"])
                    ),
                    "Valor": item["valor"],
                }
                for item in resumo_geral["por_turno_dia"]
                if item["competencia"] in meses_do_mapa
            ]
        )
        .groupby(["Mês", "Grupo"], as_index=False)["Valor"]
        .sum()
    )
    mapa_agrupado["Valor_txt"] = mapa_agrupado["Valor"].apply(abreviar_numero)
    mapa_agrupado["Valor_moeda"] = mapa_agrupado["Valor"].apply(formatar_moeda)
    maior_valor_mapa = mapa_agrupado["Valor"].max()
    ordem_grupos = ORDEM_DIAS_MAPA if por_dia else ORDEM_TURNOS_MAPA
    ordem_meses = [rotulo_mes(competencia) for competencia in meses_do_mapa]

    base_mapa = alt.Chart(mapa_agrupado).encode(
        x=alt.X("Mês:N", sort=ordem_meses, title=None, axis=EIXO_MESES),
        y=alt.Y("Grupo:N", sort=ordem_grupos, title=None),
    )
    celulas = base_mapa.mark_rect().encode(
        color=alt.Color(
            "Valor:Q",
            title="Faturamento (R$)",
            scale=alt.Scale(range=[PALETA["heat_claro"], PALETA["heat_escuro"]]),
            legend=alt.Legend(labelExpr=EIXO_NUMERO_EXPR),
        ),
        tooltip=[
            alt.Tooltip("Mês:N"),
            alt.Tooltip("Grupo:N", title=cruzar_com),
            alt.Tooltip("Valor_moeda:N", title="Faturamento"),
        ],
    )
    rotulos = base_mapa.mark_text(baseline="middle", fontSize=10).encode(
        text="Valor_txt:N",
        color=alt.condition(
            alt.datum.Valor > maior_valor_mapa / 2,
            alt.value("white"),
            alt.value("#1a1a1a"),
        ),
    )

    altura_mapa = max(180, 34 * mapa_agrupado["Grupo"].nunique() + 40)
    st.altair_chart(
        (celulas + rotulos)
        .properties(height=altura_mapa)
        .configure_view(strokeWidth=0),
        width="stretch",
    )
    st.caption(
        f"Faturamento de cada mês por {cruzar_com.lower()}, nos últimos "
        f"{len(meses_do_mapa)} mês(es) com cobrança — sem o filtro de período. "
        "Alunos sem turno ou dia da semana cadastrado aparecem em 'Não informado' — "
        "preencha esses campos na edição do aluno para refinar o mapa."
    )

section_title("Curva de vintage — inadimplência acumulada por safra")

SERIE_MEDIA = "Média geral"
COR_MEDIA = PALETA["primary"]
PALETA_SAFRAS = ["#3b6fb6", "#d98b3a", "#8a63b8", "#c75f6a", "#6b8f3e", "#8c7a5b"]
MAX_SAFRAS_NO_GRAFICO = 6

if len(vintage["media"]) < 2:
    # Com um único mês de vida não há curva, só um ponto.
    st.caption(
        "Ainda não há histórico suficiente para a curva de vintage — ela precisa "
        "de alunos com cobranças em pelo menos dois meses desde a matrícula."
    )
else:
    # A curva olha a carteira inteira (não segue o filtro de período): cada
    # safra é o mês de matrícula e o eixo X é a idade da conta.
    safras_com_dados = sorted({ponto["safra"] for ponto in vintage["safras"]})
    passo = max(1, len(safras_com_dados) // MAX_SAFRAS_NO_GRAFICO)
    safras_amostra = safras_com_dados[::passo][:MAX_SAFRAS_NO_GRAFICO]

    linhas_vintage = [
        {
            "Série": f"Safra {ponto['safra']}",
            "Mês": ponto["mes_de_vida"],
            "Percentual": ponto["percentual"],
            "Alunos": ponto["alunos"],
        }
        for ponto in vintage["safras"]
        if ponto["safra"] in safras_amostra
    ] + [
        {
            "Série": SERIE_MEDIA,
            "Mês": ponto["mes_de_vida"],
            "Percentual": ponto["percentual"],
            "Alunos": ponto["alunos"],
        }
        for ponto in vintage["media"]
    ]
    df_vintage = pd.DataFrame(linhas_vintage)
    series = [f"Safra {safra}" for safra in safras_amostra] + [SERIE_MEDIA]
    cores = [*PALETA_SAFRAS[: len(safras_amostra)], COR_MEDIA]
    eh_media = alt.datum["Série"] == SERIE_MEDIA

    chart_vintage = (
        alt.Chart(df_vintage)
        .mark_line(point=alt.OverlayMarkDef(size=28))
        .encode(
            x=alt.X(
                "Mês:Q",
                title="Meses desde a matrícula",
                scale=alt.Scale(domain=[0, vintage["meses"]]),
                axis=alt.Axis(values=list(range(vintage["meses"] + 1)), grid=True),
            ),
            y=alt.Y(
                "Percentual:Q",
                title="% inadimplentes (acumulado)",
                axis=alt.Axis(gridColor="#eef2f6", titlePadding=14),
            ),
            color=alt.Color(
                "Série:N",
                scale=alt.Scale(domain=series, range=cores),
                legend=alt.Legend(title=None, orient="bottom", columns=4),
            ),
            strokeWidth=alt.condition(eh_media, alt.value(4), alt.value(1.5)),
            opacity=alt.condition(eh_media, alt.value(1), alt.value(0.6)),
            tooltip=[
                alt.Tooltip("Série:N"),
                alt.Tooltip("Mês:Q", title="Mês de vida"),
                alt.Tooltip("Percentual:Q", title="% acumulado", format=".1f"),
                alt.Tooltip("Alunos:Q", title="Alunos com cobrança no mês"),
            ],
        )
        .properties(height=380)
        .configure_view(strokeWidth=0)
    )

    media_por_mes = {p["mes_de_vida"]: p["percentual"] for p in vintage["media"]}
    ultimo_mes = max(media_por_mes)
    metrica_inicio, metrica_fim = st.columns(2, gap="medium")
    metrica_inicio.metric(
        "Média geral no mês 0",
        f"{media_por_mes.get(0, 0.0):.1f}%".replace(".", ","),
    )
    metrica_fim.metric(
        f"Média geral no mês {ultimo_mes}",
        f"{media_por_mes[ultimo_mes]:.1f}%".replace(".", ","),
    )
    st.altair_chart(chart_vintage, width="stretch")
    st.caption(
        "Cada linha é uma **safra** (alunos que se matricularam no mesmo mês). "
        "O ponto mostra o % deles que já ficou **inadimplente ao menos uma vez** "
        "até aquele mês de vida da conta — por isso, em geral, a curva sobe."
    )
    st.caption(
        f"Mostra {len(safras_amostra)} de {len(safras_com_dados)} safras, "
        "espalhadas ao longo do período; a média geral considera todas, "
        "ponderada pelo tamanho de cada safra. Em cada mês entram só os alunos "
        "com cobrança naquele mês, então safras pequenas podem oscilar."
    )

section_title("Detalhamento da carteira do mês")

if not detalhamento["itens"]:
    st.caption("Nenhuma cobrança disponível para detalhamento.")
else:
    if detalhamento["total"] > len(detalhamento["itens"]):
        st.caption(
            f"Mostrando as {formatar_inteiro(len(detalhamento['itens']))} cobranças "
            f"mais recentes de {formatar_inteiro(detalhamento['total'])}. Use o filtro de período para ver outro mês."
        )
    detalhes = pd.DataFrame(
        [
            {
                "ID": cobranca["id"],
                "Aluno": cobranca["aluno_nome"] or f"Aluno #{cobranca['aluno_id']}",
                "Competência": cobranca["competencia"],
                "Vencimento": cobranca["data_vencimento"],
                "Valor": formatar_moeda(float(cobranca["valor"])),
                "Status": STATUS_LABELS.get(
                    cobranca["status"],
                    cobranca["status"].title(),
                ),
                "Pagamento": cobranca.get("data_pagamento"),
                "Forma": (cobranca.get("forma_pagamento") or "—").upper(),
            }
            for cobranca in detalhamento["itens"]
        ]
    )
    detalhes["Vencimento"] = pd.to_datetime(detalhes["Vencimento"]).dt.date
    detalhes["Pagamento"] = pd.to_datetime(detalhes["Pagamento"]).dt.date

    st.dataframe(
        detalhes,
        width="stretch",
        hide_index=True,
        column_config={
            "ID": st.column_config.NumberColumn("ID", format="%d"),
            "Vencimento": st.column_config.DateColumn(
                "Vencimento", format="DD/MM/YYYY"
            ),
            "Pagamento": st.column_config.DateColumn("Pagamento", format="DD/MM/YYYY"),
        },
    )
