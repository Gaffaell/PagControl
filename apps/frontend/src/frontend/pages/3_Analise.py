from datetime import date

import altair as alt
import pandas as pd
import streamlit as st
from frontend.api.cliente import (
    APIError,
    limpar_cache_metricas,
    obter_arrecadacao,
    obter_resumo_metricas,
)
from frontend.ui import (
    EIXO_MESES_EXPR,
    EIXO_NUMERO_EXPR,
    MESES_ABREV,
    abreviar_numero,
    api_status,
    apply_theme,
    formatar_competencia,
    formatar_inteiro,
    formatar_moeda,
    formatar_moeda_inteira,
    insights_box,
    metric_grid,
    page_header,
    paleta_atual,
    rotulo_mes,
    section_title,
    sidebar_brand,
)

PALETA = paleta_atual()
COR_DESTAQUE = PALETA["recebido"]
COR_NEUTRA = PALETA["previsto"]
CORES_CURSOS = [
    PALETA["recebido"],
    PALETA["card_2"],
    PALETA["card_3"],
    PALETA["pago"],
    PALETA["pendente"],
]
CURSOS_NA_EVOLUCAO = 5
TODOS_OS_ANOS = "Todos os anos"
ANO_INTEIRO = "Ano inteiro"
TODOS_OS_CURSOS = "Todos os cursos"
NAO_INFORMADO = "Não informado"
SEM_INFORMACAO = {NAO_INFORMADO, "Não informada"}  # valores sem o dado preenchido

# Nomes curtos: a coluna do gráfico é estreita (as horas estão na página de Métricas).
TURNOS = {"manha": "Manhã", "tarde": "Tarde", "noite": "Noite"}
ORDEM_TURNOS = [*TURNOS.values(), NAO_INFORMADO]
DIAS = {
    "segunda": "Segunda",
    "terca": "Terça",
    "quarta": "Quarta",
    "quinta": "Quinta",
    "sexta": "Sexta",
    "sabado": "Sábado",
    "domingo": "Domingo",
}
ORDEM_DIAS = [*DIAS.values(), NAO_INFORMADO]

st.set_page_config(
    page_title="Análise - PagControl",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="auto",
)

apply_theme()
sidebar_brand()

page_header(
    "Análise do negócio",
    "O que vende e quem paga",
    (
        "Escolha o ano (e, se quiser, o mês) para ver quais cursos mais faturam e "
        "qual perfil de aluno mais arrecada."
    ),
)

if st.sidebar.button("🔄 Atualizar dados", width="stretch"):
    limpar_cache_metricas()
    st.rerun()

try:
    resumo_geral = obter_resumo_metricas()
except APIError as exc:
    api_status(False)
    st.error(str(exc))
    st.info(
        "Inicie o backend com `uv run --package backend uvicorn backend.api:app --reload` "
        "e recarregue esta página."
    )
    st.stop()

api_status(True)

competencias = sorted(resumo_geral["competencias"])
if not competencias:
    st.info("Ainda não há cobranças registradas para analisar.")
    st.stop()

# ---------------------------------------------------------------- filtros
# Linha de anos (todos os que têm cobrança); ao escolher um ano, aparece a linha
# dos meses daquele ano.
anos = sorted({c[:4] for c in competencias})
ano_escolhido = st.pills(
    "Ano",
    [*anos, TODOS_OS_ANOS],
    default=anos[-1],
    key="analise_ano",
    help="Todos os anos com cobrança registrada. 'Todos os anos' soma a carteira inteira.",
)
if ano_escolhido is None:  # clicar de novo no pill selecionado o desmarca
    ano_escolhido = anos[-1]

mes_escolhido: str | None = None
if ano_escolhido == TODOS_OS_ANOS:
    periodo = None
    descricao_periodo = "todos os anos"
