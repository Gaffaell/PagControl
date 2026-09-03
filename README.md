# 💳 PagControl — Sistema de Cobrança e Gestão Recorrente

Monorepo estruturado com **uv workspaces** para gestão de cobrança recorrente de academias (cadastro de alunos, emissão de faturas mensais, régua de cobrança automática e métricas financeiras).

---

## 🏛️ Arquitetura do Workspace

O repositório é gerenciado via [uv](https://docs.astral.sh/uv/) em formato de workspace monorepo:

```
PagControl/
├── pyproject.toml                         # Orquestrador do Workspace uv (raiz virtual)
├── uv.lock                                # Lockfile único determinístico
├── apps/
│   ├── backend/                           # API FastAPI + SQLAlchemy (workspace: backend)
│   │   ├── pyproject.toml
│   │   └── src/backend/
│   │       ├── api.py                     # Rotas da API REST
│   │       ├── crud.py                    # Regras de negócio e faturamento
│   │       ├── database.py                # Conexão SQLAlchemy (SQLite / Neon Postgres)
│   │       ├── init_db.py                 # Criação e inicialização de tabelas
│   │       ├── models.py                  # Modelos ORM (Aluno, Cobranca, Regua)
│   │       ├── schemas.py                 # Schemas Pydantic
│   │       └── cli.py                     # CLI para resumo do banco
│   │
│   └── frontend/                          # Aplicação Streamlit (workspace: frontend)
│       ├── pyproject.toml
│       └── src/frontend/
│           ├── app.py                     # Dashboard principal
│           └── pages/
│               ├── 1_Alunos.py            # Gestão e cadastro de alunos
│               └── 2_Metricas.py          # Indicadores e inadimplência
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

Por padrão, a aplicação utiliza SQLite local (`academia.db`), gerado automaticamente sem configurações extras.

Para conectar a um banco PostgreSQL gerenciado (como [Neon](https://neon.tech)):
1. Copie `.env.example` para `.env`:
   ```bash
   cp .env.example .env
   ```
2. Defina a variável `DATABASE_URL` com sua connection string do Postgres.
