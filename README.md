# 💳 PagControl — Sistema de Cobrança e Gestão Recorrente

Monorepo estruturado com **uv workspaces** para gestão de cobrança recorrente de academias: cadastro de alunos, dados de contato/endereço e régua de cobrança (módulo de Admin), emissão de faturas mensais, régua de cobrança automática, métricas financeiras e um módulo analítico de Big Data (dados sintéticos, PDD e curva de vintage).

---

## 🏛️ Arquitetura do Workspace

O repositório é gerenciado via [uv](https://docs.astral.sh/uv/) em formato de workspace monorepo:

```
PagControl/
├── pyproject.toml                         # Orquestrador do Workspace uv (raiz virtual)
├── uv.lock                                # Lockfile único determinístico
├── .streamlit/config.toml                 # Fixa o tema visual (claro), independente do sistema de quem acessa
├── apps/
│   ├── backend/                           # API FastAPI + SQLAlchemy (workspace: backend)
│   │   ├── pyproject.toml
│   │   └── src/backend/
│   │       ├── api.py                     # Rotas da API REST
│   │       ├── crud.py                    # Regras de negócio e faturamento
│   │       ├── database.py                # Conexão SQLAlchemy (SQLite / Neon Postgres)
│   │       ├── init_db.py                 # Criação e inicialização de tabelas
│   │       ├── models.py                  # Modelos ORM (Aluno, Cobranca, ConfiguracaoRegua)
│   │       ├── schemas.py                 # Schemas Pydantic
│   │       └── cli.py                     # CLI para resumo do banco
│   │
│   ├── frontend/                          # Aplicação Streamlit (workspace: frontend)
│   │   ├── pyproject.toml
│   │   └── src/frontend/
│   │       ├── app.py                     # Dashboard principal
│   │       ├── ui.py                      # Tema visual e componentes compartilhados entre as páginas
│   │       └── pages/
│   │           ├── 1_Alunos.py            # Gestão e cadastro de alunos
│   │           ├── 2_Metricas.py          # Indicadores e inadimplência
│   │           └── 3_Admin.py             # Contato/endereço do aluno e configuração da régua de cobrança
│   │
│   └── analytics/                         # Módulo de Big Data (workspace: analytics)
│       ├── pyproject.toml
│       ├── README.md                      # Detalhes de uso do módulo
│       └── src/analytics/
│           ├── gerar_dados.py             # Gera base sintética de alunos e cobranças (Faker + DuckDB)
│           ├── metricas.py                # Calcula PDD e curva de vintage
│           └── grafico_vintage.py         # Gera o gráfico da curva de vintage
```

---

## 🚀 Como Começar

### Pré-requisitos
- [uv](https://docs.astral.sh/uv/) instalado (`curl -LsSf https://astral.sh/uv/install.sh | sh` ou via mise/brew/pipx)
- Python >= 3.11

### 1. Instalar dependências de todos os workspaces

```bash
uv sync --all-packages
```

Isso cria um ambiente virtual único (`.venv`) na raiz com todos os pacotes instalados em modo editável.

---

## 💻 Executando os Serviços

### Backend (FastAPI)

Para iniciar o servidor FastAPI com reload automático:

```bash
uv run --package backend uvicorn backend.api:app --reload
```

- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

Para consultar um resumo rápido do banco no terminal:

```bash
uv run --package backend backend
```

### Frontend (Streamlit)

Para iniciar a interface web:

```bash
uv run --package frontend streamlit run apps/frontend/src/frontend/app.py
```

- **Aplicação Web**: [http://localhost:8501](http://localhost:8501)

---

## 🗄️ Banco de Dados

A equipe compartilha um projeto [Neon](https://neon.tech) (PostgreSQL gerenciado) como banco de produção. Para conectar a ele:
1. Copie `.env.example` para `.env`:
   ```bash
   cp .env.example .env
   ```
2. Defina a variável `DATABASE_URL` com a connection string do Postgres.

Sem essa variável configurada, a aplicação recorre automaticamente a um SQLite local (`academia.db`) — útil só para testes pontuais isolados, já que não reflete os dados reais compartilhados pela equipe.

---

## 📊 Módulo de Big Data (analytics)

Gera uma base sintética de alunos e cobranças (biblioteca [Faker](https://faker.readthedocs.io/)), totalmente separada do banco Neon de produção, num arquivo [DuckDB](https://duckdb.org/) local. A partir dela, calcula a PDD (probabilidade de inadimplência) e a curva de vintage. Ver [`apps/analytics/README.md`](apps/analytics/README.md) para detalhes.

```bash
uv run --package analytics python -m analytics.gerar_dados
uv run --package analytics python -m analytics.metricas
uv run --package analytics python -m analytics.grafico_vintage
```

---

## 🧹 Qualidade de Código (Lint & Format)

O repositório utiliza o [Ruff](https://docs.astral.sh/ruff/) para garantir formatação consistente e conformidade de código, verificado automaticamente via GitHub Actions a cada push e pull request para `main` (`.github/workflows/lint.yml`).

Para rodar localmente antes de enviar uma alteração:

```bash
# Executar verificação de lint
uv run ruff check .

# Aplicar correções automáticas de lint
uv run ruff check --fix .

# Formatar todos os arquivos
uv run ruff format .

# Verificar conformidade de formatação (sem modificar arquivos)
uv run ruff format --check .
```

