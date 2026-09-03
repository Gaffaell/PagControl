# Backend — Sistema de Cobrança PagControl

API em FastAPI + SQLAlchemy para o sistema de cobrança recorrente da academia
(cadastro de alunos, geração de faturas mensais, régua de atraso/inadimplência).

## Como rodar

A partir da raiz do monorepo:

```bash
# Executar a API com reload automático
uv run --package backend uvicorn backend.api:app --reload

# Ou executar o CLI de resumo do banco de dados
uv run --package backend backend
```

Ou entrando na pasta do workspace:

```bash
cd apps/backend
uv run uvicorn backend.api:app --reload
```

Sem configuração extra, usa um SQLite local (`academia.db`, ignorado pelo Git).
Para usar um banco Postgres na nuvem (ex.: [Neon](https://neon.tech)), configure `DATABASE_URL` no arquivo `.env` na raiz do projeto ou neste diretório.

Documentação interativa Swagger disponível em `http://127.0.0.1:8000/docs`.

## Estrutura

```
src/backend/
  models.py     → Aluno, Cobranca, ConfiguracaoRegua (SQLAlchemy)
  database.py   → engine/sessão (Postgres via DATABASE_URL, ou SQLite local)
  schemas.py    → validação de entrada/saída (Pydantic)
  crud.py       → regras de negócio (gerar fatura do mês, régua de atraso)
  api.py        → rotas FastAPI
  init_db.py    → cria tabelas e semeia configuração padrão
  cli.py        → resumo rápido do banco pelo terminal, sem subir a API
```

## Endpoints

| Método | Rota | Descrição |
|---|---|---|
| POST | `/alunos` | Cadastra um aluno |
| GET | `/alunos` | Lista alunos (`?apenas_ativos=true`) |
| GET/PATCH/DELETE | `/alunos/{id}` | Detalhe, edita, desativa (soft delete) |
| POST | `/alunos/{id}/cobrancas` | Gera a fatura do próximo mês (idempotente) |
| GET | `/cobrancas` | Lista cobranças (filtros `aluno_id`, `status`) |
| POST | `/cobrancas/{id}/pagar` | Registra pagamento (`pix` ou `cnab`) |
| POST | `/cobrancas/atualizar-status` | Aplica a régua: marca atraso/inadimplência |
