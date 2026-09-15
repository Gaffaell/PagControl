from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from .models import FormaPagamento, StatusCobranca

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
    # Campos de contato/endereço: editados só pela tela de Admin.
    email: str | None = None
    telefone: str | None = None
    cep: str | None = None
    endereco: str | None = None
    numero: str | None = None
    complemento: str | None = None


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
    email: str | None
    telefone: str | None
    cep: str | None
    endereco: str | None
    numero: str | None
    complemento: str | None
    criado_em: datetime


class ConfiguracaoReguaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    dias_lembrete_antes: int
    dias_aviso_vencimento: int
    dias_cobranca_atraso: str


class ConfiguracaoReguaUpdate(BaseModel):
    dias_lembrete_antes: int | None = None
    dias_aviso_vencimento: int | None = None
    # Lista de dias separada por vírgula, ex.: "3,7".
    dias_cobranca_atraso: str | None = None


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