else:
    meses_do_ano = [c for c in competencias if c.startswith(ano_escolhido)]
    por_rotulo = {MESES_ABREV[int(c[5:7]) - 1]: c for c in meses_do_ano}
    escolha_mes = st.pills(
        "Mês",
        [ANO_INTEIRO, *por_rotulo],
        default=ANO_INTEIRO,
        key=f"analise_mes_{ano_escolhido}",  # trocar de ano volta para "Ano inteiro"
        help="Ao clicar em um ano aparecem os meses dele; escolha um para ver só aquele mês.",
    )
    mes_escolhido = por_rotulo.get(escolha_mes or ANO_INTEIRO)
    periodo = mes_escolhido or ano_escolhido
    descricao_periodo = (
        formatar_competencia(mes_escolhido) if mes_escolhido else f"ano {ano_escolhido}"
    )

st.html(
    '<hr style="border:none;border-top:2px solid var(--pc-border);margin:.6rem 0 1rem">'
)

try:
    resumo = obter_resumo_metricas(periodo) if periodo else resumo_geral
    arrecadacao = obter_arrecadacao(periodo)
except APIError as exc:
    st.error(str(exc))
    st.stop()

mes_corrente = f"{date.today():%Y-%m}"
periodo_inclui_mes_corrente = (
    periodo is None or mes_corrente.startswith(periodo) or mes_corrente == periodo
)
if periodo_inclui_mes_corrente and mes_corrente in competencias:
    st.caption(
        f"Período: **{descricao_periodo}**. O mês corrente ({rotulo_mes(mes_corrente)}) "
        "ainda está em andamento: parte das cobranças segue pendente e o valor "
        "recebido tende a subir até o fechamento."
    )
else:
    st.caption(f"Período: **{descricao_periodo}**.")


def normalizar_modalidade(valor: str | None) -> str:
    if not valor or not valor.strip():
        return "Não informada"
    return valor.strip().title()


def barras_horizontais(
    df: pd.DataFrame,
    categoria: str,
    valor: str,
    ordem: list[str],
    *,
    titulo_x: str,
    tooltip: list[alt.Tooltip],
    compacto: bool = False,
) -> alt.LayerChart:
    """Barras horizontais com rótulo "valor · participação"; só a maior barra
    ganha a cor de destaque, o resto fica num tom neutro. No modo `compacto`
    (gráficos em colunas estreitas) o rótulo perde o "R$" e a folga à direita
    aumenta, para o texto não ser cortado."""
    df = df.copy()
    total = df[valor].sum() or 1.0
    df["Participação"] = df[valor] / total * 100
    df["Rótulo"] = df.apply(
        lambda linha: (
            f"{abreviar_numero(linha[valor], moeda=not compacto)} · "
            + f"{linha['Participação']:.1f}%".replace(".", ",")
        ),
        axis=1,
    )
    df["Destaque"] = df[valor] == df[valor].max()
    limite = df[valor].max() * (1.9 if compacto else 1.5)
    escala_x = alt.Scale(domain=[0, limite])
    barras = (
        alt.Chart(df)
        .mark_bar(cornerRadiusTopRight=6, cornerRadiusBottomRight=6, size=20)
        .encode(
            y=alt.Y(
                f"{categoria}:N", sort=ordem, title=None, axis=alt.Axis(labelPadding=8)
            ),
            x=alt.X(
                f"{valor}:Q",
                title=titulo_x,
                scale=escala_x,
                axis=alt.Axis(
                    gridColor="#eef2f6", titlePadding=10, labelExpr=EIXO_NUMERO_EXPR
                ),
            ),
            color=alt.Color(
                "Destaque:N",
                scale=alt.Scale(domain=[True, False], range=[COR_DESTAQUE, COR_NEUTRA]),
                legend=None,
            ),
            tooltip=tooltip,
        )
        .properties(height=max(150, 32 * len(df)))
    )
    rotulos = (
        alt.Chart(df)
        .mark_text(align="left", dx=6, fontSize=11, color="#475569")
        .encode(
            y=alt.Y(f"{categoria}:N", sort=ordem),
            x=alt.X(f"{valor}:Q", scale=escala_x),
            text="Rótulo:N",
        )
    )
    return (barras + rotulos).configure_view(strokeWidth=0)


