"""Cliente HTTP do frontend para a API PagControl."""

import os
from typing import Any

import httpx

BASE_URL = os.getenv("PAGCONTROL_API_URL", "http://localhost:8000").rstrip("/")
REQUEST_TIMEOUT = 10


class APIError(RuntimeError):
    """Erro de comunicação ou resposta inválida da API."""


def _request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json: dict[str, Any] | None = None,
) -> Any:
    try:
        response = httpx.request(
            method,
            f"{BASE_URL}{path}",
            params=params,
            json=json,
            timeout=REQUEST_TIMEOUT,
            trust_env=False,
        )
    except httpx.RequestError as exc:
        raise APIError(
            "Não foi possível conectar à API do PagControl. "
            f"Confirme se o backend está ativo em {BASE_URL}."
        ) from exc

    if not response.is_success:
        try:
            payload = response.json()
            detalhe = payload.get("detail", payload)
        except ValueError:
            detalhe = response.text or "Resposta sem detalhes"
        raise APIError(f"A API retornou o erro {response.status_code}: {detalhe}")

    if response.status_code == 204 or not response.content:
        return None

    try:
        return response.json()
    except ValueError as exc:
        raise APIError("A API retornou uma resposta em formato inválido.") from exc


def listar_alunos(apenas_ativos: bool = False) -> list[dict[str, Any]]:
    return _request("GET", "/alunos", params={"apenas_ativos": apenas_ativos})


def criar_aluno(dados: dict[str, Any]) -> dict[str, Any]:
    return _request("POST", "/alunos", json=dados)


def atualizar_aluno(aluno_id: int, dados: dict[str, Any]) -> dict[str, Any]:
    return _request("PATCH", f"/alunos/{aluno_id}", json=dados)


def desativar_aluno(aluno_id: int) -> None:
    _request("DELETE", f"/alunos/{aluno_id}")


def listar_cobrancas(
    aluno_id: int | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {}
    if aluno_id is not None:
        params["aluno_id"] = aluno_id
    if status is not None:
        params["status"] = status
    return _request("GET", "/cobrancas", params=params)


def gerar_cobranca(aluno_id: int) -> dict[str, Any]:
    return _request("POST", f"/alunos/{aluno_id}/cobrancas")


def registrar_pagamento(
    cobranca_id: int,
    forma_pagamento: str,
    data_pagamento: str | None = None,
) -> dict[str, Any]:
    dados: dict[str, Any] = {"forma_pagamento": forma_pagamento}
    if data_pagamento is not None:
        dados["data_pagamento"] = data_pagamento
    return _request("POST", f"/cobrancas/{cobranca_id}/pagar", json=dados)


def atualizar_status_cobrancas() -> int:
    resultado = _request("POST", "/cobrancas/atualizar-status")
    return int(resultado["cobrancas_atualizadas"])


def obter_configuracao_regua() -> dict[str, Any]:
    return _request("GET", "/configuracao-regua")


def atualizar_configuracao_regua(dados: dict[str, Any]) -> dict[str, Any]:
    return _request("PATCH", "/configuracao-regua", json=dados)
