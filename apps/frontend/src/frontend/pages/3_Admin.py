import streamlit as st
from frontend.api.cliente import (
    APIError,
    atualizar_aluno,
    atualizar_configuracao_regua,
    listar_alunos,
    obter_configuracao_regua,
)
from frontend.ui import (
    api_status,
    apply_theme,
    page_header,
    section_title,
    sidebar_brand,
)

st.set_page_config(
    page_title="Admin - PagControl",
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_theme()
sidebar_brand()

page_header(
    "Administração",
    "Contato do aluno e régua de cobrança",
    (
        "Dados de contato/endereço e parâmetros da régua de cobrança — "
        "informações que não fazem parte do cadastro rápido da tela de Alunos."
    ),
)

try:
    alunos = listar_alunos(False)
    regua = obter_configuracao_regua()
except APIError as exc:
    api_status(False)
    st.error(str(exc))
    st.info(
        "Inicie o backend com `uv run --package backend uvicorn backend.api:app --reload` "
        "e recarregue esta página."
    )
    st.stop()

api_status(True)

section_title("Dados de contato do aluno")

if not alunos:
    st.info("Nenhum aluno cadastrado ainda.")
else:
    opcoes = {f"{a['nome']} (id {a['id']})": a for a in alunos}
    escolhido = st.selectbox("Selecione um aluno", list(opcoes.keys()))
    aluno = opcoes[escolhido]

    with st.form("admin_contato_form"):
        col1, col2 = st.columns(2)
        with col1:
            email = st.text_input("Email", value=aluno.get("email") or "")
            telefone = st.text_input("Telefone", value=aluno.get("telefone") or "")
            cep = st.text_input("CEP", value=aluno.get("cep") or "")
        with col2:
            endereco = st.text_input("Endereço", value=aluno.get("endereco") or "")
            numero = st.text_input("Número", value=aluno.get("numero") or "")
            complemento = st.text_input(
                "Complemento", value=aluno.get("complemento") or ""
            )

        salvar_contato = st.form_submit_button("Salvar dados de contato")

    if salvar_contato:
        try:
            atualizar_aluno(
                aluno["id"],
                {
                    "email": email or None,
                    "telefone": telefone or None,
                    "cep": cep or None,
                    "endereco": endereco or None,
                    "numero": numero or None,
                    "complemento": complemento or None,
                },
            )
        except APIError as exc:
            st.error(str(exc))
        else:
            st.success(
                f"Dados de contato de **{aluno['nome']}** atualizados com sucesso!"
            )

st.divider()
section_title("Régua de cobrança")

with st.form("admin_regua_form"):
    dias_lembrete_antes = st.number_input(
        "Dias de lembrete antes do vencimento",
        min_value=0,
        max_value=30,
        value=regua["dias_lembrete_antes"],
    )
    dias_aviso_vencimento = st.number_input(
        "Dias de aviso no vencimento",
        min_value=0,
        max_value=30,
        value=regua["dias_aviso_vencimento"],
    )
    dias_cobranca_atraso = st.text_input(
        "Dias de cobrança após atraso (separados por vírgula)",
        value=regua["dias_cobranca_atraso"],
        help="Ex.: 3,7 — cobra em 3 dias de atraso e novamente em 7 (vira inadimplente no maior valor).",
    )

    salvar_regua = st.form_submit_button("Salvar régua de cobrança")

if salvar_regua:
    try:
        atualizar_configuracao_regua(
            {
                "dias_lembrete_antes": int(dias_lembrete_antes),
                "dias_aviso_vencimento": int(dias_aviso_vencimento),
                "dias_cobranca_atraso": dias_cobranca_atraso,
            }
        )
    except APIError as exc:
        st.error(str(exc))
    else:
        st.success("Régua de cobrança atualizada com sucesso!")
