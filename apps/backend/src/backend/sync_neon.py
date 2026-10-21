"""Envia o banco local (SQLite) para a Neon, como cópia de segurança.

Uso, a partir da raiz do monorepo:

    uv run --package backend python -m backend.sync_neon

Origem: SQLite local (academia.db, ou --origem). Destino: Postgres da Neon, lido
de NEON_DATABASE_URL ou, na falta dela, de DATABASE_URL_UNPOOLED (arquivo .env).

É um espelho de ida só: faz upsert pelo id (insere ou atualiza) e nunca apaga
nada na Neon. Pensado para uma única máquina que escreve os dados; o que for
criado direto na Neon pode ser sobrescrito se o id coincidir.
"""

import argparse
import os
import sys
from pathlib import Path

from sqlalchemy import Connection, create_engine, select, text
from sqlalchemy.dialects import postgresql, sqlite

from . import models

# Importar database carrega o .env (python-dotenv) antes de ler as variáveis.
from .database import Base

# Ordem respeita a chave estrangeira: alunos antes de cobranças.
TABELAS = [
    models.Aluno.__table__,
    models.Cobranca.__table__,
    models.ConfiguracaoRegua.__table__,
]
TAMANHO_LOTE = 1000

_INSERT_POR_DIALETO = {"postgresql": postgresql.insert, "sqlite": sqlite.insert}


def sincronizar(origem: Connection, destino: Connection) -> dict[str, int]:
    """Copia todas as linhas de origem para destino (upsert pelo id).

    Idempotente e sem exclusões: rodar de novo não duplica nem apaga nada.
    """
    insert = _INSERT_POR_DIALETO[destino.dialect.name]
    Base.metadata.create_all(destino)

    enviados: dict[str, int] = {}
    for tabela in TABELAS:
        linhas = [dict(linha._mapping) for linha in origem.execute(select(tabela))]
        atualizaveis = [c.name for c in tabela.columns if not c.primary_key]
        for inicio in range(0, len(linhas), TAMANHO_LOTE):
            comando = insert(tabela)
            comando = comando.on_conflict_do_update(
                index_elements=[tabela.c.id],
                set_={nome: comando.excluded[nome] for nome in atualizaveis},
            )
            destino.execute(comando, linhas[inicio : inicio + TAMANHO_LOTE])
        enviados[tabela.name] = len(linhas)
    return enviados


def ajustar_sequencias(destino: Connection) -> None:
    """Alinha os contadores de id do Postgres ao maior id copiado, para que
    inserções feitas direto na Neon não colidam com os ids enviados."""
    for tabela in TABELAS:
        destino.execute(
            text(
                f"SELECT setval(pg_get_serial_sequence('{tabela.name}', 'id'), "
                f"(SELECT COALESCE(MAX(id), 1) FROM {tabela.name}))"
            )
        )


def _normalizar_url_postgres(url: str) -> str:
    # Mesma normalização do database.py: força o driver psycopg (v3).
    for prefixo in ("postgres://", "postgresql://"):
        if url.startswith(prefixo):
            return url.replace(prefixo, "postgresql+psycopg://", 1)
    return url


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Copia o SQLite local para a Neon (upsert, sem apagar nada)."
    )
    parser.add_argument(
        "--origem",
        default="sqlite:///./academia.db",
        help="URL do banco de origem, SQLite (padrão: sqlite:///./academia.db)",
    )
    args = parser.parse_args(argv)

    destino_url = os.getenv("NEON_DATABASE_URL") or os.getenv("DATABASE_URL_UNPOOLED")
    if not destino_url:
        print(
            "Defina NEON_DATABASE_URL (ou DATABASE_URL_UNPOOLED) no .env com a "
            "connection string da Neon."
        )
        return 1

    origem_engine = create_engine(args.origem)
    destino_engine = create_engine(
        _normalizar_url_postgres(destino_url), pool_pre_ping=True
    )

    # Trava contra mandar os dados na direção errada.
    if origem_engine.dialect.name != "sqlite":
        print("A origem precisa ser um banco SQLite local.")
        return 1
    if destino_engine.dialect.name != "postgresql":
        print("O destino precisa ser o Postgres da Neon.")
        return 1
    arquivo = origem_engine.url.database
    if not arquivo or not Path(arquivo).exists():
        print(f"Banco de origem não encontrado: {arquivo}")
        return 1

    with origem_engine.connect() as origem, destino_engine.begin() as destino:
        enviados = sincronizar(origem, destino)
        ajustar_sequencias(destino)

    for tabela, quantidade in enviados.items():
        print(f"{tabela}: {quantidade} linha(s) enviada(s)")
    print("Sincronização concluída.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
