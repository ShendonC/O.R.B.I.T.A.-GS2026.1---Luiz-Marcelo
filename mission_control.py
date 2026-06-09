"""
============================================================
  O.R.B.I.T.A. — Mission Control AI
  Operational Risk & Balance Intelligence via Technique Analysis
  Equipe: Aldebaran
============================================================
  Disciplinas: Pensamento Computacional | DSA
  Arquivo principal do sistema de monitoramento.
============================================================
"""

import json
import os
from typing import Any

from energy_manager import executar_analise_energetica
from ai_copilot import processar_ciclos_criticos, consultar_agente_energia

# ── Constantes de cor ANSI ────────────────────────────────
RESET   = "\033[0m"
BOLD    = "\033[1m"
CYAN    = "\033[96m"
GREEN   = "\033[92m"
YELLOW  = "\033[93m"
RED     = "\033[91m"
MAGENTA = "\033[95m"
WHITE   = "\033[97m"
DIM     = "\033[2m"

# ── Configuração da missão ────────────────────────────────
NOME_MISSAO = "O.R.B.I.T.A."
NOME_EQUIPE = "Aldebaran"
ARQUIVO_TELEMETRIA = os.path.join(os.path.dirname(__file__), "data", "telemetria.json")

# ── Áreas monitoradas (alinhadas às colunas da matriz) ────
areas_monitoradas: list[str] = [
    "Temperatura interna",
    "Comunicacao com a base",
    "Sistema de energia",
    "Suporte de oxigenio",
    "Estabilidade operacional",
]

# ── Matriz principal de dados ─────────────────────────────
# Cada linha: [temperatura, comunicacao, bateria, oxigenio, estabilidade]
dados_missao: list[list[int]] = [
    [22, 95, 92, 97, 91],   # Ciclo 1 — Inicio da missao
    [26, 88, 80, 95, 84],   # Ciclo 2 — Estabilizacao dos sistemas
    [31, 52, 65, 91, 72],   # Ciclo 3 — Queda parcial de comunicacao
    [37, 41, 33, 86, 54],   # Ciclo 4 — Alerta de energia e temperatura
    [40, 25, 17, 76, 32],   # Ciclo 5 — Risco operacional critico
    [33, 58, 29, 83, 48],   # Ciclo 6 — Tentativa de recuperacao
]

nomes_ciclos: list[str] = [
    "Inicio da missao",
    "Estabilizacao dos sistemas",
    "Queda parcial de comunicacao",
    "Alerta de energia e temperatura",
    "Risco operacional critico",
    "Tentativa de recuperacao",
]


# ════════════════════════════════════════════════════════════
#  MOTOR 1 — INGESTÃO DE DADOS (DSA)
# ════════════════════════════════════════════════════════════

def carregar_telemetria(caminho: str) -> list[dict[str, Any]]:
    """Lê o arquivo JSON de telemetria e retorna a lista de ciclos.

    Implementa a ingestão de dados via mock API (telemetria.json),
    garantindo Zero Input Manual conforme arquitetura do projeto.

    Args:
        caminho: Caminho para o arquivo telemetria.json.

    Returns:
        Lista de dicionários com os dados de cada ciclo.
        Retorna lista vazia se o arquivo não for encontrado.
    """
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            payload = json.load(f)
        return payload.get("ciclos", [])
    except FileNotFoundError:
        print(f"{YELLOW}[AVISO] Arquivo de telemetria nao encontrado: {caminho}{RESET}")
        print(f"{DIM}Usando dados internos da matriz dados_missao.{RESET}")
        return []


def construir_matriz_de_json(ciclos_json: list[dict[str, Any]]) -> list[list[int]]:
    """Converte os ciclos do JSON para a matriz dados_missao padrão.

    Garante compatibilidade entre o formato da API e a estrutura
    interna de análise do sistema.

    Args:
        ciclos_json: Lista de dicionários lidos do JSON.

    Returns:
        Matriz no formato [[temp, comm, bat, o2, estab], ...].
    """
    matriz: list[list[int]] = []
    for ciclo in ciclos_json:
        linha = [
            ciclo.get("temperatura", 0),
            ciclo.get("comunicacao", 0),
            ciclo.get("bateria", 0),
            ciclo.get("oxigenio", 0),
            ciclo.get("estabilidade", 0),
        ]
        matriz.append(linha)
    return matriz


# ════════════════════════════════════════════════════════════
#  MOTOR 2 — REGRAS DE NEGÓCIO E DIAGNÓSTICO (Pensamento Comp.)
# ════════════════════════════════════════════════════════════

