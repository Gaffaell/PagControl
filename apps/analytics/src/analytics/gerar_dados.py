"""Gera uma base sintética de alunos e cobranças para o módulo de Big Data.

Roda 100% local, num arquivo DuckDB separado (analytics/data/pagcontrol_analytics.duckdb).
Não tem nenhuma relação com o banco Neon de produção - é dado fictício, gerado
com a biblioteca Faker, só para viabilizar as análises (PDD e curva de vintage)
sem depender da base real (que hoje tem só 2 alunos cadastrados).

Uso: uv run python src/analytics/gerar_dados.py
"""

import random
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import duckdb
from faker import Faker

# Caminho do arquivo DuckDB de saída. Fica dentro da própria pasta "data" ao
# lado deste script (Path(__file__).parent), então não importa de onde o
# comando "uv run" é executado - o caminho sempre aponta pro lugar certo.
DB_PATH = Path(__file__).parent / "data" / "pagcontrol_analytics.duckdb"

# ---------------------------------------------------------------------------
# "Painel de controle" do gerador: mude esses números pra simular cenários
# diferentes (base maior, janela de tempo maior, etc.) sem mexer no resto do
# código.
# ---------------------------------------------------------------------------
NUM_ALUNOS = 6000
MESES_HISTORICO = 36  # janela de matrícula: últimos 36 meses até HOJE
HOJE = date(
    2026, 9, 15
)  # "hoje" fixo da simulação, para os resultados serem reprodutíveis

MODALIDADES = ["musculação", "natação", "crossfit", "funcional", "pilates", "luta"]

# Tabela de perfis de risco: pra cada perfil, o "peso" é a chance de um aluno
# fictício nascer com esse perfil (as três chances somam 1.0 = 100%), e as
# outras três chaves são a chance de CADA FATURA daquele aluno terminar como
# paga em dia, paga atrasada ou inadimplente (essas três também somam 1.0).
# É esse dicionário que faz "bom pagador" se comportar diferente de
# "inadimplente contumaz" quando o código sorteia o resultado de uma fatura.
PERFIS_RISCO = {
    "bom_pagador": {
        "peso": 0.60,
        "pago_em_dia": 0.90,
        "pago_atrasado": 0.08,
        "inadimplente": 0.02,
    },
    "regular": {
        "peso": 0.30,
        "pago_em_dia": 0.65,
        "pago_atrasado": 0.25,
        "inadimplente": 0.10,
    },
    "inadimplente_contumaz": {
        "peso": 0.10,
        "pago_em_dia": 0.30,
        "pago_atrasado": 0.30,
        "inadimplente": 0.40,
    },
}

# Instância do Faker configurada pra português do Brasil (pt_BR), pra gerar
# nomes que parecem nomes brasileiros de verdade em vez de nomes em inglês.
fake = Faker("pt_BR")


# "Ficha" de um aluno fictício. @dataclass é um atalho do Python: cria
# automaticamente o método que monta o objeto (Aluno(id=1, nome="...", ...))
# só a partir da lista de campos abaixo, sem precisar escrever isso na mão.
@dataclass
class Aluno:
    id: int
    nome: str
    modalidade: str
    perfil_risco: str
    valor_mensalidade: float
    dia_vencimento: int
    data_matricula: date


def sortear_perfil() -> str:
    """Sorteia um dos três perfis de risco, respeitando os pesos 60/30/10%."""
    perfis = list(PERFIS_RISCO.keys())
    pesos = [PERFIS_RISCO[p]["peso"] for p in perfis]
    # random.choices faz um sorteio "ponderado": com pesos [0.60, 0.30, 0.10],
    # o primeiro item sai ~60% das vezes, o segundo ~30%, e assim por diante -
    # é a mesma ideia de uma roleta com fatias de tamanhos diferentes.
    # k=1 pede só um resultado; random.choices sempre devolve uma lista,
    # por isso o [0] no final pra pegar o único item dela.
    return random.choices(perfis, weights=pesos, k=1)[0]


