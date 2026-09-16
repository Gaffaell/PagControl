"""Gera o gráfico da curva de vintage a partir da base sintética.

Mostra, para um punhado de safras (meses de matrícula) e para a média geral,
como o % acumulado de inadimplência cresce com os meses de vida da conta.

Uso: uv run python src/analytics/grafico_vintage.py
"""

from pathlib import Path

import duckdb
import matplotlib.pyplot as plt

DB_PATH = Path(__file__).parent / "data" / "pagcontrol_analytics.duckdb"
SAIDA_PATH = Path(__file__).parent / "data" / "curva_vintage.png"

# Mesma consulta de curva de vintage explicada em detalhe em metricas.py:
# calcula, por safra (mês de matrícula) e mês de vida da conta, o % de alunos
# que já ficaram inadimplentes ao menos uma vez até aquele mês (métrica
# acumulada, por isso só cresce - nunca cai de um mês pro seguinte).
VINTAGE_QUERY = """
    WITH primeiro_default AS (
        SELECT aluno_id, MIN(mes_relativo) AS mes_primeiro_default
        FROM cobrancas_sinteticas
        WHERE status = 'inadimplente'
        GROUP BY aluno_id
    ),
    alunos_safra AS (
        SELECT a.id AS aluno_id, strftime(a.data_matricula, '%Y-%m') AS safra, p.mes_primeiro_default
        FROM alunos_sinteticos a
        LEFT JOIN primeiro_default p ON p.aluno_id = a.id
    ),
    base AS (
        SELECT DISTINCT ap.safra, ap.aluno_id, ap.mes_primeiro_default, c.mes_relativo
        FROM alunos_safra ap
        JOIN cobrancas_sinteticas c ON c.aluno_id = ap.aluno_id
        WHERE c.mes_relativo <= 12
    )
    SELECT
        safra,
        mes_relativo,
        COUNT(*) AS alunos_na_safra,
        ROUND(
            100.0 * SUM(
                CASE WHEN mes_primeiro_default IS NOT NULL AND mes_primeiro_default <= mes_relativo
                     THEN 1 ELSE 0 END
            ) / COUNT(*), 2
        ) AS pdd_acumulado_pct
    FROM base
    GROUP BY safra, mes_relativo
"""


def main() -> None:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    # Roda a consulta e já traz o resultado como um DataFrame do pandas
    # (uma linha por combinação de safra + mês de vida da conta).
    vintage = con.execute(VINTAGE_QUERY).df()

    # Calcula a linha "média geral": para cada mes_relativo, uma média das
    # taxas de todas as safras, PONDERADA pelo tamanho de cada safra (uma
    # safra com mais alunos pesa mais na média do que uma pequena).
    # .groupby("mes_relativo") separa os dados em grupos, um por mês; .apply
    # roda a conta de média ponderada em cada grupo separadamente; e
    # .reset_index transforma o resultado de volta numa tabela normal, com
    # "mes_relativo" e "pdd_acumulado_pct_medio" como colunas.
    media = (
        vintage.groupby("mes_relativo")
        .apply(
            lambda g: (
                (g["pdd_acumulado_pct"] * g["alunos_na_safra"]).sum()
                / g["alunos_na_safra"].sum()
            )
        )
        .reset_index(name="pdd_acumulado_pct_medio")
    )

    # 6 safras espalhadas ao longo do período, só para ilustrar a dispersão
    # entre cohortes por trás da média. Em vez de pegar as 6 primeiras (que
    # ficariam todas próximas no tempo), o "passo" pula de forma uniforme
    # pela lista ordenada de safras, garantindo uma amostra espalhada do
    # início ao fim do período de 36 meses.
    safras_ordenadas = sorted(vintage["safra"].unique())
    passo = max(1, len(safras_ordenadas) // 6)
    safras_amostra = safras_ordenadas[::passo][
        :6
    ]  # [::passo] pula de "passo" em "passo" itens

    # Cria a figura e os eixos do gráfico (a "tela" onde tudo vai ser desenhado).
    fig, ax = plt.subplots(figsize=(9, 5.5))

    # Uma linha fina e semitransparente (alpha=0.55) para cada safra de
    # exemplo, sem ela sobrepor visualmente demais a linha da média.
    for safra in safras_amostra:
        dados_safra = vintage[vintage["safra"] == safra].sort_values("mes_relativo")
        ax.plot(
            dados_safra["mes_relativo"],
            dados_safra["pdd_acumulado_pct"],
            linewidth=1.2,
            alpha=0.55,
            label=f"Safra {safra}",
        )

    # A linha da média geral, mais grossa e em cor sólida, para se destacar
    # das safras individuais (que servem só de referência visual).
    ax.plot(
        media["mes_relativo"],
        media["pdd_acumulado_pct_medio"],
        linewidth=3,
        color="#0f766e",
        label="Média geral",
    )

    # Rótulos e legenda do gráfico. Sem título aqui de propósito: a imagem é
    # sempre embutida nos PDFs com uma legenda "Figura N — ..." logo abaixo,
    # que já descreve o gráfico - um título dentro da própria imagem ficaria
    # redundante com essa legenda.
    ax.set_xlabel("Meses desde a matrícula")
    ax.set_ylabel("% de alunos inadimplentes (acumulado)")
    ax.set_xticks(
        range(13)
    )  # marca todos os meses de 0 a 12 no eixo X, sem pular nenhum
    ax.grid(True, alpha=0.3)  # linhas de grade leves, ajudam a ler os valores
    ax.legend(loc="upper left", fontsize=8, ncols=2)
    fig.tight_layout()  # ajusta as margens automaticamente pra nada ficar cortado

    # Salva a imagem em disco. dpi=150 dá uma resolução boa o suficiente pra
    # ficar nítida tanto na tela quanto embutida num PDF.
    SAIDA_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(SAIDA_PATH, dpi=150)
    print(f"Gráfico salvo em {SAIDA_PATH}")


if __name__ == "__main__":
    main()