def analisar_temperatura(valor: int) -> tuple[str, int, str]:
    """Classifica a temperatura interna do módulo.

    Regras:
        < 18°C         → ATENÇÃO  (frio extremo, risco de falha mecânica)
        18°C a 30°C    → NORMAL
        30°C a 35°C    → ATENÇÃO  (aquecimento moderado)
        > 35°C         → CRÍTICO  (superaquecimento)

    Args:
        valor: Temperatura em graus Celsius.

    Returns:
        Tupla (classificacao, pontuacao, mensagem).
    """
    if valor > 35:
        return ("CRITICO", 2, "Risco de superaquecimento")
    elif valor > 30:
        return ("ATENCAO", 1, "Temperatura elevada")
    elif valor < 18:
        return ("ATENCAO", 1, "Temperatura abaixo do ideal")
    else:
        return ("NORMAL", 0, "Temperatura estavel")


def analisar_comunicacao(valor: int) -> tuple[str, int, str]:
    """Classifica o sinal de comunicacao com a base.

    Regras (DSA — verificação: comunicação = 0 → Falha):
        < 30%   → CRÍTICO (falha de comunicacao)
        30–59%  → ATENÇÃO (sinal instavel)
        >= 60%  → NORMAL

    Args:
        valor: Percentual de qualidade do sinal (0–100).

    Returns:
        Tupla (classificacao, pontuacao, mensagem).
    """
    if valor < 30:
        return ("CRITICO", 2, "Comunicacao com a base em nivel critico")
    elif valor < 60:
        return ("ATENCAO", 1, "Comunicacao instavel")
    else:
        return ("NORMAL", 0, "Comunicacao estavel")


def analisar_bateria(valor: int) -> tuple[str, int, str]:
    """Classifica o nivel de bateria do sistema de energia.

    Regras (DSA — verificação: energia < 20 → Economia):
        < 20%   → CRÍTICO (economia de energia ativada)
        20–49%  → ATENÇÃO
        >= 50%  → NORMAL

    Args:
        valor: Percentual de carga da bateria (0–100).

    Returns:
        Tupla (classificacao, pontuacao, mensagem).
    """
    if valor < 20:
        return ("CRITICO", 2, "Bateria em nivel critico")
    elif valor < 50:
        return ("ATENCAO", 1, "Bateria abaixo do recomendado")
    else:
        return ("NORMAL", 0, "Energia estavel")


def analisar_oxigenio(valor: int) -> tuple[str, int, str]:
    """Classifica o nivel de oxigenio disponivel.

    Regras:
        < 80%   → CRÍTICO (protocolo de suporte a vida)
        80–89%  → ATENÇÃO
        >= 90%  → NORMAL

    Args:
        valor: Percentual de oxigenio disponivel (0–100).

    Returns:
        Tupla (classificacao, pontuacao, mensagem).
    """
    if valor < 80:
        return ("CRITICO", 2, "Oxigenio em nivel critico")
    elif valor < 90:
        return ("ATENCAO", 1, "Oxigenio abaixo do ideal")
    else:
        return ("NORMAL", 0, "Oxigenio adequado")


def analisar_estabilidade(valor: int) -> tuple[str, int, str]:
    """Classifica a estabilidade operacional geral da nave.

    Regras:
        < 40%   → CRÍTICO (reduzir operacoes nao essenciais)
        40–69%  → ATENÇÃO
        >= 70%  → NORMAL

    Args:
        valor: Percentual de estabilidade (0–100).

    Returns:
        Tupla (classificacao, pontuacao, mensagem).
    """
    if valor < 40:
        return ("CRITICO", 2, "Estabilidade operacional critica")
    elif valor < 70:
        return ("ATENCAO", 1, "Estabilidade operacional reduzida")
    else:
        return ("NORMAL", 0, "Estabilidade operacional adequada")


def classificar_ciclo(pontuacao: int) -> str:
    """Classifica o estado geral do ciclo pela pontuacao de risco.

    Escala:
        0–2  → MISSAO ESTAVEL
        3–5  → MISSAO EM ATENCAO
        6–10 → MISSAO CRITICA

    Args:
        pontuacao: Soma dos pontos do ciclo (0 a 10).

    Returns:
        String com a classificacao do ciclo.
    """
    if pontuacao <= 2:
        return "MISSAO ESTAVEL"
    elif pontuacao <= 5:
        return "MISSAO EM ATENCAO"
    else:
        return "MISSAO CRITICA"


