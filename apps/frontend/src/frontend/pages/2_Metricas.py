import altair as alt
import pandas as pd
import streamlit as st

from frontend.ui import (
    apply_theme,
    metric_card,
    page_header,
    section_title,
    sidebar_brand,
)


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
        "Acompanhe os principais indicadores da operação, a projeção de receita "
        "e a distribuição das cobranças por situação."
    ),
)

# Os mesmos dados demonstrativos da versão original foram preservados.
dados_cobranca = pd.DataFrame(
    {
        "Status": ["Pagas", "Pendentes", "Atrasadas", "Inadimplentes"],
        "Quantidade": [42, 4, 1, 1],
        "Valor (R$)": [5460.00, 520.00, 130.00, 130.00],
    }
)

st.caption("Indicadores demonstrativos · referência do mês atual")
col1, col2, col3 = st.columns(3, gap="medium")
with col1:
    metric_card("Alunos ativos", "48", "+3 neste mês")
with col2:
    metric_card("Receita prevista", "R$ 6.240,00", "+5,2% no mês", accent="#1d4ed8")
with col3:
    metric_card(
        "Taxa de inadimplência",
        "4,1%",
        "−1,2% no mês",
        accent="#f79009",
        attention=True,
    )

section_title("Distribuição das faturas")

chart = (
    alt.Chart(dados_cobranca)
    .mark_bar(cornerRadiusTopLeft=7, cornerRadiusTopRight=7, size=52)
    .encode(
        x=alt.X(
            "Status:N",
            sort=None,
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
                domain=["Pagas", "Pendentes", "Atrasadas", "Inadimplentes"],
                range=["#0f766e", "#f2c94c", "#f79009", "#d92d20"],
            ),
            legend=None,
        ),
        tooltip=[
            alt.Tooltip("Status:N", title="Situação"),
            alt.Tooltip("Quantidade:Q", title="Faturas"),
            alt.Tooltip("Valor (R$):Q", title="Valor", format=",.2f"),
        ],
    )
    .properties(height=340)
    .configure_view(strokeWidth=0)
)

chart_col, summary_col = st.columns([2.15, 1], gap="large")
with chart_col:
    st.altair_chart(chart, use_container_width=True)

with summary_col:
    st.markdown("#### Resumo por situação")
    st.caption("Quantidade e valor total das faturas.")
    resumo = dados_cobranca.rename(columns={"Valor (R$)": "Valor"}).copy()
    st.dataframe(
        resumo,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Status": st.column_config.TextColumn("Situação"),
            "Quantidade": st.column_config.NumberColumn("Qtd.", format="%d"),
            "Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
        },
    )

section_title("Leitura operacional")
paid_col, pending_col = st.columns(2, gap="large")
with paid_col:
    st.success(
        "**87,5% das faturas estão pagas.** O volume recebido concentra a maior "
        "parte da receita prevista no período."
    )
with pending_col:
    st.warning(
        "**6 faturas exigem acompanhamento.** Considere priorizar os casos "
        "atrasados e inadimplentes na régua de cobrança."
    )
