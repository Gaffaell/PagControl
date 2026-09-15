import datetime

import pandas as pd
import streamlit as st

from frontend.api.cliente import listar_alunos
from frontend.ui import (
    api_status,
    apply_theme,
    metric_card,
    page_header,
    section_title,
    sidebar_brand,
)


st.set_page_config(
    page_title="Gestão de Alunos - PagControl",
    page_icon="👥",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_theme()
sidebar_brand()

page_header(
    "Cadastros",
    "Gestão de alunos",
    (
        "Cadastre novos alunos e consulte as informações das matrículas com uma "
        "visão organizada e objetiva."
    ),
)


def preparar_alunos(dados: list[dict]) -> pd.DataFrame:
    """Ajusta apenas os nomes de exibição dos campos recebidos da API."""
    df = pd.DataFrame(dados)
    if df.empty:
        return df

    df = df.rename(
        columns={
            "id": "ID",
            "nome": "Nome",
            "valor_mensalidade": "Valor Mensalidade (R$)",
            "dia_vencimento": "Dia Vencimento",
            "modalidade": "Modalidade",
            "data_matricula": "Data Matrícula",
            "criado_em": "Criado em",
        }
    )

    if "ativo" in df.columns:
        df["Status"] = df["ativo"].map({True: "Ativo", False: "Inativo"})
        df = df.drop(columns=["ativo"])

    return df


# A leitura continua usando exatamente a integração existente. Caso o backend
# esteja fora do ar, a página permanece acessível e informa o estado ao usuário.
api_online = True
try:
    alunos_cadastrados = listar_alunos(False)
except Exception:
    alunos_cadastrados = []
    api_online = False

status_col, help_col = st.columns([1, 2.4])
with status_col:
    api_status(api_online)
with help_col:
    if not api_online:
        st.warning(
            "Não foi possível consultar o backend. Confirme se a API está ativa em "
            "http://localhost:8000."
        )

# Mantém o comportamento existente da aplicação: a tabela é carregada uma vez
# na sessão e os novos cadastros são adicionados ao session_state.
if "alunos_df" not in st.session_state:
    st.session_state.alunos_df = preparar_alunos(alunos_cadastrados)

alunos_df = st.session_state.alunos_df
total_alunos = len(alunos_df)

if "Status" in alunos_df.columns:
    total_ativos = int(alunos_df["Status"].astype(str).str.casefold().eq("ativo").sum())
else:
    total_ativos = total_alunos

if "Valor Mensalidade (R$)" in alunos_df.columns:
    receita_mensal = pd.to_numeric(
        alunos_df["Valor Mensalidade (R$)"], errors="coerce"
    ).fillna(0).sum()
else:
    receita_mensal = 0.0

metric1, metric2, metric3 = st.columns(3, gap="medium")
with metric1:
    metric_card("Alunos cadastrados", str(total_alunos), "Base da sessão")
with metric2:
    metric_card("Matrículas ativas", str(total_ativos), "Situação atual", accent="#1d4ed8")
with metric3:
    metric_card(
        "Mensalidades cadastradas",
        f"R$ {receita_mensal:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        "Valor mensal",
        accent="#7c3aed",
    )

section_title("Adicionar novo aluno")
st.caption("Preencha os dados abaixo. Os campos essenciais estão destacados no formulário.")

with st.form("add_aluno_form"):
    st.markdown("**Informações pessoais e financeiras**")
    col1, col2 = st.columns(2, gap="large")
    with col1:
        nome = st.text_input("Nome completo *", placeholder="Ex.: Maria Souza Oliveira")
        email = st.text_input("E-mail", placeholder="Ex.: maria.souza@pagcontrol.com")
        telefone = st.text_input("Telefone", placeholder="Ex.: (11) 98765-4321")
        valor_mensalidade = st.number_input(
            "Valor da mensalidade (R$) *",
            min_value=0.0,
            value=120.0,
            step=10.0,
            format="%.2f",
        )
    with col2:
        cep = st.text_input("CEP", placeholder="Ex.: 04538-133")
        endereco = st.text_input("Endereço", placeholder="Ex.: Rua das Flores")
        numero = st.text_input("Número", placeholder="Ex.: 456")
        complemento = st.text_input("Complemento", placeholder="Ex.: Bloco B")
        dia_vencimento = st.number_input(
            "Dia de vencimento *",
            min_value=1,
            max_value=31,
            value=10,
            step=1,
        )

    submitted = st.form_submit_button("Cadastrar aluno", use_container_width=True)

if submitted:
    if not nome:
        st.error("Preencha o nome do aluno para concluir o cadastro.")
    else:
        novo_id = len(st.session_state.alunos_df) + 1
        hoje = datetime.date.today().strftime("%d/%m/%Y")
        novo_aluno = pd.DataFrame(
            [
                {
                    "ID": novo_id,
                    "Nome": nome,
                    "Email": email,
                    "Telefone": telefone,
                    "CEP": cep,
                    "Endereço": endereco,
                    "Número": numero,
                    "Complemento": complemento,
                    "Valor Mensalidade (R$)": valor_mensalidade,
                    "Dia Vencimento": int(dia_vencimento),
                    "Status": "Ativo",
                    "Data Matrícula": hoje,
                }
            ]
        )

        st.session_state.alunos_df = pd.concat(
            [st.session_state.alunos_df, novo_aluno],
            ignore_index=True,
        )
        st.success(f"Aluno **{nome}** cadastrado com sucesso.")
        st.dataframe(novo_aluno, use_container_width=True, hide_index=True)

section_title("Alunos cadastrados")

filter_col, status_filter_col = st.columns([2, 1], gap="medium")
with filter_col:
    busca = st.text_input(
        "Buscar aluno",
        placeholder="Digite um nome, e-mail ou telefone",
        label_visibility="collapsed",
    )
with status_filter_col:
    filtro_status = st.selectbox(
        "Filtrar por status",
        ["Todos", "Ativo", "Inativo"],
        label_visibility="collapsed",
    )

alunos_exibidos = st.session_state.alunos_df.copy()

if busca and not alunos_exibidos.empty:
    colunas_busca = [
        coluna
        for coluna in ["Nome", "Email", "Telefone"]
        if coluna in alunos_exibidos.columns
    ]
    if colunas_busca:
        mascara = pd.Series(False, index=alunos_exibidos.index)
        for coluna in colunas_busca:
            mascara |= alunos_exibidos[coluna].astype(str).str.contains(
                busca,
                case=False,
                na=False,
                regex=False,
            )
        alunos_exibidos = alunos_exibidos[mascara]

if filtro_status != "Todos" and "Status" in alunos_exibidos.columns:
    alunos_exibidos = alunos_exibidos[
        alunos_exibidos["Status"].astype(str) == filtro_status
    ]

st.caption(f"Exibindo {len(alunos_exibidos)} de {len(st.session_state.alunos_df)} registro(s).")

if alunos_exibidos.empty:
    st.info("Nenhum aluno encontrado para os filtros selecionados.")
else:
    st.data_editor(
        alunos_exibidos,
        use_container_width=True,
        hide_index=True,
        disabled=["ID", "Data Matrícula", "Criado em"],
        column_config={
            "Status": st.column_config.SelectboxColumn(
                "Status",
                help="Status da matrícula do aluno",
                options=["Ativo", "Inativo"],
                required=True,
            ),
            "Valor Mensalidade (R$)": st.column_config.NumberColumn(
                "Valor Mensalidade (R$)",
                format="R$ %.2f",
            ),
            "Dia Vencimento": st.column_config.NumberColumn(
                "Vencimento",
                min_value=1,
                max_value=31,
                format="%d",
            ),
        },
    )