def gerar_recomendacao(classificacoes: list[tuple[str, int, str]]) -> str:
    """Gera recomendacao automatica baseada nas classificacoes do ciclo.

    Prioriza as situacoes mais criticas para formular a acao sugerida.

    Args:
        classificacoes: Lista de tuplas (classificacao, pontuacao, mensagem)
                        para cada metrica do ciclo.

    Returns:
        String com a recomendacao de acao para o ciclo.
    """
    criticos: list[str] = []
    for i, (status, _, _) in enumerate(classificacoes):
        if status == "CRITICO":
            criticos.append(areas_monitoradas[i])

    if not criticos:
        return "Manter operacao normal e continuar monitoramento."

    acoes: dict[str, str] = {
        "Temperatura interna":       "verificar controle termico da missao",
        "Comunicacao com a base":    "tentar restabelecer contato com a base",
        "Sistema de energia":        "ativar modo de economia de energia",
        "Suporte de oxigenio":       "acionar protocolo de suporte a vida",
        "Estabilidade operacional":  "reduzir operacoes nao essenciais",
    }

    if len(criticos) >= 3:
        return "ALERTA MAXIMO: Ativar modo de seguranca e priorizar suporte a vida, energia e comunicacao."

    partes = [acoes[area] for area in criticos if area in acoes]
    return "Acoes recomendadas: " + " | ".join(partes).capitalize() + "."


# ════════════════════════════════════════════════════════════
#  MOTOR 2 — ANÁLISE COMPLETA DE UM CICLO
# ════════════════════════════════════════════════════════════

def analisar_ciclo(ciclo: list[int]) -> dict[str, Any]:
    """Executa a analise completa de um ciclo da missao.

    Percorre cada metrica da linha da matriz, classifica, pontua
    e compila o resultado em um dicionario estruturado.

    Args:
        ciclo: Lista [temperatura, comunicacao, bateria, oxigenio, estabilidade].

    Returns:
        Dicionario com classificacoes, pontuacao total e classificacao geral.
    """
    funcoes_analise = [
        analisar_temperatura,
        analisar_comunicacao,
        analisar_bateria,
        analisar_oxigenio,
        analisar_estabilidade,
    ]

    classificacoes: list[tuple[str, int, str]] = []
    pontuacao_total = 0

    for i, func in enumerate(funcoes_analise):
        resultado = func(ciclo[i])
        classificacoes.append(resultado)
        pontuacao_total += resultado[1]

    classificacao_geral = classificar_ciclo(pontuacao_total)
    recomendacao = gerar_recomendacao(classificacoes)

    return {
        "valores": ciclo,
        "classificacoes": classificacoes,
        "pontuacao": pontuacao_total,
        "status": classificacao_geral,
        "recomendacao": recomendacao,
    }


# ════════════════════════════════════════════════════════════
#  MOTOR 2 — TENDÊNCIA E ÁREA MAIS AFETADA
# ════════════════════════════════════════════════════════════

def analisar_tendencia(resultados: list[dict[str, Any]]) -> str:
    """Compara o risco do primeiro e do ultimo ciclo para identificar tendencia.

    Args:
        resultados: Lista de dicionarios retornados por analisar_ciclo().

    Returns:
        String descrevendo a tendencia da missao.
    """
    if len(resultados) < 2:
        return "Dados insuficientes para analise de tendencia."

    risco_inicial = resultados[0]["pontuacao"]
    risco_final   = resultados[-1]["pontuacao"]

    if risco_final > risco_inicial:
        return "A missao apresentou tendencia de PIORA."
    elif risco_final < risco_inicial:
        return "A missao apresentou tendencia de MELHORA."
    else:
        return "A missao permaneceu ESTAVEL em relacao ao inicio."


def identificar_area_mais_afetada(resultados: list[dict[str, Any]]) -> tuple[str, list[int]]:
    """Soma a pontuacao de risco de cada area ao longo de todos os ciclos.

    Args:
        resultados: Lista de dicionarios retornados por analisar_ciclo().

    Returns:
        Tupla (nome_da_area_mais_afetada, lista_de_pontuacoes_acumuladas).
    """
    acumulado = [0] * len(areas_monitoradas)

    for resultado in resultados:
        for i, (_, pontos, _) in enumerate(resultado["classificacoes"]):
            acumulado[i] += pontos

    indice_max = acumulado.index(max(acumulado))
    return (areas_monitoradas[indice_max], acumulado)


