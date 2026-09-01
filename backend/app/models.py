import enum
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# Modelo de dados do sistema de cobrança (Aluno, Cobrança, Configuração da
# régua) — ver proposta em Downloads/proposta-cobranca-academia-bairro.docx,
# seção 2.1, para o desenho conceitual completo.


class StatusCobranca(str, enum.Enum):
    """Ciclo de vida de uma cobrança, avançado pela régua (crud.atualizar_status_atrasos)."""

    PENDENTE = "pendente"
    PAGO = "pago"
    ATRASADO = "atrasado"
    INADIMPLENTE = "inadimplente"


class FormaPagamento(str, enum.Enum):
    """Os dois caminhos de integração financeira previstos na proposta (seção 6)."""

    PIX = "pix"
    CNAB = "cnab"


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
    # Usada depois pela curva de vintage (risco de inadimplência por turma de matrícula).
    data_matricula: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    ativo: Mapped[bool] = mapped_column(default=True)
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
