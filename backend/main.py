from app import models
from app.database import SessionLocal
from app.init_db import init_db

# Ponto de entrada rápido para checar o estado do banco sem subir a API
# (ex.: rodar `python main.py` só pra ver quantos alunos/cobranças existem).


def resumo() -> None:
    db = SessionLocal()
    try:
        total_alunos = db.query(models.Aluno).count()
        total_cobrancas = db.query(models.Cobranca).count()
        regua = db.query(models.ConfiguracaoRegua).first()

        print("=== Sistema de Cobrança - PagControl ===")
        print(f"Alunos cadastrados: {total_alunos}")
        print(f"Cobranças geradas: {total_cobrancas}")
        if regua:
            print(
                f"Régua de cobrança: lembrete {regua.dias_lembrete_antes}d antes, "
                f"atraso em {regua.dias_cobranca_atraso}d"
            )
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
    resumo()