def gerar_alunos(quantidade: int) -> list[Aluno]:
    """Cria a lista de alunos fictícios, cada um com seus dados sorteados."""
    alunos = []
    for aluno_id in range(1, quantidade + 1):
        # Sorteia quantos dias atrás o aluno se matriculou, dentro da janela
        # de MESES_HISTORICO meses (aproximando cada mês a 30 dias). Isso
        # espalha as matrículas ao longo do tempo, criando várias "safras"
        # diferentes para a curva de vintage comparar depois.
        dias_atras = random.randint(0, MESES_HISTORICO * 30)
        data_matricula = HOJE - timedelta(days=dias_atras)
        alunos.append(
            Aluno(
                id=aluno_id,
                nome=fake.name(),  # nome fictício vindo do Faker
                modalidade=random.choice(MODALIDADES),
                perfil_risco=sortear_perfil(),
                # Mensalidade sorteada entre valores "redondos" comuns numa
                # academia. O "* 1.0" força o resultado a ser float mesmo
                # quando random.choice pega um número que parece inteiro.
                valor_mensalidade=round(
                    random.choice([80, 100, 120, 150, 180, 200]) * 1.0, 2
                ),
                dia_vencimento=random.randint(
                    1, 28
                ),  # 28 evita problema com meses de 28/29/30/31 dias
                data_matricula=data_matricula,
            )
        )
    return alunos


def somar_meses(d: date, meses: int) -> date:
    """Soma uma quantidade de meses a uma data, sem depender de bibliotecas externas.

    O Python não tem uma forma nativa de somar "meses" a uma data (só dias,
    com timedelta), porque meses têm tamanhos diferentes. Esta função faz a
    matemática na mão: transforma ano+mês num único número de meses corridos,
    soma, e depois separa de volta em ano e mês.
    """
    mes_total = d.month - 1 + meses
    ano = d.year + mes_total // 12
    mes = mes_total % 12 + 1
    # min(d.day, 28) evita erro em meses menores (ex.: fevereiro não tem dia 30)
    return date(ano, mes, min(d.day, 28))


def sortear_status(perfil: str) -> str:
    """Sorteia o desfecho de UMA fatura, usando as probabilidades do perfil do aluno."""
    probs = PERFIS_RISCO[perfil]
    # Mesmo mecanismo de sorteio ponderado do sortear_perfil(), mas agora
    # decidindo o resultado de uma fatura específica em vez do perfil do aluno.
    return random.choices(
        ["pago_em_dia", "pago_atrasado", "inadimplente"],
        weights=[probs["pago_em_dia"], probs["pago_atrasado"], probs["inadimplente"]],
        k=1,
    )[0]


def gerar_cobrancas(alunos: list[Aluno]) -> list[dict]:
    """Gera uma fatura por mês para cada aluno, do mês da matrícula até HOJE."""
    cobrancas = []
    cobranca_id = 1
    for aluno in alunos:
        # mes_relativo conta há quantos meses aquela conta existe (0 = mês da
        # matrícula, 1 = um mês depois, etc.) - é o número que vira o eixo X
        # da curva de vintage.
        mes_relativo = 0

        # Primeiro vencimento: mesmo mês/ano da matrícula, no dia de
        # vencimento do aluno. Se esse dia já passou dentro do mês da
        # matrícula (ex.: matriculou dia 20, vencimento é dia 5), a primeira
        # fatura só nasce no mês seguinte.
        vencimento = date(
            aluno.data_matricula.year, aluno.data_matricula.month, aluno.dia_vencimento
        )
        if vencimento < aluno.data_matricula:
            vencimento = somar_meses(vencimento, 1)
            mes_relativo = 1

        # Um laço que gera uma fatura por mês, avançando o vencimento a cada
        # volta, até ultrapassar a data "de hoje" da simulação.
        while vencimento <= HOJE:
            status_sorteado = sortear_status(aluno.perfil_risco)

            # Traduz o resultado do sorteio ("pago_em_dia"/"pago_atrasado"/
            # "inadimplente") pros campos que a fatura realmente guarda:
            # o status final e quantos dias de atraso teve o pagamento.
            if status_sorteado == "pago_em_dia":
                status_final = "pago"
                dias_atraso = 0
            elif status_sorteado == "pago_atrasado":
                status_final = "pago"
                dias_atraso = random.randint(1, 25)
            else:
                status_final = "inadimplente"
                dias_atraso = None  # nunca foi pago, então não existe "dias de atraso até o pagamento"

            # Só existe data de pagamento se a fatura foi paga (em dia ou atrasada).
            data_pagamento = (
                vencimento + timedelta(days=dias_atraso)
                if status_final == "pago"
                else None
            )

            cobrancas.append(
                {
                    "id": cobranca_id,
                    "aluno_id": aluno.id,
                    "competencia": vencimento.strftime(
                        "%Y-%m"
                    ),  # "2026-09", por exemplo
                    "mes_relativo": mes_relativo,
                    "valor": aluno.valor_mensalidade,
                    "data_vencimento": vencimento,
                    "status": status_final,
                    "dias_atraso": dias_atraso,
                    "data_pagamento": data_pagamento,
                }
            )

            # Prepara a próxima volta do laço: próximo id, próximo mês de
            # vida da conta, e o vencimento empurrado um mês pra frente.
            cobranca_id += 1
            mes_relativo += 1
            vencimento = somar_meses(vencimento, 1)

    return cobrancas