# ------------------------------------------------- 1) faturamento por curso
section_title("Faturamento — o que mais vende")

df_cursos = pd.DataFrame(
    [
        {
            "Curso": normalizar_modalidade(item["modalidade"]),
            "Competência": item["competencia"],
            "Cobranças": item["quantidade"],
            "Faturamento": item["valor"],
        }
        for item in resumo["por_modalidade"]
    ]
)
total_cobrado = sum(linha["valor_cobrado"] for linha in arrecadacao["linhas"])
total_recebido = sum(linha["valor_recebido"] for linha in arrecadacao["linhas"])

if df_cursos.empty:
    st.caption("Não há cobranças neste período.")
else:
    ranking = (
        df_cursos.groupby("Curso", as_index=False)
        .agg(Cobranças=("Cobranças", "sum"), Faturamento=("Faturamento", "sum"))
        .sort_values("Faturamento", ascending=False)
    )
    lider = ranking.iloc[0]
    participacao_lider = lider["Faturamento"] / (ranking["Faturamento"].sum() or 1)
    recebido_pct = f"{total_recebido / total_cobrado * 100:.1f}%".replace(".", ",")
    metric_grid(
        [
            {
                "label": "Faturamento (cobrado)",
                "value": formatar_moeda_inteira(total_cobrado),
                "delta": f"{formatar_inteiro(ranking['Cobranças'].sum())} cobranças",
            },
            {
                "label": "Recebido",
                "value": formatar_moeda_inteira(total_recebido),
                "delta": f"{recebido_pct} do cobrado",
                "accent": PALETA["card_2"],
            },
            {
                "label": "Curso que mais fatura",
                "value": lider["Curso"],
                "delta": f"{participacao_lider * 100:.1f}% do faturamento".replace(
                    ".", ","
                ),
                "accent": PALETA["card_3"],
            },
            {
                "label": "Cursos com cobrança",
                "value": str(len(ranking)),
                "delta": "no período",
                "accent": PALETA["card_4"],
            },
        ]
    )

    ranking["Cobranças_txt"] = ranking["Cobranças"].apply(formatar_inteiro)
    ranking["Faturamento_txt"] = ranking["Faturamento"].apply(formatar_moeda)
    st.altair_chart(
        barras_horizontais(
            ranking,
            "Curso",
            "Faturamento",
            ranking["Curso"].tolist(),
            titulo_x="Faturamento (R$)",
            tooltip=[
                alt.Tooltip("Curso:N"),
                alt.Tooltip("Cobranças_txt:N", title="Cobranças"),
                alt.Tooltip("Faturamento_txt:N", title="Faturamento"),
            ],
        ),
        width="stretch",
    )

    meses_no_periodo = sorted(df_cursos["Competência"].unique())
    if len(meses_no_periodo) > 1:
        principais = ranking["Curso"].head(CURSOS_NA_EVOLUCAO).tolist()
        evolucao = (
            df_cursos[df_cursos["Curso"].isin(principais)]
            .groupby(["Competência", "Curso"], as_index=False)["Faturamento"]
            .sum()
        )
        evolucao["Mês"] = evolucao["Competência"].apply(rotulo_mes)
        evolucao["Faturamento_txt"] = evolucao["Faturamento"].apply(formatar_moeda)
        ordem_meses = [rotulo_mes(c) for c in meses_no_periodo]
        base_linha = alt.Chart(evolucao).encode(
            x=alt.X(
                "Mês:N",
                sort=ordem_meses,
                title=None,
                axis=alt.Axis(
                    labelAngle=0,
                    labelOverlap=False,
                    labelFontWeight="bold",
                    labelFontSize=10,
                    labelExpr=EIXO_MESES_EXPR,
                ),
            ),
            y=alt.Y(
                "Faturamento:Q",
                title="Faturamento (R$)",
                axis=alt.Axis(gridColor="#eef2f6", labelExpr=EIXO_NUMERO_EXPR),
            ),
            color=alt.Color(
                "Curso:N",
                sort=principais,
                scale=alt.Scale(
                    domain=principais, range=CORES_CURSOS[: len(principais)]
                ),
                legend=alt.Legend(title=None, orient="bottom"),
            ),
            tooltip=[
                alt.Tooltip("Mês:N"),
                alt.Tooltip("Curso:N"),
                alt.Tooltip("Faturamento_txt:N", title="Faturamento"),
            ],
        )
        st.altair_chart(
            (
                base_linha.mark_line(strokeWidth=2.5)
                + base_linha.mark_point(size=45, filled=True)
            )
            .properties(height=280)
            .configure_view(strokeWidth=0),
            width="stretch",
        )
        st.caption(
            f"Evolução mensal dos {len(principais)} cursos que mais faturam no período."
        )

