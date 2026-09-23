import pandas as pd
import streamlit as st
from frontend.api.cliente import (
    APIError,
    atualizar_aluno,
    criar_aluno,
    desativar_aluno,
    gerar_cobranca,
    listar_alunos,
    listar_cobrancas,
    registrar_pagamento,
)
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
        "Cadastre alunos e mantenha os dados das matrículas sincronizados com "
        "a API do PagControl."
    ),
)


def formatar_moeda(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def preparar_alunos(dados: list[dict]) -> pd.DataFrame:
    colunas = [
        "ID",
        "Nome",
        "Modalidade",
        "Mensalidade",
        "Vencimento",
        "Matrícula",
        "Status",
    ]
    if not dados:
        return pd.DataFrame(columns=colunas)

    registros = []
    for aluno in dados:
        registros.append(
            {
                "ID": aluno["id"],
                "Nome": aluno["nome"],
                "Modalidade": aluno.get("modalidade") or "Não informada",
                "Mensalidade": float(aluno["valor_mensalidade"]),
                "Vencimento": aluno["dia_vencimento"],
                "Matrícula": aluno["data_matricula"],
                "Status": "Ativo" if aluno["ativo"] else "Inativo",
            }
        )
    df = pd.DataFrame(registros, columns=colunas)
    df["Matrícula"] = pd.to_datetime(df["Matrícula"]).dt.date
    return df


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

alunos_df = preparar_alunos(alunos)
alunos_ativos = [aluno for aluno in alunos if aluno["ativo"]]
receita_mensal = sum(float(aluno["valor_mensalidade"]) for aluno in alunos_ativos)

metric1, metric2, metric3 = st.columns(3, gap="medium")
with metric1:
    metric_card("Alunos cadastrados", str(len(alunos)), "Dados persistidos na API")
with metric2:
    metric_card(
        "Matrículas ativas",
        str(len(alunos_ativos)),
        "Situação atual",
        accent="#1d4ed8",
    )
with metric3:
    metric_card(
        "Receita mensal prevista",
        formatar_moeda(receita_mensal),
        "Alunos ativos",
        accent="#7c3aed",
    )

cadastro_tab, gestao_tab, pagamento_tab = st.tabs(
    ["Cadastrar aluno", "Consultar e editar", "Registrar pagamento"]
)

with cadastro_tab:
    section_title("Novo aluno")
    st.caption("Os campos abaixo correspondem ao contrato atual da API.")

    with st.form("add_aluno_form", clear_on_submit=True):
        col1, col2 = st.columns(2, gap="large")
        with col1:
            nome = st.text_input(
                "Nome completo *",
                placeholder="Ex.: Maria Souza Oliveira",
            )
            modalidade = st.text_input(
                "Modalidade",
                placeholder="Ex.: Musculação",
            )
        with col2:
            valor_mensalidade = st.number_input(
                "Valor da mensalidade (R$) *",
                min_value=0.01,
                value=120.0,
                step=10.0,
                format="%.2f",
            )
            dia_vencimento = st.number_input(
                "Dia de vencimento *",
                min_value=1,
                max_value=31,
                value=10,
                step=1,
            )

        cadastrar = st.form_submit_button("Cadastrar aluno", width="stretch")

    if cadastrar:
        nome_limpo = nome.strip()
        if not nome_limpo:
            st.error("Preencha o nome do aluno para concluir o cadastro.")
        else:
            try:
                aluno_criado = criar_aluno(
                    {
                        "nome": nome_limpo,
                        "modalidade": modalidade.strip() or None,
                        "valor_mensalidade": float(valor_mensalidade),
                        "dia_vencimento": int(dia_vencimento),
                    }
                )
                aluno_id = aluno_criado["id"]
                cobranca_criada = gerar_cobranca(aluno_id)
            except APIError as exc:
                st.error(str(exc))
            else:
                st.success(
                    f"Aluno **{aluno_criado['nome']}** cadastrado e persistido com sucesso."
                )
                st.rerun()

with gestao_tab:
    section_title("Base de alunos")

    filter_col, status_filter_col = st.columns([2, 1], gap="medium")
    with filter_col:
        busca = st.text_input(
            "Buscar aluno",
            placeholder="Digite o nome ou a modalidade",
            label_visibility="collapsed",
        )
    with status_filter_col:
        filtro_status = st.selectbox(
            "Filtrar por status",
            ["Todos", "Ativo", "Inativo"],
            label_visibility="collapsed",
        )

    alunos_exibidos = alunos_df.copy()
    if busca:
        mascara = alunos_exibidos["Nome"].astype(str).str.contains(
            busca, case=False, na=False, regex=False
        ) | alunos_exibidos["Modalidade"].astype(str).str.contains(
            busca, case=False, na=False, regex=False
        )
        alunos_exibidos = alunos_exibidos[mascara]

    if filtro_status != "Todos":
        alunos_exibidos = alunos_exibidos[alunos_exibidos["Status"] == filtro_status]

    st.caption(f"Exibindo {len(alunos_exibidos)} de {len(alunos_df)} registro(s).")

    if alunos_exibidos.empty:
        st.info("Nenhum aluno encontrado para os filtros selecionados.")
    else:
        st.dataframe(
            alunos_exibidos,
            width="stretch",
            hide_index=True,
            column_config={
                "ID": st.column_config.NumberColumn("ID", format="%d"),
                "Mensalidade": st.column_config.NumberColumn(
                    "Mensalidade",
                    format="R$ %.2f",
                ),
                "Vencimento": st.column_config.NumberColumn(
                    "Vencimento",
                    format="Dia %d",
                ),
                "Matrícula": st.column_config.DateColumn(
                    "Matrícula",
                    format="DD/MM/YYYY",
                ),
            },
        )

    if alunos:
        section_title("Editar matrícula")
        aluno_por_id = {aluno["id"]: aluno for aluno in alunos}
        aluno_id = st.selectbox(
            "Selecione um aluno",
            options=list(aluno_por_id),
            key="aluno_para_editar",
            format_func=lambda item: (
                f"{aluno_por_id[item]['nome']} · "
                f"{'Ativo' if aluno_por_id[item]['ativo'] else 'Inativo'}"
            ),
        )
        selecionado = aluno_por_id[aluno_id]

        with st.form("editar_aluno_form"):
            edit_col1, edit_col2 = st.columns(2, gap="large")
            with edit_col1:
                nome_editado = st.text_input("Nome completo", value=selecionado["nome"])
                modalidade_editada = st.text_input(
                    "Modalidade",
                    value=selecionado.get("modalidade") or "",
                )
            with edit_col2:
                valor_editado = st.number_input(
                    "Valor da mensalidade (R$)",
                    min_value=0.01,
                    value=float(selecionado["valor_mensalidade"]),
                    step=10.0,
                    format="%.2f",
                )
                vencimento_editado = st.number_input(
                    "Dia de vencimento",
                    min_value=1,
                    max_value=31,
                    value=int(selecionado["dia_vencimento"]),
                    step=1,
                )

            salvar = st.form_submit_button("Salvar alterações", width="stretch")

        if salvar:
            if not nome_editado.strip():
                st.error("O nome do aluno não pode ficar vazio.")
            else:
                try:
                    atualizado = atualizar_aluno(
                        aluno_id,
                        {
                            "nome": nome_editado.strip(),
                            "modalidade": modalidade_editada.strip() or None,
                            "valor_mensalidade": float(valor_editado),
                            "dia_vencimento": int(vencimento_editado),
                        },
                    )
                except APIError as exc:
                    st.error(str(exc))
                else:
                    st.success(
                        f"Dados de **{atualizado['nome']}** atualizados com sucesso."
                    )
                    st.rerun()

        acao_status = (
            "Desativar matrícula" if selecionado["ativo"] else "Reativar matrícula"
        )
        st.caption(
            "A desativação preserva o aluno e seu histórico financeiro no banco de dados."
        )
        confirmar_status = st.checkbox(
            f"Confirmo que desejo {acao_status.lower()} de {selecionado['nome']}",
            key=f"confirmar_status_{aluno_id}",
        )
        if st.button(
            acao_status,
            disabled=not confirmar_status,
            width="stretch",
            type="secondary",
        ):
            try:
                if selecionado["ativo"]:
                    desativar_aluno(aluno_id)
                    mensagem = "desativada"
                else:
                    atualizar_aluno(aluno_id, {"ativo": True})
                    mensagem = "reativada"
            except APIError as exc:
                st.error(str(exc))
            else:
                st.success(
                    f"Matrícula de **{selecionado['nome']}** {mensagem} com sucesso."
                )
                st.rerun()

section_title("Registro de pagamentos")
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

with pagamento_tab:
    section_title("Registrar pagamento")
    st.caption("Os campos abaixo correspondem ao contrato atual da API.")

    if alunos:
        section_title("Registrar pagamento de aluno")
        aluno_por_id = {aluno["id"]: aluno for aluno in alunos}
        aluno_id = st.selectbox(
            "Selecione um aluno",
            options=list(aluno_por_id),
            key="aluno_para_registrar_pagamento",
            format_func=lambda item: (
                f"{aluno_por_id[item]['nome']} · "
                f"{'Ativo' if aluno_por_id[item]['ativo'] else 'Inativo'}"
            ),
        )
        selecionado = aluno_por_id[aluno_id]
        cobrancas_do_aluno = [
            cobranca
            for cobranca in cobrancas
            if cobranca["aluno_id"] == aluno_id and cobranca["status"] != "pago"
        ]

        if not cobrancas_do_aluno:
            st.info("Este aluno não possui cobranças pendentes de pagamento.")
        else:
            cobranca_por_id = {
                cobranca["id"]: cobranca for cobranca in cobrancas_do_aluno
            }
            cobranca_id = st.selectbox(
                "Selecione a cobrança",
                options=list(cobranca_por_id),
                format_func=lambda item: (
                    (
                        f"#{item} · {cobranca_por_id[item]['competencia']} · "
                        f"R$ {float(cobranca_por_id[item]['valor']):,.2f}"
                    )
                    .replace(",", "X")
                    .replace(".", ",")
                    .replace("X", ".")
                ),
            )
            cobranca_selecionada = cobranca_por_id[cobranca_id]

            with st.form("registrar_pagamento_form"):
                id_col, forma_col, data_col = st.columns(3, gap="medium")
                with id_col:
                    st.number_input(
                        "Número ID da cobrança",
                        value=cobranca_id,
                        disabled=True,
                    )
                with forma_col:
                    forma_pagamento = st.selectbox(
                        "Forma de pagamento",
                        ["Pix", "Cnab"],
                        index=0,
                    )
                with data_col:
                    data_pagamento = st.date_input("Data do pagamento")

                st.caption(
                    f"Competência: {cobranca_selecionada['competencia']} · "
                    f"Valor: {formatar_moeda(float(cobranca_selecionada['valor']))}"
                )
                salvar = st.form_submit_button(
                    "Registrar pagamento",
                    width="stretch",
                )

            if salvar:
                try:
                    atualizado = registrar_pagamento(
                        cobranca_id,
                        forma_pagamento.lower(),
                        data_pagamento.isoformat(),
                    )
                except APIError as exc:
                    st.error(str(exc))
                else:
                    st.success(
                        f"Pagamento da cobrança **#{atualizado['id']}** de "
                        f"**{selecionado['nome']}** registrado com sucesso."
                    )
                    st.rerun()
