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
    "Pagas": "#0f766e",
    "Pendentes": "#f2c94c",
    "Atrasadas": "#f79009",
    "Inadimplentes": "#d92d20",
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

dados_cobranca = pd.DataFrame(resumo_status)

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
                sort=list(STATUS_LABELS.values()),
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
