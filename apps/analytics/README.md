# analytics

Módulo de Big Data do PagControl: gera uma base sintética de alunos e cobranças
(biblioteca Faker) num arquivo DuckDB local, totalmente separado do banco de
produção (Neon), e calcula métricas de risco de crédito — PDD (probabilidade
de default) e curva de vintage.

## Uso

```bash
uv run --package analytics python -m analytics.gerar_dados
uv run --package analytics python -m analytics.metricas
uv run --package analytics python -m analytics.grafico_vintage
```

- `gerar_dados.py` — gera ~6.000 alunos fictícios e suas cobranças mensais
  (~105 mil registros), salvos em `src/analytics/data/pagcontrol_analytics.duckdb`.
- `metricas.py` — calcula PDD geral, por perfil de risco e por modalidade, e a
  curva de vintage (acumulada por safra de matrícula).
- `grafico_vintage.py` — gera o gráfico da curva de vintage em
  `src/analytics/data/curva_vintage.png`.

A pasta `src/analytics/data/` (banco DuckDB e imagens gerados) não é versionada
— rode `gerar_dados.py` antes dos outros dois scripts.
