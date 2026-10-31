from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from .models import DiaSemana, FormaPagamento, StatusCobranca, Turno

# Schemas Pydantic: validam o que entra/sai da API, separados dos modelos
# do banco (app/models.py) para não expor campos internos sem querer.


class AlunoCreate(BaseModel):
    nome: str
    valor_mensalidade: float
    dia_vencimento: int
    modalidade: str | None = None
    turno: Turno | None = None
    dia_semana: DiaSemana | None = None
    data_nascimento: date | None = None


class AlunoUpdate(BaseModel):
    nome: str | None = None
    valor_mensalidade: float | None = None
    dia_vencimento: int | None = None
    modalidade: str | None = None
    turno: Turno | None = None
    dia_semana: DiaSemana | None = None
    data_nascimento: date | None = None
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
    turno: Turno | None
    dia_semana: DiaSemana | None
    data_matricula: date
    data_nascimento: date | None
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
    porcentagem_juros_por_dia: str


class ConfiguracaoReguaUpdate(BaseModel):
    dias_lembrete_antes: int | None = None
    dias_aviso_vencimento: int | None = None
    # Lista de dias separada por vírgula, ex.: "3,7".
    dias_cobranca_atraso: str | None = None
    porcentagem_juros_por_dia: str | None = None


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


class MetricaStatus(BaseModel):
    status: StatusCobranca
    quantidade: int
    valor: float


class MetricaFaixaEtaria(BaseModel):
    faixa_etaria: str
    status: StatusCobranca
    quantidade: int
    valor: float


class MetricaModalidade(BaseModel):
    modalidade: str | None
    competencia: str
    quantidade: int
    valor: float


class MetricaTurnoDia(BaseModel):
    competencia: str
    turno: Turno | None
    dia_semana: DiaSemana | None
    valor: float


class MetricaCompetencia(BaseModel):
    competencia: str
    status: StatusCobranca
    quantidade: int
    valor: float


class ResumoMetricas(BaseModel):
    """Totais já agrupados no banco, para a página de Métricas não precisar
    baixar a tabela de cobranças inteira."""

    competencias: list[str]
    ordem_faixas_etarias: list[str]
    alunos_ativos: int
    receita_prevista: float
    por_status: list[MetricaStatus]
    por_competencia: list[MetricaCompetencia]
    por_faixa_etaria: list[MetricaFaixaEtaria]
    por_modalidade: list[MetricaModalidade]
    por_turno_dia: list[MetricaTurnoDia]


class LinhaArrecadacao(BaseModel):
    modalidade: str | None
    faixa_etaria: str
    turno: Turno | None
    dia_semana: DiaSemana | None
    valor_cobrado: float
    valor_recebido: float
    cobrancas: int
    alunos: int


class AnaliseArrecadacao(BaseModel):
    """Cobrado e recebido por perfil de aluno, para a página de Análise."""

    ordem_faixas_etarias: list[str]
    linhas: list[LinhaArrecadacao]


class CobrancaDetalhe(BaseModel):
    id: int
    aluno_id: int
    aluno_nome: str | None
    competencia: str
    valor: float
    data_vencimento: date
    status: StatusCobranca
    data_pagamento: date | None
    forma_pagamento: FormaPagamento | None


class DetalhamentoMetricas(BaseModel):
    total: int
    itens: list[CobrancaDetalhe]


class VintagePonto(BaseModel):
    mes_de_vida: int
    alunos: int
    inadimplentes: int
    percentual: float


class VintageSafraPonto(VintagePonto):
    safra: str


class CurvaVintage(BaseModel):
    """% acumulado de alunos inadimplentes por mês de vida da conta, por safra
    (mês de matrícula) e na média ponderada geral."""

    meses: int
    safras: list[VintageSafraPonto]
    media: list[VintagePonto]


class InsightItem(BaseModel):
    """Um alerta do resumo analítico. `codigo` identifica o tipo de mensagem e
    `dados` traz os números usados (o texto é montado na tela)."""

    codigo: str
    tipo: str  # alta | queda | atencao | info
    assunto: str | None
    dados: dict[str, float | str]


class InsightsMetricas(BaseModel):
    referencia: str | None
    meses_analisados: int
    itens: list[InsightItem]


class LoginRequisicao(BaseModel):
    nomde_de_usuario: str
    senha_hash: str
