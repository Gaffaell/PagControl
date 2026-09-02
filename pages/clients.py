import datetime
import random

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

# Show app title and description.
st.set_page_config(page_title="Aluno", page_icon="👥")
st.title("👥 Alunos")
st.write(
    """
    Here you can see, edit any information 
    about your aluno and add a new alunos 
    """
)

# Create a random Pandas dataframe with existing tickets.
if "df" not in st.session_state:

    # Set seed for reproducibility.
    np.random.seed(42)

    # Make up some fake issue descriptions.
    issue_descriptions = [
        "Network connectivity issues in the office",
        "Software application crashing on startup",
        "Printer not responding to print commands",
        "Email server downtime",
        "Data backup failure",
        "Login authentication problems",
        "Website performance degradation",
        "Security vulnerability identified",
        "Hardware malfunction in the server room",
        "Employee unable to access shared files",
        "Database connection failure",
        "Mobile application not syncing data",
        "VoIP phone system issues",
        "VPN connection problems for remote employees",
        "System updates causing compatibility issues",
        "File server running out of storage space",
        "Intrusion detection system alerts",
        "Inventory management system errors",
        "Customer data not loading in CRM",
        "Collaboration tool not sending notifications",
    ]

    # Generate the dataframe with 100 rows/tickets.
    data = {
        "ID": [f"TICKET-{i}" for i in range(1100, 1000, -1)],
        "Issue": np.random.choice(issue_descriptions, size=100),
        "Status": np.random.choice(["Open", "In Progress", "Closed"], size=100),
        "Priority": np.random.choice(["High", "Medium", "Low"], size=100),
        "Date Submitted": [
            datetime.date(2023, 6, 1) + datetime.timedelta(days=random.randint(0, 182))
            for _ in range(100)
        ],
    }
    df = pd.DataFrame(data)

    # Save the dataframe in session state (a dictionary-like object that persists across
    # page runs). This ensures our data is persisted when the app updates.
    st.session_state.df = df


# Show a section to add a new ticket.
st.header("Adicionar um novo aluno")

# We're adding tickets via an `st.form` and some input widgets. If widgets are used
# in a form, the app will only rerun once the submit button is pressed.
with st.form("add_aluno_form"):
    nome = st.text_input("Nome completo", placeholder="EX: Rodrigo Costa Silva")
    email = st.text_input("Email", placeholder="EX: rodrigo.silva123@pagcontrol.com")
    telefone = st.text_input("Telefone", placeholder="EX: (11) 91234-5678")
    cep = st.text_input("CEP", placeholder="EX: 12342-112")
    endereco = st.text_input("Endereço", placeholder="EX: Rua das águias")
    numero = st.text_input("Número da casa", placeholder="EX: 123")
    complemento = st.text_input("Complemento", placeholder="EX: Casa 1")
    valor_mensalidade = st.number_input("Valor da mensalidade", placeholder="EX: 125,90") 
    submitted = st.form_submit_button("Submit")

if submitted:
    # Make a dataframe for the new ticket and append it to the dataframe in session
    # state.
    id_aluno = int(max(st.session_state.df.ID).split("-")[1])
    today = datetime.datetime.now().strftime("%m-%d-%Y")
    df_new = pd.DataFrame(
        [
            {
                "ID": f"{id_aluno+1}",
                "Nome": nome,
                "Email": email,
                "Telefone": telefone,
                "CEP": cep,
                "Endereço": endereco,
                "Numero": numero,
                "Complemento": complemento,
                "Valor da mensalidade": valor_mensalidade,
                "Status": "Open",
                "Date Submitted": today,
            }
        ]
    )

    # Show a little success message.
    st.write("Aluno cadastrado com sucesso! aqui está as informaçoes cadastradas:")
    st.dataframe(df_new, use_container_width=True, hide_index=True)
    st.session_state.df = pd.concat([df_new, st.session_state.df], axis=0)

# Show section to view and edit existing tickets in a table.
st.header("Alunos cadastrados")
st.write(f"Número de alunos cadastradas: `{len(st.session_state.df)}`")

st.info(
    "You can edit the tickets by double clicking on a cell. Note how the plots below "
    "update automatically! You can also sort the table by clicking on the column headers.",
    icon="✍️",
)

# Show the tickets dataframe with `st.data_editor`. This lets the user edit the table
# cells. The edited data is returned as a new dataframe.
edited_df = st.data_editor(
    st.session_state.df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Status": st.column_config.SelectboxColumn(
            "Status",
            help="Ticket status",
            options=["Open", "In Progress", "Closed"],
            required=True,
        ),
        "Priority": st.column_config.SelectboxColumn(
            "Priority",
            help="Priority",
            options=["High", "Medium", "Low"],
            required=True,
        ),
    },
    # Disable editing the ID and Date Submitted columns.
    disabled=["ID", "Date Submitted"],
)


st.set_page_config(page_title="Alunos manager", layout="centered", page_icon="👥")
