from turtle import st
from frontend.api.cliente import is_authenticated, login_verificacao

def render_login_page():
    st.title("Login")
    st.write("Por favor, insira suas credenciais para acessar o sistema.")

    with st.form(key="login_form", clear_on_submit=False):
        data = {}
        data["nome_de_usuario"] = st.text_input("Nome de usuário")
        data["senha"] = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Entrar")

        if submitted:
            if not data.nome_de_usuario or not data.senha:
                st.error("Por favor, preencha todos os campos.")
            else:
                if login_verificacao(data):
                    st.session_state.authenticated = True
                    st.success("Login bem-sucedido!")
                    st.experimental_rerun()
                else:
                    st.error("Nome de usuário ou senha incorretos.")