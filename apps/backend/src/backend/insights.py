"""Resumo analítico (estatístico) da carteira.

Transforma os totais por modalidade, competência e situação em alertas curtos:
modalidades em alta ou em queda, tendência da inadimplência e modalidades com
inadimplência acima da média. Só olha meses FECHADOS (anteriores ao mês
corrente): a competência em andamento ainda tem quase tudo pendente e
distorceria qualquer comparação.

O módulo não acessa o banco: recebe linhas já agrupadas, o que facilita testar.
"""

from collections import defaultdict
from datetime import date
from statistics import mean

JANELA_MESES = 6  # meses fechados usados para a tendência
MESES_BASE = 3  # meses anteriores ao último, usados como base de comparação
LIMIAR_VARIACAO = 0.05  # último mês ≥ 5% acima/abaixo da base
LIMIAR_TENDENCIA = 0.01  # inclinação ≥ 1% da média por mês
MIN_R2 = 0.25  # a reta explica ao menos 25% da variação da série
PARTICIPACAO_MINIMA = 0.03  # ignora modalidades com < 3% do faturamento
LIMIAR_INAD_PP = 0.015  # inadimplência geral: mudança de 1,5 ponto percentual
LIMIAR_MODALIDADE_PP = 0.03  # modalidade 3 p.p. acima da taxa geral
MIN_COBRANCAS_MODALIDADE = 20
META_RECEBIMENTO = 0.90
MAX_ITENS_POR_TIPO = 3
SITUACOES_EM_ATRASO = {"atrasado", "inadimplente"}

# Linha de entrada: (modalidade, competencia "AAAA-MM", situacao, valor, quantidade)
Linha = tuple[str | None, str, str, float, int]


def normalizar_modalidade(valor: str | None) -> str:
    if not valor or not valor.strip():
        return "Não informada"
    return valor.strip().title()


def _tendencia(serie: list[float]) -> tuple[float, float]:
    """Inclinação relativa por mês (inclinação ÷ média) e R² da reta de mínimos
    quadrados ajustada à série."""
    n = len(serie)
    media_y = mean(serie)
    if n < 2 or media_y == 0:
        return 0.0, 0.0
    media_x = (n - 1) / 2
    sxx = sum((x - media_x) ** 2 for x in range(n))
    sxy = sum((x - media_x) * (y - media_y) for x, y in enumerate(serie))
    syy = sum((y - media_y) ** 2 for y in serie)
    inclinacao = sxy / sxx
    r2 = (sxy**2) / (sxx * syy) if syy > 0 else 0.0
    return inclinacao / media_y, r2


def _taxa_em_atraso(por_situacao: dict[str, float]) -> float | None:
    total = sum(por_situacao.values())
    if total <= 0:
        return None
    return sum(v for s, v in por_situacao.items() if s in SITUACOES_EM_ATRASO) / total


