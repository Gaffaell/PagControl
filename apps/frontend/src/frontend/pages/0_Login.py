import streamlit as st
from frontend.api.cliente import (
    validar_administrador,
)
from frontend.ui import (
    apply_theme,
    page_header,
    paleta_atual,
    sidebar_brand,
)

apply_theme()
paleta_atual()
sidebar_brand()

st.set_page_config(
    page_title="Login",
    page_icon="🔑",
    layout="wide",
    initial_sidebar_state="auto",
)

page_header(
    "Login",
    "Acesso ao sistema",
    ("Faça login para acessar o sistema PagControl. Conecte-se à API do PagControl."),
)

with st.form("login_form", clear_on_submit=False):
    email = st.text_input("Email", placeholder="Dígite o seu email")
    senha = st.text_input("Senha", type="password", placeholder="Dígite a sua senha")
    submit_button = st.form_submit_button("Entrar")

if submit_button:
    email_limpo = email.strip()
    senha_limpo = senha.strip()
    dados = {"email": email_limpo, "senha": senha_limpo}
    if validar_administrador(dados):
        st.session_state["authenticated"] = True
        st.success("Login bem-sucedido!")
        st.switch_page("pages/1_Alunos.py")
        st.rerun()
    else:
        st.error("Email ou senha incorretos. Tente novamente.")
#   if username == "admin" and password == "admin":
#       st.session_state["authenticated"] = True
#       st.success("Login bem-sucedido!")
#       st.switch_page("pages/1_Alunos.py")
#       st.rerun()
#   else:
#       st.error("Usuário ou senha incorretos. Tente novamente.")