# ------------------------------------------------ 2) arrecadação por perfil
section_title("Arrecadação — quem paga")

df_perfil = pd.DataFrame(arrecadacao["linhas"])
if df_perfil.empty:
    st.caption("Não há cobranças neste período.")
    st.stop()

df_perfil["Curso"] = df_perfil["modalidade"].apply(normalizar_modalidade)
df_perfil["Faixa etária"] = df_perfil["faixa_etaria"]
df_perfil["Turno"] = df_perfil["turno"].map(TURNOS).fillna(NAO_INFORMADO)
df_perfil["Dia da semana"] = df_perfil["dia_semana"].map(DIAS).fillna(NAO_INFORMADO)

cursos = sorted(df_perfil["Curso"].unique())
curso_escolhido = st.selectbox(
    "Curso",
    [TODOS_OS_CURSOS, *cursos],
    key="analise_curso",
    help=(
        "Escolha um curso para ver o perfil de quem mais paga nele; 'Todos os "
        "cursos' mostra a carteira inteira."
    ),
)
if curso_escolhido != TODOS_OS_CURSOS:
    df_perfil = df_perfil[df_perfil["Curso"] == curso_escolhido]

recebido_curso = df_perfil["valor_recebido"].sum()
cobrado_curso = df_perfil["valor_cobrado"].sum()
if recebido_curso <= 0:
    st.caption(
        "Nenhuma cobrança paga neste período e curso; ainda não há arrecadação para "
        "analisar."
    )
    st.stop()


def somar_por(coluna: str) -> pd.DataFrame:
    """Soma recebido/cobrado/alunos por uma característica, com tooltip pronto."""
    agrupado = df_perfil.groupby(coluna, as_index=False).agg(
        Recebido=("valor_recebido", "sum"),
        Cobrado=("valor_cobrado", "sum"),
        Alunos=("alunos", "sum"),
    )
    agrupado["Recebido_txt"] = agrupado["Recebido"].apply(formatar_moeda)
    agrupado["Taxa"] = (
        (
            agrupado["Recebido"]
            / agrupado["Cobrado"].where(agrupado["Cobrado"] > 0)
            * 100
        )
        .fillna(0)
        .apply(lambda v: f"{v:.1f}%".replace(".", ","))
    )
    agrupado["Alunos_txt"] = agrupado["Alunos"].apply(formatar_inteiro)
    return agrupado


