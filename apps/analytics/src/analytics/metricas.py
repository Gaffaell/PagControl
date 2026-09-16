"""Calcula PDD (probabilidade de default) e curva de vintage a partir da base
sintética gerada por gerar_dados.py.

Este script só LÊ o banco DuckDB (não gera nem altera dados) - por isso abre
a conexão com read_only=True. Todo o cálculo é feito em SQL direto no DuckDB
(em vez de trazer os dados pro Python e calcular linha por linha), porque é
muito mais rápido para agregações desse tipo sobre ~105 mil registros.

Uso: uv run python src/analytics/metricas.py
"""

from pathlib import Path

import duckdb

DB_PATH = Path(__file__).parent / "data" / "pagcontrol_analytics.duckdb"


def main() -> None:
    con = duckdb.connect(str(DB_PATH), read_only=True)

    # ------------------------------------------------------------------
    # PDD (Probabilidade de Default) geral: de todas as faturas geradas,
    # qual fração terminou como "inadimplente"? O CASE WHEN ... THEN 1 ELSE 0
    # END transforma cada linha em 1 (se é inadimplente) ou 0 (se não é), e o
    # SUM soma isso tudo - é um jeito comum em SQL de "contar só o que
    # interessa" sem precisar de um WHERE separado.
    # ------------------------------------------------------------------
    print("=" * 60)
    print("PDD geral (probabilidade de inadimplência por fatura)")
    print("=" * 60)
    print(
        con.execute(
            """
            SELECT
                COUNT(*) AS total_faturas,
                SUM(CASE WHEN status = 'inadimplente' THEN 1 ELSE 0 END) AS inadimplentes,
                ROUND(100.0 * SUM(CASE WHEN status = 'inadimplente' THEN 1 ELSE 0 END) / COUNT(*), 2) AS pdd_pct
            FROM cobrancas_sinteticas
            """
        ).df()  # .df() converte o resultado da consulta num DataFrame do pandas, fácil de imprimir
    )

    # ------------------------------------------------------------------
    # A mesma conta de PDD, mas agora quebrada por perfil de risco do aluno.
    # O JOIN busca, pra cada fatura (cobrancas_sinteticas), o perfil_risco do
    # aluno dono dela (alunos_sinteticos) - sem o JOIN não teríamos acesso ao
    # perfil, porque ele está guardado na tabela de alunos, não na de faturas.
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("PDD por perfil de risco do aluno")
    print("=" * 60)
    print(
        con.execute(
            """
            SELECT
                a.perfil_risco,
                COUNT(*) AS total_faturas,
                ROUND(100.0 * SUM(CASE WHEN c.status = 'inadimplente' THEN 1 ELSE 0 END) / COUNT(*), 2) AS pdd_pct
            FROM cobrancas_sinteticas c
            JOIN alunos_sinteticos a ON a.id = c.aluno_id
            GROUP BY a.perfil_risco
            ORDER BY pdd_pct DESC
            """
        ).df()
    )

    # A mesma ideia, mas agrupando por modalidade em vez de perfil de risco -
    # serve como "teste de sanidade": como a modalidade é sorteada sem
    # nenhuma relação com o perfil de risco (ver gerar_dados.py), o esperado
    # é que os números aqui fiquem todos parecidos entre si.
    print("\n" + "=" * 60)
    print("PDD por modalidade")
    print("=" * 60)
    print(
        con.execute(
            """
            SELECT
                a.modalidade,
                COUNT(*) AS total_faturas,
                ROUND(100.0 * SUM(CASE WHEN c.status = 'inadimplente' THEN 1 ELSE 0 END) / COUNT(*), 2) AS pdd_pct
            FROM cobrancas_sinteticas c
            JOIN alunos_sinteticos a ON a.id = c.aluno_id
            GROUP BY a.modalidade
            ORDER BY pdd_pct DESC
            """
        ).df()
    )

    # ------------------------------------------------------------------
    # Curva de vintage de verdade: % ACUMULADO de alunos da safra que já
    # ficaram inadimplentes ao menos uma vez até cada mês de vida da conta
    # (não a taxa pontual de cada mês isolado, que é ruidosa e não é o
    # conceito de vintage usado em análise de risco de crédito).
    #
    # A consulta é dividida em três blocos com WITH (chamados "CTEs" -
    # Common Table Expressions), que funcionam como "tabelas temporárias"
    # nomeadas só pra deixar a query final mais fácil de ler:
    #
    #   1) primeiro_default: pra cada aluno que alguma vez ficou
    #      inadimplente, em qual mês de vida da conta (mes_relativo) isso
    #      aconteceu PELA PRIMEIRA VEZ (MIN). Quem nunca ficou inadimplente
    #      simplesmente não aparece aqui.
    #   2) alunos_safra: junta cada aluno com a safra dele (mês de matrícula,
    #      no formato "2026-09") e com o mês do primeiro default (ou NULL, se
    #      ele nunca ficou inadimplente - por isso o LEFT JOIN, que mantém o
    #      aluno na lista mesmo sem correspondência em primeiro_default).
    #   3) base: junta isso com as faturas de cada aluno, restrito a
    #      mes_relativo <= 12 (só nos interessa o primeiro ano de vida da
    #      conta pra este gráfico).
    #
    # A consulta final compara, linha a linha, se o aluno já tinha "estreado"
    # na inadimplência até aquele mes_relativo (mes_primeiro_default <=
    # mes_relativo) - é essa comparação que transforma um evento pontual
    # (o mês do primeiro default) numa métrica acumulada que só cresce.
    # ------------------------------------------------------------------
    vintage_query = """
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
        ORDER BY safra, mes_relativo
    """

    # A "curva de vintage média": pega o resultado de vintage_query (que tem
    # uma linha por safra + mês) e faz uma média PONDERADA pelo tamanho de
    # cada safra (SUM(pct * alunos) / SUM(alunos)) - assim uma safra com 200
    # alunos pesa mais no resultado final do que uma com 60, em vez de tratar
    # todas as safras como se tivessem o mesmo peso.
    # O "f" antes das aspas triplas é uma f-string: permite colar o texto de
    # vintage_query dentro desta nova consulta usando {vintage_query}, como
    # se vintage_query fosse uma "sub-tabela" chamada dentro do FROM (...).
    print("\n" + "=" * 60)
    print(
        "Curva de vintage média (todas as safras) — % acumulado inadimplente por mês de vida"
    )
    print("=" * 60)
    print(
        con.execute(
            f"""
            SELECT
                mes_relativo,
                COUNT(DISTINCT safra) AS safras_incluidas,
                SUM(alunos_na_safra) AS alunos_total,
                ROUND(SUM(pdd_acumulado_pct * alunos_na_safra) / SUM(alunos_na_safra), 2) AS pdd_acumulado_pct_medio
            FROM ({vintage_query})
            GROUP BY mes_relativo
            ORDER BY mes_relativo
            """
        ).df()
    )

    # Mostra o detalhe (não só a média) das 3 safras mais antigas, útil pra
    # inspecionar se os números de safras individuais fazem sentido antes de
    # confiar na média geral.
    print("\n" + "=" * 60)
    print("Curva de vintage por safra (3 safras mais antigas, para inspeção)")
    print("=" * 60)
    print(
        con.execute(
            f"""
            SELECT * FROM ({vintage_query})
            WHERE safra IN (SELECT DISTINCT safra FROM ({vintage_query}) ORDER BY safra LIMIT 3)
            ORDER BY safra, mes_relativo
            """
        )
        .df()
        .to_string()  # .to_string() imprime a tabela inteira, sem cortar linhas no meio
    )

    con.close()


if __name__ == "__main__":
    main()
