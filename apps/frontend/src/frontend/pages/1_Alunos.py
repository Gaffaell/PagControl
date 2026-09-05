import datetime

from frontend.api.cliente import criar_aluno, listar_alunos
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Gestão de Alunos - PagControl", page_icon="👥", layout="wide")
st.title("👥 Gestão de Alunos")
st.write("Cadastre, visualize e edite os alunos matriculados na academia.")

# Inicializa DataFrame de alunos em session_state
if "alunos_df" not in st.session_state:
    alunos_cadastrados = listar_alunos(False)
    st.session_state.alunos_df = pd.DataFrame(alunos_cadastrados)

st.header("Adicionar um novo aluno")

with st.form("add_aluno_form"):
    col1, col2 = st.columns(2)
    with col1:
        nome = st.text_input("Nome completo", placeholder="Ex: Maria Souza Oliveira")
        email = st.text_input("Email", placeholder="Ex: maria.souza@pagcontrol.com")
        telefone = st.text_input("Telefone", placeholder="Ex: (11) 98765-4321")
        valor_mensalidade = st.number_input(
            "Valor da mensalidade (R$)", min_value=0.0, value=120.0, step=10.0, format="%.2f"
        )
    with col2:
        cep = st.text_input("CEP", placeholder="Ex: 04538-133")
        endereco = st.text_input("Endereço", placeholder="Ex: Rua das Flores")
        numero = st.text_input("Número", placeholder="Ex: 456")
        complemento = st.text_input("Complemento", placeholder="Ex: Bloco B")
        dia_vencimento = st.number_input(
            "Dia de vencimento", min_value=1, max_value=31, value=10, step=1
        )

    submitted = st.form_submit_button("Cadastrar Aluno")

if submitted:
    if not nome or not valor_mensalidade or not dia_vencimento:
        st.error("Por favor, preencha todos os campos obrigatórios.")
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

        # Chama a função criar_aluno da API para enviar os dados ao backend
        criar_aluno(
            {
                "nome": nome,
                "email": email or None,
                "telefone": telefone or None,
                "cep": cep or None,
                "endereco": endereco or None,
                "numero": numero or None,
                "complemento": complemento or None,
                "valor_mensalidade": float(valor_mensalidade),
                "dia_vencimento": int(dia_vencimento),
            }
        )
        st.session_state.alunos_df = pd.concat([st.session_state.alunos_df, novo_aluno], ignore_index=True)
        st.success(f"Aluno **{nome}** cadastrado com sucesso!")
        st.dataframe(novo_aluno, use_container_width=True, hide_index=True)

st.header("Alunos Cadastrados")
st.write(f"Total de alunos registrados: `{len(st.session_state.alunos_df)}`")

st.data_editor(
    st.session_state.alunos_df,
    use_container_width=True,
    hide_index=True,
    disabled=["ID", "Data Matrícula"],
    column_config={
        "Status": st.column_config.SelectboxColumn(
            "Status",
            help="Status da matrícula do aluno",
            options=["Ativo", "Inativo"],
            required=True,
        ),
        "Valor Mensalidade (R$)": st.column_config.NumberColumn(
            "Valor Mensalidade (R$)", format="R$ %.2f"
        ),
    },
)