def grafico_perfil(coluna: str, ordem: list[str]) -> alt.LayerChart:
    dados = somar_por(coluna)
    dados = dados[dados[coluna].isin(ordem)]
    dados = dados[dados["Recebido"] > 0]
    ordem_presente = [item for item in ordem if item in set(dados[coluna])]
    return barras_horizontais(
        dados,
        coluna,
        "Recebido",
        ordem_presente,
        titulo_x="Recebido (R$)",
        compacto=True,
        tooltip=[
            alt.Tooltip(f"{coluna}:N"),
            alt.Tooltip("Recebido_txt:N", title="Recebido"),
            alt.Tooltip("Taxa:N", title="Recebido do cobrado"),
            alt.Tooltip("Alunos_txt:N", title="Alunos"),
        ],
    )


ordem_faixas = [
    f
    for f in arrecadacao["ordem_faixas_etarias"]
    if f in set(df_perfil["Faixa etária"])
]
col_faixa, col_turno, col_dia = st.columns(3, gap="medium")
with col_faixa:
    st.markdown("**Faixa etária**")
    st.altair_chart(grafico_perfil("Faixa etária", ordem_faixas), width="stretch")
with col_turno:
    st.markdown("**Turno**")
    st.altair_chart(grafico_perfil("Turno", ORDEM_TURNOS), width="stretch")
with col_dia:
    st.markdown("**Dia da semana**")
    st.altair_chart(grafico_perfil("Dia da semana", ORDEM_DIAS), width="stretch")


# Resumo em frases: o que mais arrecada em cada característica (ignorando quem não
# tem a informação preenchida) e a combinação faixa etária + turno de maior valor.
def maior(coluna: str) -> tuple[str, float] | None:
    dados = somar_por(coluna)
    dados = dados[~dados[coluna].isin(SEM_INFORMACAO) & (dados["Recebido"] > 0)]
    if dados.empty:
        return None
    linha = dados.sort_values("Recebido", ascending=False).iloc[0]
    return linha[coluna], linha["Recebido"] / recebido_curso


def percentual(fracao: float) -> str:
    return f"{fracao * 100:.1f}%".replace(".", ",")


escopo = (
    "na carteira inteira"
    if curso_escolhido == TODOS_OS_CURSOS
    else f"em {curso_escolhido}"
)
frases: list[dict] = []
for coluna, titulo in (
    ("Faixa etária", "Faixa etária que mais paga"),
    ("Turno", "Turno que mais paga"),
    ("Dia da semana", "Dia que mais arrecada"),
):
    achado = maior(coluna)
    if achado:
        nome, fracao = achado
        frases.append(
            {
                "tipo": "info",
                "titulo": titulo,
                "texto": (
                    f"{nome} concentra {percentual(fracao)} do valor recebido "
                    f"{escopo} ({descricao_periodo})."
                ),
            }
        )

combinacao = (
    df_perfil[
        ~df_perfil["Faixa etária"].isin(SEM_INFORMACAO)
        & ~df_perfil["Turno"].isin(SEM_INFORMACAO)
    ]
    .groupby(["Faixa etária", "Turno"], as_index=False)["valor_recebido"]
    .sum()
    .sort_values("valor_recebido", ascending=False)
)
if not combinacao.empty and combinacao.iloc[0]["valor_recebido"] > 0:
    topo = combinacao.iloc[0]
    frases.append(
        {
            "tipo": "alta",
            "titulo": "Perfil que mais arrecada",
            "texto": (
                f"{topo['Faixa etária']} no turno da {topo['Turno'].lower()}: "
                f"{abreviar_numero(topo['valor_recebido'], moeda=True)} recebidos "
                f"({percentual(topo['valor_recebido'] / recebido_curso)} do total)."
            ),
        }
    )

taxa_curso = percentual(recebido_curso / cobrado_curso) if cobrado_curso else "—"
if frases:
    insights_box(
        frases,
        (
            f"Recebido: {formatar_moeda(recebido_curso)} de {formatar_moeda(cobrado_curso)} "
            f"cobrados ({taxa_curso}). O cadastro ainda não tem o sexo do aluno, por "
            "isso o perfil usa faixa etária, turno e dia da semana."
        ),
        titulo="Perfil de quem mais paga",
    )
