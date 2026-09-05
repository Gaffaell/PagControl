import requests

BASE_URL = "http://localhost:8000"


def listar_alunos(apenas_ativos=False):
    response = requests.get(
        f"{BASE_URL}/alunos",
        params={"apenas_ativos": apenas_ativos}
    )

    response.raise_for_status()

    return response.json()

def criar_aluno(dados):
    response = requests.post(
        f"{BASE_URL}/alunos",
        json=dados
    )

    response.raise_for_status()

    return response.json()