def salvar_no_duckdb(alunos: list[Aluno], cobrancas: list[dict]) -> None:
    """Grava alunos e cobrancas no arquivo DuckDB, substituindo o que existir.

    Importante: a gravação é feita em BLOCO (via DataFrame + "CREATE TABLE AS
    SELECT"), não linha por linha. A primeira versão deste script inseria
    fatura por fatura com executemany, e cada inserção virava uma escrita de
    disco separada - isso fez o processo, pra ~105 mil faturas, ficar rodando
    por vários minutos sem terminar. Montando tudo num DataFrame primeiro e
    inserindo de uma vez só, o tempo caiu para ~22 segundos.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Apaga o banco (e o arquivo de log de transações .wal, se sobrou de uma
    # execução anterior) antes de recriar do zero - garante que rodar o
    # script de novo sempre produz um resultado limpo, sem misturar com dados
    # de uma rodada anterior.
    if DB_PATH.exists():
        DB_PATH.unlink()
    wal_path = DB_PATH.with_suffix(DB_PATH.suffix + ".wal")
    if wal_path.exists():
        wal_path.unlink()

    con = duckdb.connect(str(DB_PATH))

    # con.register deixa o DuckDB "enxergar" um DataFrame do pandas como se
    # fosse uma tabela (aqui chamada "alunos_df"), sem duplicar os dados na
    # memória. CREATE TABLE ... AS SELECT * FROM copia isso pra uma tabela de
    # verdade dentro do arquivo .duckdb, em uma única operação em lote.
    alunos_df = duckdb_frame_alunos(alunos)
    con.register("alunos_df", alunos_df)
    con.execute("CREATE TABLE alunos_sinteticos AS SELECT * FROM alunos_df")

    cobrancas_df = duckdb_frame_cobrancas(cobrancas)
    con.register("cobrancas_df", cobrancas_df)
    con.execute("CREATE TABLE cobrancas_sinteticas AS SELECT * FROM cobrancas_df")

    con.close()


def duckdb_frame_alunos(alunos: list[Aluno]):
    """Converte a lista de objetos Aluno num DataFrame do pandas (formato de tabela)."""
    import pandas as pd

    return pd.DataFrame(
        [
            {
                "id": a.id,
                "nome": a.nome,
                "modalidade": a.modalidade,
                "perfil_risco": a.perfil_risco,
                "valor_mensalidade": a.valor_mensalidade,
                "dia_vencimento": a.dia_vencimento,
                "data_matricula": a.data_matricula,
            }
            for a in alunos
        ]
    )


def duckdb_frame_cobrancas(cobrancas: list[dict]):
    """Converte a lista de cobranças (já são dicionários) direto num DataFrame."""
    import pandas as pd

    return pd.DataFrame(cobrancas)


if __name__ == "__main__":
    # random.seed fixa o "estado inicial" do gerador de números aleatórios do
    # Python. Sem isso, cada execução sortearia valores diferentes; com a
    # seed fixa, rodar o script de novo sempre produz exatamente os mesmos
    # 6.000 alunos e as mesmas faturas - importante pra poder comparar
    # resultados entre execuções e pra documentar números específicos (como
    # os 105.418 registros citados nos PDFs).
    random.seed(42)

    print(
        f"Gerando {NUM_ALUNOS} alunos sintéticos (matrícula nos últimos {MESES_HISTORICO} meses)..."
    )
    alunos = gerar_alunos(NUM_ALUNOS)

    print("Gerando cobranças mensais para cada aluno...")
    cobrancas = gerar_cobrancas(alunos)
    print(f"Total de cobranças geradas: {len(cobrancas)}")

    print(f"Salvando em {DB_PATH} ...")
    salvar_no_duckdb(alunos, cobrancas)
    print("Concluído.")