# ════════════════════════════════════════════════════════════
#  MOTOR 2 — LÓGICA BOOLEANA X=1 (Computer Science)
# ════════════════════════════════════════════════════════════

def avaliar_alerta_booleano(ciclo: list[int]) -> dict[str, Any]:
    """Implementa o sistema de alerta por logica digital (X = 1).

    Variaveis de entrada (binarias):
        A = Falha de comunicacao       (comunicacao < 30)
        B = Temperatura critica        (temperatura > 35)
        C = Baixo nivel de energia     (bateria < 20)
        D = Falha operacional          (estabilidade < 40)
        E = Suporte de vida critico    (oxigenio < 80)

    Expressao logica:
        X = A OR B OR C OR D OR E
        (alerta acionado se QUALQUER condicao critica for verdadeira)

    Expressao simplificada:
        X = A + B + C + D + E  (notacao booleana)

    Args:
        ciclo: Lista [temperatura, comunicacao, bateria, oxigenio, estabilidade].

    Returns:
        Dicionario com os valores das variaveis e o resultado X.
    """
    temp, comm, bat, o2, estab = ciclo

    A = int(comm < 30)    # Falha de comunicacao
    B = int(temp > 35)    # Temperatura critica
    C = int(bat < 20)     # Baixo nivel de energia
    D = int(estab < 40)   # Falha operacional
    E = int(o2 < 80)      # Suporte de vida critico

    X = int(A or B or C or D or E)

    return {
        "variaveis": {"A": A, "B": B, "C": C, "D": D, "E": E},
        "expressao": "X = A OR B OR C OR D OR E",
        "X": X,
        "alerta_ativo": bool(X),
    }


# ════════════════════════════════════════════════════════════
#  VERIFICAÇÃO AUTOMÁTICA BÁSICA (DSA)
# ════════════════════════════════════════════════════════════

def verificacao_automatica(temperatura: int, energia: int, comunicacao: int) -> list[str]:
    """Verificacao automatica basica conforme requisito DSA.

    Implementa as tres verificacoes diretas exigidas pela disciplina
    de Data Structures and Algorithms:
        Temperatura > 80  -> Alerta de superaquecimento
        Energia < 20      -> Economia de energia
        Comunicacao == 0  -> Falha de comunicacao

    Estas verificacoes sao independentes das regras de classificacao
    do motor de diagnostico (que usam faixas mais granulares).

    Args:
        temperatura: Temperatura da nave em graus Celsius.
        energia:     Percentual de energia/bateria (0-100).
        comunicacao: Status/qualidade da comunicacao (0-100).

    Returns:
        Lista de strings com os alertas acionados. Vazia se tudo normal.
    """
    alertas: list[str] = []

    if temperatura > 80:
        alertas.append("Alerta de superaquecimento")
    if energia < 20:
        alertas.append("Economia de energia")
    if comunicacao == 0:
        alertas.append("Falha de comunicacao")

    return alertas


# ════════════════════════════════════════════════════════════
#  OUTPUT — EXIBIÇÃO NO TERMINAL (colorido)
# ════════════════════════════════════════════════════════════

def _cor_status(status: str) -> str:
    """Retorna a cor ANSI correspondente ao status da metrica."""
    if status == "CRITICO":
        return RED
    elif status == "ATENCAO":
        return YELLOW
    return GREEN


def _cor_ciclo(status: str) -> str:
    """Retorna a cor ANSI correspondente ao status do ciclo."""
    if "CRITICA" in status:
        return RED
    elif "ATENCAO" in status:
        return YELLOW
    return GREEN


def exibir_cabecalho() -> None:
    """Exibe o cabecalho do sistema no terminal."""
    print(f"\n{CYAN}{BOLD}{'═' * 62}{RESET}")
    print(f"{CYAN}{BOLD}  ██████╗ ██████╗ ██████╗ ██╗████████╗ █████╗ {RESET}")
    print(f"{CYAN}{BOLD}  ██╔══██╗██╔══██╗██╔══██╗██║╚══██╔══╝██╔══██╗{RESET}")
    print(f"{CYAN}{BOLD}  ██║  ██║██████╔╝██████╔╝██║   ██║   ███████║{RESET}")
    print(f"{CYAN}{BOLD}  ██║  ██║██╔══██╗██╔══██╗██║   ██║   ██╔══██║{RESET}")
    print(f"{CYAN}{BOLD}  ██████╔╝██████╔╝██████╔╝██║   ██║   ██║  ██║{RESET}")
    print(f"{CYAN}{BOLD}  ╚═════╝ ╚═════╝ ╚═════╝ ╚═╝   ╚═╝   ╚═╝  ╚═╝{RESET}")
    print(f"{CYAN}{BOLD}{'═' * 62}{RESET}")
    print(f"  {WHITE}Missao : {BOLD}{NOME_MISSAO}{RESET}")
    print(f"  {WHITE}Equipe : {BOLD}{NOME_EQUIPE}{RESET}")
    print(f"  {DIM}Operational Risk & Balance Intelligence via Technique Analysis{RESET}")
    print(f"{CYAN}{BOLD}{'═' * 62}{RESET}\n")


