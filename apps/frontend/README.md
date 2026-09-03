# Frontend — Sistema de Cobrança PagControl

Interface em Streamlit para gerenciamento de alunos, cobranças e métricas de inadimplência da academia.

## Como rodar

A partir da raiz do monorepo:

```bash
uv run --package frontend streamlit run apps/frontend/src/frontend/app.py
```

Ou a partir do diretório do frontend:

```bash
cd apps/frontend
uv run streamlit run src/frontend/app.py
```

O aplicativo estará disponível em `http://localhost:8501`.

## Estrutura

```
src/frontend/
  app.py                    → Painel principal / Dashboard PagControl
  pages/
    1_Alunos.py             → Gestão e cadastro de alunos
    2_Metricas.py           → Indicadores de inadimplência e receita
```
