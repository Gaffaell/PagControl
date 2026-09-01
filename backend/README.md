# Backend — Sistema de Cobrança PagControl

API em FastAPI + SQLAlchemy para o sistema de cobrança recorrente da academia
(cadastro de alunos, geração de faturas mensais, régua de atraso/inadimplência).

## Como rodar

```bash
cd backend
pip install -r requirements.txt
```

Sem configuração extra, usa um SQLite local (`academia.db`, ignorado pelo Git).
Para usar um banco Postgres na nuvem (recomendado — o Render, onde a API será
hospedada, apaga arquivos locais a cada redeploy), copie `.env.example` para
`.env` e preencha `DATABASE_URL` com uma connection string de Postgres (ex.:
[Neon](https://neon.tech), tier gratuito).

```bash
uvicorn app.api:app --reload
```

Documentação interativa em `http://127.0.0.1:8000/docs`.

## Estrutura

```
app/
  models.py     → Aluno, Cobranca, ConfiguracaoRegua (SQLAlchemy)
  database.py   → engine/sessão (Postgres via DATABASE_URL, ou SQLite local)
  schemas.py    → validação de entrada/saída (Pydantic)
  crud.py       → regras de negócio (gerar fatura do mês, régua de atraso)
  api.py        → rotas FastAPI
  init_db.py    → cria tabelas e semeia configuração padrão
main.py         → resumo rápido do banco pelo terminal, sem subir a API
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

## Nota para quem for ligar o frontend

A página `pages/clients.py` usa o termo **"cliente"** com plano
Básico/Premium; este backend usa **"aluno"** com mensalidade fixa única
(sem planos), conforme a proposta acadêmica. Vale alinhar esses dois modelos
antes de conectar o frontend a esta API — provavelmente ajustando o
formulário de clientes para bater com os campos de `Aluno` (nome, valor da
mensalidade, dia de vencimento).