def exibir_ciclo(numero: int, nome: str, resultado: dict[str, Any], alerta: dict[str, Any]) -> None:
    """Exibe a analise detalhada de um ciclo no terminal.

    Args:
        numero:    Numero do ciclo (1-based).
        nome:      Nome descritivo do ciclo.
        resultado: Dicionario retornado por analisar_ciclo().
        alerta:    Dicionario retornado por avaliar_alerta_booleano().
    """
    cor_ciclo = _cor_ciclo(resultado["status"])
    print(f"{BOLD}{CYAN}  CICLO {numero} — {nome}{RESET}")
    print(f"  {'─' * 58}")

    labels = ["Temperatura", "Comunicacao", "Bateria    ", "Oxigenio   ", "Estabilidade"]
    unidades = ["°C", "%", "%", "%", "%"]

    for i, (status, _, msg) in enumerate(resultado["classificacoes"]):
        cor = _cor_status(status)
        valor = resultado["valores"][i]
        unidade = unidades[i]
        print(
            f"  {WHITE}{labels[i]}: {BOLD}{valor:>3}{unidade}{RESET}"
            f"  {cor}[{status:^8}]{RESET}"
            f"  {DIM}{msg}{RESET}"
        )

    # Alerta booleano X=1
    x_val = alerta["X"]
    x_cor = RED if x_val else GREEN
    vars_str = " | ".join(f"{k}={v}" for k, v in alerta["variaveis"].items())
    print(f"\n  {DIM}Logica digital: {vars_str}  →  {x_cor}{BOLD}X={x_val}{RESET}")

    print(
        f"\n  Pontuacao de risco : {BOLD}{resultado['pontuacao']}/10{RESET}"
    )
    print(
        f"  Status do ciclo    : {cor_ciclo}{BOLD}{resultado['status']}{RESET}"
    )
    print(
        f"  Recomendacao       : {YELLOW}{resultado['recomendacao']}{RESET}"
    )
    print()