def gerar_insights(linhas: list[Linha], hoje: date) -> dict:
    atual = f"{hoje:%Y-%m}"
    fechadas = sorted(
        {competencia for _, competencia, *_ in linhas if competencia < atual}
    )
    janela = fechadas[-JANELA_MESES:]
    resultado: dict = {
        "referencia": janela[-1] if janela else None,
        "meses_analisados": len(janela),
        "itens": [],
    }
    if len(janela) < MESES_BASE + 1:
        return resultado

    ultimo = janela[-1]
    base = janela[-1 - MESES_BASE : -1]
    ultimos_tres = janela[-3:]

    fat_modalidade: dict[str, dict[str, float]] = defaultdict(
        lambda: defaultdict(float)
    )
    por_competencia: dict[str, dict[str, float]] = defaultdict(
        lambda: defaultdict(float)
    )
    modalidade_situacao: dict[str, dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(lambda: [0.0, 0])
    )
    for modalidade, competencia, situacao, valor, quantidade in linhas:
        if competencia not in janela:
            continue
        nome = normalizar_modalidade(modalidade)
        fat_modalidade[nome][competencia] += valor
        por_competencia[competencia][situacao] += valor
        if competencia in ultimos_tres:
            acumulado = modalidade_situacao[nome][situacao]
            acumulado[0] += valor
            acumulado[1] += quantidade

    itens: list[dict] = []

    # 1) modalidades em alta / em queda
    total_ultimo = sum(fat[ultimo] for fat in fat_modalidade.values()) or 1.0
    candidatos = {"alta": [], "queda": []}
    for nome, fat in fat_modalidade.items():
        serie = [fat.get(c, 0.0) for c in janela]
        media_base = mean(fat.get(c, 0.0) for c in base)
        if media_base <= 0 or fat.get(ultimo, 0.0) / total_ultimo < PARTICIPACAO_MINIMA:
            continue
        variacao = fat.get(ultimo, 0.0) / media_base - 1
        inclinacao, r2 = _tendencia(serie)
        dados = {
            "mes": ultimo,
            "ultimo": fat.get(ultimo, 0.0),
            "base": media_base,
            "variacao": variacao,
            "tendencia": inclinacao,
            "r2": r2,
            "meses": len(janela),
        }
        if (
            variacao >= LIMIAR_VARIACAO
            and inclinacao >= LIMIAR_TENDENCIA
            and r2 >= MIN_R2
        ):
            candidatos["alta"].append((variacao, nome, dados))
        elif (
            variacao <= -LIMIAR_VARIACAO
            and inclinacao <= -LIMIAR_TENDENCIA
            and r2 >= MIN_R2
        ):
            candidatos["queda"].append((variacao, nome, dados))
    for tipo, codigo, ordem in (
        ("queda", "modalidade_queda", False),
        ("alta", "modalidade_alta", True),
    ):
        escolhidos = sorted(candidatos[tipo], key=lambda c: c[0], reverse=ordem)
        for _, nome, dados in escolhidos[:MAX_ITENS_POR_TIPO]:
            itens.append(
                {"codigo": codigo, "tipo": tipo, "assunto": nome, "dados": dados}
            )

    # 2) tendência da inadimplência geral
    taxas = {c: _taxa_em_atraso(por_competencia[c]) for c in janela}
    taxas_base = [taxas[c] for c in base if taxas[c] is not None]
    if taxas[ultimo] is not None and taxas_base:
        taxa_base = mean(taxas_base)
        mudanca = taxas[ultimo] - taxa_base
        dados = {
            "mes": ultimo,
            "taxa_ultimo": taxas[ultimo],
            "taxa_base": taxa_base,
            "mudanca": mudanca,
        }
        if mudanca >= LIMIAR_INAD_PP:
            itens.append(
                {
                    "codigo": "inadimplencia_subindo",
                    "tipo": "atencao",
                    "assunto": None,
                    "dados": dados,
                }
            )
        elif mudanca <= -LIMIAR_INAD_PP:
            itens.append(
                {
                    "codigo": "inadimplencia_caindo",
                    "tipo": "alta",
                    "assunto": None,
                    "dados": dados,
                }
            )

    # 3) recebimento do último mês fechado
    total_mes = sum(por_competencia[ultimo].values())
    if total_mes > 0:
        taxa_recebimento = por_competencia[ultimo].get("pago", 0.0) / total_mes
        itens.append(
            {
                "codigo": "recebimento",
                "tipo": "info" if taxa_recebimento >= META_RECEBIMENTO else "atencao",
                "assunto": None,
                "dados": {
                    "mes": ultimo,
                    "taxa": taxa_recebimento,
                    "meta": META_RECEBIMENTO,
                    "valor_pago": por_competencia[ultimo].get("pago", 0.0),
                },
            }
        )

    # 4) modalidades com inadimplência acima da média (últimos 3 meses fechados)
    geral = defaultdict(float)
    for situacoes in modalidade_situacao.values():
        for situacao, (valor, _) in situacoes.items():
            geral[situacao] += valor
    taxa_geral = _taxa_em_atraso(geral)
    if taxa_geral is not None:
        acima = []
        for nome, situacoes in modalidade_situacao.items():
            quantidade = sum(q for _, q in situacoes.values())
            taxa = _taxa_em_atraso({s: v for s, (v, _) in situacoes.items()})
            if taxa is None or quantidade < MIN_COBRANCAS_MODALIDADE:
                continue
            if taxa - taxa_geral >= LIMIAR_MODALIDADE_PP:
                acima.append(
                    (
                        taxa - taxa_geral,
                        nome,
                        {
                            "taxa": taxa,
                            "taxa_geral": taxa_geral,
                            "cobrancas": quantidade,
                        },
                    )
                )
        for _, nome, dados in sorted(acima, key=lambda c: c[0], reverse=True)[:2]:
            itens.append(
                {
                    "codigo": "modalidade_inadimplencia",
                    "tipo": "atencao",
                    "assunto": nome,
                    "dados": dados,
                }
            )

    prioridade = {"atencao": 0, "queda": 1, "alta": 2, "info": 3}
    resultado["itens"] = sorted(itens, key=lambda item: prioridade[item["tipo"]])
    return resultado
