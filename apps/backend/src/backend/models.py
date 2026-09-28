import enum
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

# Modelo de dados do sistema de cobrança (Aluno, Cobrança, Configuração da
# régua) — ver proposta em Downloads/proposta-cobranca-academia-bairro.docx,
# seção 2.1, para o desenho conceitual completo.


class StatusCobranca(enum.StrEnum):
    """Ciclo de vida de uma cobrança, avançado pela régua (crud.atualizar_status_atrasos)."""

    PENDENTE = "pendente"
    PAGO = "pago"
    ATRASADO = "atrasado"
    INADIMPLENTE = "inadimplente"


class FormaPagamento(enum.StrEnum):
    """Os dois caminhos de integração financeira previstos na proposta (seção 6)."""

    PIX = "pix"
    CNAB = "cnab"


class Turno(enum.StrEnum):
    """Horário de frequência do aluno, para cruzar matrículas/faturamento por turno."""

    MANHA = "manha"  # 06:00-12:00
    TARDE = "tarde"  # 12:00-18:00
    NOITE = "noite"  # 18:00-00:00


class DiaSemana(enum.StrEnum):
    """Dia da semana em que o aluno tem aula — usado para evitar conflito de
    agenda entre modalidades que disputam o mesmo horário/professor (ver
    crud.GRUPOS_EXCLUSIVOS_MODALIDADE)."""

    SEGUNDA = "segunda"
    TERCA = "terca"
    QUARTA = "quarta"
    QUINTA = "quinta"
    SEXTA = "sexta"
    SABADO = "sabado"
    DOMINGO = "domingo"


class Aluno(Base):
    """O devedor: mensalidade fixa e uma única data de vencimento (sem planos escalonados)."""

    __tablename__ = "alunos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    valor_mensalidade: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    dia_vencimento: Mapped[int] = mapped_column(nullable=False)
    # Opcional: não faz parte do cadastro mínimo da proposta, mas alimenta o
    # módulo de Big Data (segmentação de risco por modalidade).
    modalidade: Mapped[str | None] = mapped_column(String(60), nullable=True)
    # Horário em que o aluno frequenta o estabelecimento — permite cruzar
    # matrículas e faturamento por turno (manhã/tarde/noite).
    turno: Mapped[Turno | None] = mapped_column(Enum(Turno), nullable=True)
    # Dia da semana da aula do aluno. Validado em crud.criar_aluno/atualizar_aluno
    # contra GRUPOS_EXCLUSIVOS_MODALIDADE para não permitir que duas modalidades
    # que disputam o mesmo horário (ex.: Boxe e Jiu-jitsu) caiam no mesmo dia.
    dia_semana: Mapped[DiaSemana | None] = mapped_column(Enum(DiaSemana), nullable=True)
    # Usada depois pela curva de vintage (risco de inadimplência por turma de matrícula).
    data_matricula: Mapped[date] = mapped_column(
        Date, nullable=False, default=date.today
    )
    # Usada para calcular a faixa etária do aluno e cruzar com inadimplência
    # (ver página de Métricas).
    data_nascimento: Mapped[date | None] = mapped_column(Date, nullable=True)
    ativo: Mapped[bool] = mapped_column(default=True)
    # Dados de contato/endereço: opcionais, fora do cadastro mínimo da
    # proposta. Coletados apenas pela tela de Admin, não pelo cadastro
    # rápido de aluno.
    email: Mapped[str | None] = mapped_column(String(150), nullable=True)
    telefone: Mapped[str | None] = mapped_column(String(80), nullable=True)
    cep: Mapped[str | None] = mapped_column(String(50), nullable=True)
    endereco: Mapped[str | None] = mapped_column(String(90), nullable=True)
    numero: Mapped[str | None] = mapped_column(String(20), nullable=True)
    complemento: Mapped[str | None] = mapped_column(String(80), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    cobrancas: Mapped[list["Cobranca"]] = relationship(back_populates="aluno")


class Cobranca(Base):
    """Uma fatura mensal gerada para um aluno (uma por competência/mês)."""

    __tablename__ = "cobrancas"

    id: Mapped[int] = mapped_column(primary_key=True)
    aluno_id: Mapped[int] = mapped_column(ForeignKey("alunos.id"), nullable=False)
    competencia: Mapped[str] = mapped_column(String(7), nullable=False)  # "YYYY-MM"
    valor: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    data_vencimento: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[StatusCobranca] = mapped_column(
        Enum(StatusCobranca), default=StatusCobranca.PENDENTE
    )
    data_pagamento: Mapped[date | None] = mapped_column(Date, nullable=True)
    forma_pagamento: Mapped[FormaPagamento | None] = mapped_column(
        Enum(FormaPagamento), nullable=True
    )
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    aluno: Mapped["Aluno"] = relationship(back_populates="cobrancas")


class ConfiguracaoRegua(Base):
    """Parâmetros da régua de cobrança. Modelo single-tenant: uma única linha
    vale para a academia inteira (não há múltiplos credores nesta versão)."""

    __tablename__ = "configuracao_regua"

    id: Mapped[int] = mapped_column(primary_key=True)
    dias_lembrete_antes: Mapped[int] = mapped_column(default=3)
    dias_aviso_vencimento: Mapped[int] = mapped_column(default=0)
    # Guardado como string "3,7" em vez de tabela separada — simples o
    # suficiente para o único caso de uso (poucos intervalos, sem edição
    # frequente), evita uma tabela extra só para isso.
    dias_cobranca_atraso: Mapped[str] = mapped_column(String(50), default="3,7")

    def lista_dias_cobranca_atraso(self) -> list[int]:
        return [int(d) for d in self.dias_cobranca_atraso.split(",") if d]