def gerar_relatorio_final(
    resultados: list[dict[str, Any]],
    alertas: list[dict[str, Any]],
) -> None:
    """Exibe o relatorio final completo da missao no terminal.

    Inclui: estatisticas gerais, ciclos criticos, risco medio,
    tendencia, pontuacao por area e conclusao da missao.

    Args:
        resultados: Lista de dicionarios de cada ciclo analisado.
        alertas:    Lista de dicionarios do alerta booleano de cada ciclo.
    """
    print(f"\n{CYAN}{BOLD}{'═' * 62}{RESET}")
    print(f"{CYAN}{BOLD}  RELATORIO FINAL DA MISSAO{RESET}")
    print(f"{CYAN}{BOLD}{'═' * 62}{RESET}")
    print(f"  {WHITE}Missao : {BOLD}{NOME_MISSAO}{RESET}")
    print(f"  {WHITE}Equipe : {BOLD}{NOME_EQUIPE}{RESET}")
    print(f"  {WHITE}Ciclos analisados: {BOLD}{len(resultados)}{RESET}")
    print(f"  {'─' * 58}")

    # ── Médias por metrica ─────────────────────────────────
    n = len(resultados)
    medias = [0.0] * 5
    for r in resultados:
        for i, v in enumerate(r["valores"]):
            medias[i] += v
    medias = [m / n for m in medias]

    labels_med = ["Temperatura", "Comunicacao", "Bateria    ", "Oxigenio   ", "Estabilidade"]
    unidades   = ["°C", "%", "%", "%", "%"]
    for i, label in enumerate(labels_med):
        print(f"  Media de {label}: {BOLD}{medias[i]:.1f}{unidades[i]}{RESET}")

    print(f"  {'─' * 58}")

    # ── Ciclos criticos ────────────────────────────────────
    ciclos_criticos = [i + 1 for i, r in enumerate(resultados) if "CRITICA" in r["status"]]
    ciclo_max       = max(resultados, key=lambda r: r["pontuacao"])
    idx_max         = resultados.index(ciclo_max) + 1
    risco_medio     = sum(r["pontuacao"] for r in resultados) / n
    alertas_x1      = sum(1 for a in alertas if a["X"] == 1)

    print(f"  Ciclos criticos        : {RED}{BOLD}{ciclos_criticos if ciclos_criticos else 'Nenhum'}{RESET}")
    print(f"  Ciclo mais critico     : {RED}{BOLD}Ciclo {idx_max}{RESET}")
    print(f"  Maior pontuacao risco  : {BOLD}{ciclo_max['pontuacao']}/10{RESET}")
    print(f"  Risco medio da missao  : {BOLD}{risco_medio:.2f}{RESET}")
    print(f"  Alertas X=1 acionados  : {RED if alertas_x1 else GREEN}{BOLD}{alertas_x1}{RESET}")

    print(f"  {'─' * 58}")

    # ── Tendencia ──────────────────────────────────────────
    tendencia = analisar_tendencia(resultados)
    print(f"  Tendencia da missao    : {BOLD}{tendencia}{RESET}")

    print(f"  {'─' * 58}")

    # ── Pontuacao por area ─────────────────────────────────
    area_mais_afetada, acumulado = identificar_area_mais_afetada(resultados)
    print(f"  {WHITE}Pontuacao acumulada por area:{RESET}")
    for i, area in enumerate(areas_monitoradas):
        destaque = RED + BOLD if area == area_mais_afetada else ""
        print(f"    {destaque}{area:<30}: {acumulado[i]} pontos{RESET}")

    print(f"\n  {WHITE}Area mais afetada: {RED}{BOLD}{area_mais_afetada}{RESET}")

    print(f"  {'─' * 58}")

    # ── Classificação final ────────────────────────────────
    pontuacoes = [r["pontuacao"] for r in resultados]
    media_final = sum(pontuacoes) / n
    status_final = classificar_ciclo(round(media_final))
    cor_final = _cor_ciclo(status_final)

    print(f"\n  {WHITE}Classificacao final: {cor_final}{BOLD}{status_final}{RESET}")

    # ── Conclusao ──────────────────────────────────────────
    conclusao_map = {
        "MISSAO ESTAVEL":      "A missao transcorreu dentro dos parametros normais. Sistemas operacionais estaveis.",
        "MISSAO EM ATENCAO":   "A missao apresentou instabilidade relevante. Manter plano de contingencia ativo.",
        "MISSAO CRITICA":      "A missao enfrentou situacoes de risco severo. Protocolo de emergencia necessario.",
    }
    conclusao = conclusao_map.get(status_final, "Status indeterminado.")
    print(f"\n  {DIM}Conclusao: {conclusao}{RESET}")
    print(f"\n{CYAN}{BOLD}{'═' * 62}{RESET}\n")


# ════════════════════════════════════════════════════════════
#  MENU INTERATIVO (DSA)
# ════════════════════════════════════════════════════════════

def exibir_menu() -> None:
    """Exibe o menu principal do sistema."""
    print(f"\n{CYAN}{'─' * 40}{RESET}")
    print(f"  {BOLD}MENU — Mission Control AI{RESET}")
    print(f"{CYAN}{'─' * 40}{RESET}")
    print(f"  {WHITE}1{RESET} · Inserir / simular novo ciclo de leitura")
    print(f"  {WHITE}2{RESET} · Executar analise completa")
    print(f"  {WHITE}3{RESET} · Visualizar status atual")
    print(f"  {WHITE}4{RESET} · Historico de leituras")
    print(f"  {WHITE}5{RESET} · Relatorio final")
    print(f"  {WHITE}6{RESET} · Analise energetica (paineis solares)")
    print(f"  {WHITE}7{RESET} · Consultar ARIA (Agente de IA) sobre ciclos criticos")
    print(f"  {WHITE}8{RESET} · Encerrar sistema")
    print(f"{CYAN}{'─' * 40}{RESET}")


