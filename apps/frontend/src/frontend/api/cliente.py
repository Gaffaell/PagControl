import requests

BASE_URL = "http://localhost:8000"


def listar_alunos(apenas_ativos=False):
    response = requests.get(
        f"{BASE_URL}/alunos",
        params={"apenas_ativos": apenas_ativos}
    )

    response.raise_for_status()

    return response.json()