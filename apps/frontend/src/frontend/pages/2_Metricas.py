from datetime import datetime

import altair as alt
import pandas as pd
import streamlit as st
from frontend.api.cliente import APIError, listar_alunos, listar_cobrancas
from frontend.ui import (
    api_status,
    apply_theme,
    metric_card,
    page_header,
    section_title,
    sidebar_brand,
)

STATUS_LABELS = {
    "pago": "Pagas",
    "pendente": "Pendentes",
    "atrasado": "Atrasadas",
    "inadimplente": "Inadimplentes",
}
STATUS_COLORS = {
    "Pagas": "#3f9a89",
    "Pendentes": "#e8bc4f",
    "Atrasadas": "#e2884a",
    "Inadimplentes": "#d16057",
}


st.set_page_config(
    page_title="Métricas Financeiras - PagControl",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
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


def formatar_moeda(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


try:
    alunos = listar_alunos(False)
    cobrancas = listar_cobrancas()
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

MESES_LABEL = {
    1: "Janeiro",
    2: "Fevereiro",
    3: "Março",
    4: "Abril",
    5: "Maio",
    6: "Junho",
    7: "Julho",
    8: "Agosto",
    9: "Setembro",
    10: "Outubro",
    11: "Novembro",
    12: "Dezembro",
}


def formatar_competencia(competencia: str) -> str:
    data = datetime.strptime(competencia, "%Y-%m")
    return f"{MESES_LABEL[data.month]}/{data.year}"


competencias_disponiveis = sorted(
    {cobranca["competencia"] for cobranca in cobrancas}, reverse=True
)
opcoes_periodo = ["Período completo"] + [
    formatar_competencia(c) for c in competencias_disponiveis
]
competencia_por_opcao = {formatar_competencia(c): c for c in competencias_disponiveis}

periodo_selecionado = st.selectbox(
    "Período",
    options=opcoes_periodo,
    help=(
        "Filtra todos os indicadores e gráficos abaixo por competência "
        "(mês cobrado). 'Período completo' soma todas as cobranças já geradas."
    ),
)

if periodo_selecionado != "Período completo":
    competencia_filtro = competencia_por_opcao[periodo_selecionado]
    cobrancas = [
        cobranca
        for cobranca in cobrancas
        if cobranca["competencia"] == competencia_filtro
    ]
    st.caption(
        f"Exibindo apenas a competência **{periodo_selecionado}** "
        f"({len(cobrancas)} cobrança(s))."
    )
else:
    st.caption(
        f"Exibindo o período completo: todas as {len(cobrancas)} cobranças já "
        "geradas, de qualquer competência."
    )

alunos_ativos = [aluno for aluno in alunos if aluno["ativo"]]
receita_prevista = sum(float(aluno["valor_mensalidade"]) for aluno in alunos_ativos)
total_cobrancas = len(cobrancas)
total_inadimplentes = sum(
    cobranca["status"] in {"atrasado", "inadimplente"} for cobranca in cobrancas
)
taxa_inadimplencia = (
    (total_inadimplentes / total_cobrancas) * 100 if total_cobrancas else 0.0
)

col1, col2, col3, col4 = st.columns(4, gap="medium")
with col1:
    metric_card("Alunos ativos", str(len(alunos_ativos)), "Dados da API")
with col2:
    metric_card(
        "Receita mensal prevista",
        formatar_moeda(receita_prevista),
        "Mensalidades ativas",
        accent="#1d4ed8",
    )
with col3:
    metric_card(
        "Cobranças registradas",
        str(total_cobrancas),
        "Carteira completa",
        accent="#7c3aed",
    )
with col4:
    metric_card(
        "Taxa de inadimplência",
        f"{taxa_inadimplencia:.1f}%".replace(".", ","),
        "Atrasadas + inadimplentes",
        accent="#f79009",
        attention=total_inadimplentes > 0,
    )

section_title("Distribuição das cobranças")

resumo_status = []
for status_api, status_label in STATUS_LABELS.items():
    itens = [cobranca for cobranca in cobrancas if cobranca["status"] == status_api]
    resumo_status.append(
        {
            "Status": status_label,
            "Quantidade": len(itens),
            "Valor (R$)": sum(float(cobranca["valor"]) for cobranca in itens),
        }
    )

dados_cobranca = pd.DataFrame(resumo_status).sort_values("Valor (R$)", ascending=False)

if not cobrancas:
    st.info(
        "Ainda não existem cobranças registradas. Os indicadores financeiros "
        "serão preenchidos assim que o backend possuir dados."
    )
else:
    chart = (
        alt.Chart(dados_cobranca)
        .mark_bar(cornerRadiusTopLeft=7, cornerRadiusTopRight=7, size=52)
        .encode(
            x=alt.X(
                "Status:N",
                sort="-y",
                title=None,
                axis=alt.Axis(labelAngle=0, labelPadding=12),
            ),
            y=alt.Y(
                "Valor (R$):Q",
                title="Valor (R$)",
                axis=alt.Axis(gridColor="#eef2f6", titlePadding=14),
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
                alt.Tooltip("Quantidade:Q", title="Cobranças"),
                alt.Tooltip("Valor (R$):Q", title="Valor", format=",.2f"),
            ],
        )
        .properties(height=340)
        .configure_view(strokeWidth=0)
    )

    chart_col, summary_col = st.columns([2.15, 1], gap="large")
    with chart_col:
        st.altair_chart(chart, width="stretch")

    with summary_col:
        st.markdown("#### Resumo por situação")
        st.caption("Quantidade e valor da carteira atual.")
        resumo = dados_cobranca.rename(columns={"Valor (R$)": "Valor"})
        st.dataframe(
            resumo,
            width="stretch",
            hide_index=True,
            column_config={
                "Status": st.column_config.TextColumn("Situação"),
                "Quantidade": st.column_config.NumberColumn("Qtd.", format="%d"),
                "Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
            },
        )

aluno_por_id = {aluno["id"]: aluno for aluno in alunos}

section_title("Inadimplência por faixa etária")

FAIXAS_ETARIAS = [
    (0, 24, "Até 24"),
    (25, 34, "25-34"),
    (35, 44, "35-44"),
    (45, 54, "45-54"),
    (55, 64, "55-64"),
    (65, 200, "65+"),
]
ORDEM_FAIXAS_ETARIAS = [label for _, _, label in FAIXAS_ETARIAS] + ["Não informada"]


def calcular_faixa_etaria(data_nascimento: str | None) -> str:
    if not data_nascimento:
        return "Não informada"
    nascimento = pd.Timestamp(data_nascimento).date()
    hoje = pd.Timestamp.today().date()
    idade = (
        hoje.year
        - nascimento.year
        - ((hoje.month, hoje.day) < (nascimento.month, nascimento.day))
    )
    for minimo, maximo, label in FAIXAS_ETARIAS:
        if minimo <= idade <= maximo:
            return label
    return "Não informada"


if not cobrancas:
    st.caption("Ainda não há cobranças suficientes para cruzar com faixa etária.")
else:
    linhas_idade = []
    for cobranca in cobrancas:
        aluno = aluno_por_id.get(cobranca["aluno_id"])
        faixa = calcular_faixa_etaria(aluno.get("data_nascimento") if aluno else None)
        linhas_idade.append(
            {
                "Faixa etária": faixa,
                "Situação": STATUS_LABELS.get(
                    cobranca["status"], cobranca["status"].title()
                ),
                "Inadimplente": cobranca["status"] in {"atrasado", "inadimplente"},
                "Valor": float(cobranca["valor"]),
            }
        )
    df_idade = pd.DataFrame(linhas_idade)

    resumo_idade = df_idade.groupby(["Faixa etária", "Situação"], as_index=False).agg(
        Quantidade=("Valor", "size"), Valor=("Valor", "sum")
    )

    chart_idade = (
        alt.Chart(resumo_idade)
        .mark_bar()
        .encode(
            x=alt.X("Faixa etária:N", sort=ORDEM_FAIXAS_ETARIAS, title=None),
            y=alt.Y("Quantidade:Q", title="Cobranças"),
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
                alt.Tooltip("Quantidade:Q", title="Cobranças"),
                alt.Tooltip("Valor:Q", title="Valor", format=",.2f"),
            ],
        )
        .properties(height=340)
        .configure_view(strokeWidth=0)
    )

    taxa_por_faixa = (
        df_idade.groupby("Faixa etária")
        .agg(Total=("Inadimplente", "size"), Inadimplentes=("Inadimplente", "sum"))
        .reset_index()
    )
    taxa_por_faixa["Taxa de inadimplência"] = (
        taxa_por_faixa["Inadimplentes"] / taxa_por_faixa["Total"] * 100
    )
    taxa_por_faixa["ordem"] = taxa_por_faixa["Faixa etária"].apply(
        ORDEM_FAIXAS_ETARIAS.index
    )
    taxa_por_faixa = taxa_por_faixa.sort_values("ordem").drop(columns="ordem")

    chart_col, tabela_col = st.columns([2.15, 1], gap="large")
    with chart_col:
        st.altair_chart(chart_idade, width="stretch")
    with tabela_col:
        st.markdown("#### Taxa de inadimplência por faixa")
        st.caption("Atrasadas + inadimplentes sobre o total de cobranças da faixa.")
        st.dataframe(
            taxa_por_faixa,
            width="stretch",
            hide_index=True,
            column_config={
                "Faixa etária": st.column_config.TextColumn("Faixa etária"),
                "Total": st.column_config.NumberColumn("Cobranças", format="%d"),
                "Inadimplentes": st.column_config.NumberColumn(
                    "Atrasadas/inad.", format="%d"
                ),
                "Taxa de inadimplência": st.column_config.NumberColumn(
                    "Taxa", format="%.1f%%"
                ),
            },
        )
    st.caption(
        "Alunos sem data de nascimento cadastrada aparecem em 'Não informada' — "
        "preencha esse campo na edição do aluno para refinar a análise."
    )

section_title("Faturamento por modalidade")

MODALIDADE_COR_PRINCIPAL = "#1d4ed8"
MODALIDADE_COR_SECUNDARIA = "#c7d2e8"


def normalizar_modalidade(valor: str | None) -> str:
    if not valor or not valor.strip():
        return "Não informada"
    return valor.strip().title()


mes_atual = pd.Timestamp.today().strftime("%Y-%m")
mes_anterior = (pd.Timestamp.today().replace(day=1) - pd.Timedelta(days=1)).strftime(
    "%Y-%m"
)

if not cobrancas:
    st.caption(
        "Ainda não há cobranças suficientes para calcular faturamento por modalidade."
    )
else:
    linhas_modalidade = []
    for cobranca in cobrancas:
        aluno = aluno_por_id.get(cobranca["aluno_id"])
        modalidade = normalizar_modalidade(aluno.get("modalidade") if aluno else None)
        linhas_modalidade.append(
            {
                "Modalidade": modalidade,
                "Competência": cobranca["competencia"],
                "Valor": float(cobranca["valor"]),
            }
        )
    df_modalidade = pd.DataFrame(linhas_modalidade)

    faturamento_total = (
        df_modalidade.groupby("Modalidade", as_index=False)
        .agg(Quantidade=("Valor", "size"), Faturamento=("Valor", "sum"))
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

    chart_modalidade = (
        alt.Chart(faturamento_total)
        .mark_bar(cornerRadiusTopRight=6, cornerRadiusBottomRight=6, size=22)
        .encode(
            y=alt.Y(
                "Modalidade:N",
                sort="-x",
                title=None,
                axis=alt.Axis(labelPadding=8),
            ),
            x=alt.X(
                "Faturamento:Q",
                title="Faturamento (R$)",
                axis=alt.Axis(gridColor="#eef2f6", titlePadding=10),
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
                alt.Tooltip("Quantidade:Q", title="Cobranças"),
                alt.Tooltip("Faturamento:Q", title="Faturamento", format=",.2f"),
                alt.Tooltip(
                    "Variação (%):Q", title="Var. vs mês anterior", format=".1f"
                ),
            ],
        )
        .properties(height=altura_grafico)
        .configure_view(strokeWidth=0)
    )

    chart_col, tabela_col = st.columns([2.15, 1], gap="large")
    with chart_col:
        st.altair_chart(chart_modalidade, width="stretch")
    with tabela_col:
        st.markdown("#### Resumo por modalidade")
        st.caption("Faturamento acumulado e variação em relação ao mês anterior.")
        tabela_exibicao = faturamento_total.copy()
        tabela_exibicao["Variação (%)"] = tabela_exibicao["Variação (%)"].apply(
            lambda v: "—" if v is None else f"{v:+.1f}%".replace(".", ",")
        )
        st.dataframe(
            tabela_exibicao,
            width="stretch",
            hide_index=True,
            column_config={
                "Modalidade": st.column_config.TextColumn("Modalidade"),
                "Quantidade": st.column_config.NumberColumn("Cobranças", format="%d"),
                "Faturamento": st.column_config.NumberColumn(
                    "Faturamento", format="R$ %.2f"
                ),
                "Variação (%)": st.column_config.TextColumn("Var. vs mês anterior"),
            },
        )
    st.caption(
        "Variação calculada comparando o total faturado no mês atual com o mês "
        "anterior, por modalidade. Modalidades sem cobrança no mês anterior aparecem "
        "sem variação (—)."
    )

TURNO_LABELS = {
    "manha": "Manhã (06h-12h)",
    "tarde": "Tarde (12h-18h)",
    "noite": "Noite (18h-00h)",
}


def normalizar_turno(valor: str | None) -> str:
    return TURNO_LABELS.get(valor or "", "Não informado")


section_title("Mapa de calor — turno x dia da semana")

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

if not cobrancas:
    st.caption("Ainda não há cobranças suficientes para o mapa de calor.")
else:
    linhas_mapa = []
    for cobranca in cobrancas:
        aluno = aluno_por_id.get(cobranca["aluno_id"])
        turno = normalizar_turno(aluno.get("turno") if aluno else None)
        dia_raw = aluno.get("dia_semana") if aluno else None
        dia = DIA_SEMANA_CURTO.get(dia_raw, "Não informado")
        linhas_mapa.append(
            {"Turno": turno, "Dia": dia, "Valor": float(cobranca["valor"])}
        )
    mapa_agrupado = (
        pd.DataFrame(linhas_mapa)
        .groupby(["Turno", "Dia"], as_index=False)["Valor"]
        .sum()
    )
    maior_valor_mapa = mapa_agrupado["Valor"].max()

    base_mapa = alt.Chart(mapa_agrupado).encode(
        x=alt.X("Dia:N", sort=ORDEM_DIAS_MAPA, title=None),
        y=alt.Y("Turno:N", sort=ORDEM_TURNOS_MAPA, title=None),
    )
    celulas = base_mapa.mark_rect().encode(
        color=alt.Color(
            "Valor:Q",
            title="Faturamento (R$)",
            scale=alt.Scale(scheme="blues"),
        ),
        tooltip=[
            alt.Tooltip("Turno:N"),
            alt.Tooltip("Dia:N"),
            alt.Tooltip("Valor:Q", title="Faturamento", format=",.2f"),
        ],
    )
    rotulos = base_mapa.mark_text(baseline="middle").encode(
        text=alt.Text("Valor:Q", format=",.0f"),
        color=alt.condition(
            alt.datum.Valor > maior_valor_mapa / 2,
            alt.value("white"),
            alt.value("#1a1a1a"),
        ),
    )

    st.altair_chart(
        (celulas + rotulos).properties(height=220).configure_view(strokeWidth=0),
        width="stretch",
    )
    st.caption(
        "Cruza turno e dia da semana das aulas para mostrar onde se concentra o "
        "faturamento. Alunos sem dia da semana cadastrado ainda aparecem em "
        "'Não informado' — preencha esse campo na edição do aluno para refinar o mapa."
    )

section_title("Detalhamento da carteira do mês")

if not cobrancas:
    st.caption("Nenhuma cobrança disponível para detalhamento.")
else:
    nomes_por_id = {aluno["id"]: aluno["nome"] for aluno in alunos}
    detalhes = pd.DataFrame(
        [
            {
                "ID": cobranca["id"],
                "Aluno": nomes_por_id.get(
                    cobranca["aluno_id"],
                    f"Aluno #{cobranca['aluno_id']}",
                ),
                "Competência": cobranca["competencia"],
                "Vencimento": cobranca["data_vencimento"],
                "Valor": float(cobranca["valor"]),
                "Status": STATUS_LABELS.get(
                    cobranca["status"],
                    cobranca["status"].title(),
                ),
                "Pagamento": cobranca.get("data_pagamento"),
                "Forma": (cobranca.get("forma_pagamento") or "—").upper(),
            }
            for cobranca in cobrancas
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
            "Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
        },
    )