def menu_visualizar_status(
    resultados: list[dict[str, Any]],
    alertas: list[dict[str, Any]],
) -> None:
    """Exibe um resumo compacto do status de cada ciclo.

    Args:
        resultados: Lista de dicionarios de cada ciclo.
        alertas:    Lista de dicionarios do alerta booleano.
    """
    print(f"\n{BOLD}{'─' * 62}{RESET}")
    print(f"  {BOLD}STATUS ATUAL — {len(resultados)} ciclos monitorados{RESET}")
    print(f"{'─' * 62}{RESET}")
    for i, (r, a) in enumerate(zip(resultados, alertas)):
        cor = _cor_ciclo(r["status"])
        x_cor = RED if a["X"] else GREEN
        print(
            f"  Ciclo {i+1:>2} | Risco: {BOLD}{r['pontuacao']:>2}/10{RESET}"
            f" | {cor}{r['status']:<20}{RESET}"
            f" | X={x_cor}{BOLD}{a['X']}{RESET}"
        )
    print()


def menu_historico(dados: list[list[int]]) -> None:
    """Exibe o historico bruto de todas as leituras da matriz.

    Args:
        dados: Matriz dados_missao completa.
    """
    print(f"\n{BOLD}{'─' * 62}{RESET}")
    print(f"  {BOLD}HISTORICO DE LEITURAS{RESET}")
    print(f"  {'Ciclo':<8} {'Temp':>6} {'Comm':>6} {'Bat':>6} {'O2':>6} {'Estab':>6}")
    print(f"{'─' * 62}{RESET}")
    for i, linha in enumerate(dados):
        t, c, b, o, e = linha
        print(f"  {i+1:<8} {t:>5}°C {c:>5}%  {b:>5}%  {o:>5}%  {e:>5}%")
    print()


def menu_inserir_dados() -> list[int] | None:
    """Permite inserir manualmente ou simular um novo ciclo de leitura.

    Atende ao requisito de "Cadastro das Informacoes" da disciplina DSA,
    onde o usuario pode inserir dados por sensores ou simula-los. Apos a
    insercao, aplica a verificacao automatica basica (temp > 80, energia
    < 20, comunicacao == 0) exibindo os alertas imediatos.

    Returns:
        Lista [temp, comm, bat, o2, estab] do novo ciclo, ou None se cancelado.
    """
    import random

    print(f"\n{CYAN}{'─' * 50}{RESET}")
    print(f"  {BOLD}CADASTRO DE NOVO CICLO DE LEITURA{RESET}")
    print(f"{CYAN}{'─' * 50}{RESET}")
    print(f"  {WHITE}1{RESET} · Inserir dados manualmente")
    print(f"  {WHITE}2{RESET} · Simular leitura automatica de sensores")
    print(f"  {WHITE}0{RESET} · Cancelar")
    escolha = input(f"  {CYAN}>{RESET} Opcao: ").strip()

    if escolha == "0":
        return None

    if escolha == "2":
        # Simulacao automatica de sensores
        novo = [
            random.randint(15, 45),    # temperatura
            random.randint(20, 100),   # comunicacao
            random.randint(10, 100),   # bateria
            random.randint(70, 100),   # oxigenio
            random.randint(30, 100),   # estabilidade
        ]
        print(f"\n{GREEN}  Sensores simulados:{RESET}")
    elif escolha == "1":
        # Entrada manual com validacao
        def ler_int(rotulo: str, minv: int, maxv: int) -> int:
            while True:
                try:
                    v = int(input(f"  {rotulo}: ").strip())
                    if minv <= v <= maxv:
                        return v
                    print(f"  {YELLOW}Valor fora da faixa ({minv}-{maxv}).{RESET}")
                except ValueError:
                    print(f"  {YELLOW}Digite um numero inteiro.{RESET}")

        print(f"\n  {DIM}Informe os valores do novo ciclo:{RESET}")
        novo = [
            ler_int("Temperatura (°C)",  -50, 150),
            ler_int("Comunicacao (%)",     0, 100),
            ler_int("Bateria (%)",         0, 100),
            ler_int("Oxigenio (%)",        0, 100),
            ler_int("Estabilidade (%)",    0, 100),
        ]
    else:
        print(f"\n{YELLOW}  Opcao invalida.{RESET}")
        return None

    # Exibir o ciclo inserido
    labels = ["Temperatura", "Comunicacao", "Bateria", "Oxigenio", "Estabilidade"]
    unidades = ["°C", "%", "%", "%", "%"]
    for i in range(5):
        print(f"    {labels[i]:13}: {BOLD}{novo[i]}{unidades[i]}{RESET}")

    # Aplicar verificacao automatica basica (requisito DSA)
    alertas_basicos = verificacao_automatica(novo[0], novo[2], novo[1])
    if alertas_basicos:
        print(f"\n  {RED}{BOLD}Verificacao automatica — alertas acionados:{RESET}")
        for a in alertas_basicos:
            print(f"    {RED}⚠ {a}{RESET}")
    else:
        print(f"\n  {GREEN}Verificacao automatica: nenhum alerta basico.{RESET}")

    # Analise completa do ciclo inserido
    resultado = analisar_ciclo(novo)
    alerta    = avaliar_alerta_booleano(novo)
    print()
    exibir_ciclo(len(dados_missao) + 1, "Ciclo inserido pelo operador", resultado, alerta)

    return novo


