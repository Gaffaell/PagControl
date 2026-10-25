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
│   │           ├── 3_Analise.py           # Faturamento por curso e perfil de quem paga
│   │           └── 4_Admin.py             # Contato/endereço do aluno e configuração da régua de cobrança
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
uv run --package backend uvicorn backend.api:app --reload --reload-dir apps/backend/src
```

O `--reload-dir` restringe a vigilância ao código do backend. Sem ele, o reload também dispara por mudanças dentro da `.venv` — e cada recarga refaz a rotina de subida (`lifespan`), que consulta o banco.

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

A equipe compartilha um projeto [Neon](https://neon.tech) (PostgreSQL gerenciado) como banco de produção.

**Desenvolvimento do dia a dia: use o SQLite local.** Sem `DATABASE_URL` definida (ou com a linha comentada no `.env`), a aplicação usa automaticamente um SQLite local (`academia.db`, ignorado pelo Git). Desenvolver, testar e rodar com `--reload` assim não consome nada da Neon.

**Para conectar à Neon compartilhada** (demonstração / dados reais do time):
1. Copie `.env.example` para `.env`:
   ```bash
   cp .env.example .env
   ```
2. Descomente `DATABASE_URL` e preencha com a connection string do Postgres (peça ao responsável pelo projeto; ela contém a senha e nunca vai para o Git).

> Atenção: o `.env.local`, se existir, é lido antes do `.env` e tem prioridade sobre ele.

### Cópia de segurança do SQLite na Neon

Fluxo adotado: quem edita os dados (uma única máquina) trabalha no SQLite local e envia uma cópia para a Neon ao fim do dia. Os demais integrantes só consultam e testam.

1. No `.env`, comente a linha `DATABASE_URL` (a aplicação passa a usar o SQLite local) e mantenha `DATABASE_URL_UNPOOLED` — ou defina `NEON_DATABASE_URL` — com a connection string da Neon. Ela é usada só pelo script de envio.
2. Trabalhe normalmente. O `academia.db` fica na pasta de onde o backend é iniciado (a raiz do monorepo, nos comandos acima).
3. Ao fim do dia, envie a cópia:
   ```bash
   uv run --package backend python -m backend.sync_neon
   ```

Como funciona e regras:
- Faz *upsert* pelo `id` (insere ou atualiza) e **nunca apaga nada** na Neon; rodar de novo não duplica.
- Só a máquina dona dos dados roda o envio. A Neon é um espelho: **não crie nem edite dados direto nela**, pois o que for criado lá pode ser sobrescrito se o `id` coincidir.
- Para outro arquivo de origem: `--origem sqlite:///caminho/outro.db`.
- Agendamento diário no Windows (exemplo, ajuste o caminho):
  ```bash
  schtasks /Create /SC DAILY /ST 20:00 /TN "PagControl - envio para a Neon" /TR "cmd /c cd /d C:\caminho\do\PagControl && uv run --package backend python -m backend.sync_neon"
  ```

### Cota da Neon (plano gratuito)

O plano gratuito limita a **transferência de rede mensal por projeto**. Em 20/10/2026 a cota estourou e o banco ficou bloqueado para o time inteiro até a troca por um projeto novo. Para não repetir:

- **Não carregue volume de dados na Neon** (seeds de milhares de linhas, testes de carga). Dados de Big Data ficam no DuckDB local (`apps/analytics`) ou no SQLite.
- **Rode o backend com `--reload-dir apps/backend/src`** (ver acima), para que recargas desnecessárias não refaçam a subida contra o banco.
- **Confira o consumo de vez em quando** em *Review usage* no console da Neon.

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

