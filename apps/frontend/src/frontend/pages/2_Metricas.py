import altair as alt
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Métricas Financeiras - PagControl", page_icon="📊", layout="wide")
st.title("📊 Métricas e Inadimplência")
st.write("Acompanhamento financeiro, projeção de receitas e régua de cobrança.")

col1, col2, col3 = st.columns(3)
col1.metric("Alunos Ativos", "48", "+3 este mês")
col2.metric("Receita Prevista (Mês)", "R$ 6.240,00", "+5.2%")
col3.metric("Taxa de Inadimplência", "4.1%", "-1.2%", delta_color="inverse")

st.divider()

st.subheader("Distribuição de Faturas por Status")

dados_cobranca = pd.DataFrame(
    {
        "Status": ["Pagas", "Pendentes", "Atrasadas", "Inadimplentes"],
        "Quantidade": [42, 4, 1, 1],
        "Valor (R$)": [5460.00, 520.00, 130.00, 130.00],
    }
)

chart = (
    alt.Chart(dados_cobranca)
    .mark_bar()
    .encode(
        x=alt.X("Status:N", sort=None),
        y="Valor (R$):Q",
        color=alt.Color(
            "Status:N",
            scale=alt.Scale(
                domain=["Pagas", "Pendentes", "Atrasadas", "Inadimplentes"],
                range=["#28a745", "#ffc107", "#fd7e14", "#dc3545"],
            ),
        ),
        tooltip=["Status", "Quantidade", "Valor (R$)"],
    )
    .properties(height=350)
)

st.altair_chart(chart, use_container_width=True)
