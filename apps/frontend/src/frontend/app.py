import streamlit as st

st.set_page_config(
    page_title="PagControl - Sistema de Cobrança",
    page_icon="💳",
    layout="wide",
)

st.title("💳 PagControl")
st.subheader("Sistema de Cobrança e Gestão Recorrente para Academias")

st.markdown(
    """
    Bem-vindo ao **PagControl**. Este painel permite gerenciar matrículas de alunos, 
    acompanhar faturas e controlar a régua de cobrança automática contra inadimplência.
    """
)

col1, col2 = st.columns(2)

with col1:
    st.info(
        """
        ### 👥 Gestão de Alunos
        - Cadastre novos alunos com dia de vencimento e valor de mensalidade.
        - Consulte e gerencie os alunos ativos na academia.
        - Acesse pelo menu lateral em **Alunos**.
        """
    )

with col2:
    st.success(
        """
        ### 📊 Métricas e Inadimplência
        - Visualize faturas pendentes, pagas e atrasadas.
        - Acompanhe a curva de inadimplência e projeção de receita.
        - Acesse pelo menu lateral em **Metricas**.
        """
    )

st.divider()
st.caption("PagControl • Desenvolvido com FastAPI + Streamlit • Gerenciado com uv")