# ════════════════════════════════════════════════════════════
#  EXECUÇÃO PRINCIPAL
# ════════════════════════════════════════════════════════════

def executar_analise_completa() -> tuple[list[dict], list[dict]]:
    """Roda a analise completa de todos os ciclos da missao.

    Percorre a matriz dados_missao, analisa cada ciclo,
    aplica a logica booleana e exibe os resultados no terminal.

    Returns:
        Tupla (resultados, alertas) para uso no relatorio final.
    """
    resultados: list[dict[str, Any]] = []
    alertas: list[dict[str, Any]] = []

    for i, ciclo in enumerate(dados_missao):
        nome = nomes_ciclos[i] if i < len(nomes_ciclos) else f"Ciclo {i+1}"
        resultado = analisar_ciclo(ciclo)
        alerta    = avaliar_alerta_booleano(ciclo)
        resultados.append(resultado)
        alertas.append(alerta)
        exibir_ciclo(i + 1, nome, resultado, alerta)

    return resultados, alertas


def main() -> None:
    """Ponto de entrada principal do Mission Control AI.

    Carrega a telemetria do arquivo JSON (mock API), inicializa
    a matriz de dados e executa o loop do menu interativo.
    """
    # Tentar carregar via JSON (mock API)
    global dados_missao, nomes_ciclos

    ciclos_json = carregar_telemetria(ARQUIVO_TELEMETRIA)
    if ciclos_json:
        dados_missao = construir_matriz_de_json(ciclos_json)
        nomes_ciclos = [c.get("nome", f"Ciclo {c['id']}") for c in ciclos_json]

    exibir_cabecalho()

    resultados: list[dict[str, Any]] = []
    alertas: list[dict[str, Any]] = []

    while True:
        exibir_menu()
        opcao = input(f"  {CYAN}>{RESET} Escolha uma opcao: ").strip()

        if opcao == "1":
            novo_ciclo = menu_inserir_dados()
            if novo_ciclo is not None:
                dados_missao.append(novo_ciclo)
                nomes_ciclos.append("Ciclo inserido pelo operador")
                print(f"\n{GREEN}  Ciclo adicionado ao histórico da missão.{RESET}\n")

        elif opcao == "2":
            print(f"\n{BOLD}  Iniciando analise completa...{RESET}\n")
            resultados, alertas = executar_analise_completa()

        elif opcao == "3":
            if not resultados:
                print(f"\n{YELLOW}  Execute a analise primeiro (opcao 2).{RESET}\n")
            else:
                menu_visualizar_status(resultados, alertas)

        elif opcao == "4":
            menu_historico(dados_missao)

        elif opcao == "5":
            if not resultados:
                print(f"\n{YELLOW}  Execute a analise primeiro (opcao 2).{RESET}\n")
            else:
                gerar_relatorio_final(resultados, alertas)

        elif opcao == "6":
            gerenciador = executar_analise_energetica(dados_missao)
            # ARIA comenta o contexto energético
            balanco_total = sum(r["balanco_wh"] for r in gerenciador.historico)
            bateria_minima = min(c[2] for c in dados_missao)
            ciclos_economia = sum(1 for r in gerenciador.historico if not r["modulos_extras_on"])
            dados_en = {
                "missao":             NOME_MISSAO,
                "balanco_total_wh":   round(balanco_total, 1),
                "bateria_minima_pct": bateria_minima,
                "ciclos_em_economia": ciclos_economia,
                "paineis_ativos":     gerenciador.paineis_ativos,
            }
            consultar_agente_energia(dados_en)

        elif opcao == "7":
            if not resultados:
                print(f"\n{YELLOW}  Execute a analise primeiro (opcao 2).{RESET}\n")
            else:
                processar_ciclos_criticos(resultados, nomes_ciclos)

        elif opcao == "8":
            print(f"\n{CYAN}  Encerrando Mission Control AI. Boa missao, Equipe {NOME_EQUIPE}.{RESET}\n")
            break

        else:
            print(f"\n{YELLOW}  Opcao invalida. Tente novamente.{RESET}\n")


if __name__ == "__main__":
    main()
