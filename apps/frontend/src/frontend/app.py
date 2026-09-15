import streamlit as st

from frontend.ui import (
    apply_theme,
    feature_card,
    page_header,
    section_title,
    sidebar_brand,
)

st.set_page_config(
    page_title="PagControl - Sistema de Cobrança",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_theme()
sidebar_brand()

page_header(
    "Visão geral",
    "Gestão financeira simples e eficiente",
    (
        "Centralize matrículas, acompanhe cobranças recorrentes e tenha uma visão "
        "clara da operação financeira da academia."
    ),
)

section_title("Acesso rápido")
col1, col2 = st.columns(2, gap="large")

with col1:
    feature_card(
        "01",
        "Gestão de alunos",
        (
            "Cadastre alunos, organize mensalidades e consulte as informações "
            "essenciais de cada matrícula em um único lugar."
        ),
    )

with col2:
    feature_card(
        "02",
        "Métricas financeiras",
        (
            "Acompanhe receita prevista, situação das faturas e indicadores de "
            "inadimplência com leitura rápida."
        ),
    )

section_title("Como começar")
step1, step2, step3 = st.columns(3, gap="medium")
with step1:
    feature_card(
        "1", "Cadastre", "Inclua os dados do aluno e defina mensalidade e vencimento."
    )
with step2:
    feature_card(
        "2",
        "Acompanhe",
        "Consulte a base cadastrada e mantenha as informações organizadas.",
    )
with step3:
    feature_card(
        "3",
        "Analise",
        "Use o painel para visualizar os principais indicadores financeiros.",
    )

st.html("<br>")
st.caption("PagControl · FastAPI + Streamlit · Ambiente de gestão recorrente")
