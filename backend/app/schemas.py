from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models import FormaPagamento, StatusCobranca

# Schemas Pydantic: validam o que entra/sai da API, separados dos modelos
# do banco (app/models.py) para não expor campos internos sem querer.


class AlunoCreate(BaseModel):
    nome: str
    valor_mensalidade: float
    dia_vencimento: int
    modalidade: str | None = None


class AlunoUpdate(BaseModel):
    nome: str | None = None
    valor_mensalidade: float | None = None
    dia_vencimento: int | None = None
    modalidade: str | None = None
    ativo: bool | None = None


class AlunoOut(BaseModel):
    # from_attributes permite montar o schema direto de um objeto ORM
    # (models.Aluno), sem precisar converter para dict manualmente.
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    valor_mensalidade: float
    dia_vencimento: int
    modalidade: str | None
    data_matricula: date
    ativo: bool
    criado_em: datetime


class CobrancaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    aluno_id: int
    competencia: str
    valor: float
    data_vencimento: date
    status: StatusCobranca
    data_pagamento: date | None
    forma_pagamento: FormaPagamento | None
    criado_em: datetime


class PagamentoRequest(BaseModel):
    forma_pagamento: FormaPagamento
    # Se omitida, o backend usa a data de hoje (ver crud.registrar_pagamento).
    data_pagamento: date | None = None
