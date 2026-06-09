"""
============================================================
  O.R.B.I.T.A. — Energy Manager
  Motor 3: Gestão Sustentável de Energia Espacial
  Equipe: Aldebaran
============================================================
  Disciplina: Soluções em Energias Renováveis e Sustentáveis
  Gerencia o balanço energético da missão, simulando painéis
  solares virtuais, desgaste de bateria e automações de
  contingência para situações críticas.
============================================================
"""

from typing import Any

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

# ── Constantes do sistema energético ─────────────────────
POTENCIA_PAINEL_SOLAR_W   = 450.0   # Watts por painel solar virtual
NUM_PAINEIS_ATIVOS        = 4       # Painéis operacionais no início
CONSUMO_BASE_W            = 320.0   # Consumo base da nave em Watts
CONSUMO_MODULOS_EXTRAS_W  = 180.0   # Consumo de módulos não-essenciais
CAPACIDADE_BATERIA_WH     = 2000.0  # Capacidade total da bateria em Wh
DURACAO_CICLO_H           = 1.5     # Duração de cada ciclo em horas

# ── Limiares de decisão automática ───────────────────────
LIMIAR_BATERIA_CRITICO     = 20     # % — aciona desligamento de módulos extras
LIMIAR_BATERIA_ATENCAO     = 35     # % — alerta de atenção energética
LIMIAR_PAINEL_EFICIENCIA   = 0.75   # 75% — eficiência mínima aceitável

# ── Módulos não-essenciais (desligados em emergência) ─────
MODULOS_NAO_ESSENCIAIS: list[str] = [
    "Sistema de entretenimento",
    "Aquecimento de zona de carga",
    "Laboratório de experimentos secundários",
    "Iluminação de baixa prioridade",
]

# ── Módulos essenciais (nunca desligados) ─────────────────
MODULOS_ESSENCIAIS: list[str] = [
    "Suporte à vida (oxigênio e pressão)",
    "Comunicação de emergência",
    "Controle de temperatura crítica",
    "Computador de bordo principal",
    "Propulsão de emergência",
]


class GerenciadorEnergia:
    """Gerencia o balanço energético completo da missão espacial.

    Simula a geração de energia pelos painéis solares virtuais,
    o consumo da nave, o desgaste da bateria ao longo dos ciclos
    e as automações de contingência energética.

    Attributes:
        nivel_bateria_pct: Nível atual da bateria em porcentagem.
        paineis_ativos:    Número de painéis solares operacionais.
        modulos_extras_on: Se os módulos não-essenciais estão ligados.
        historico:         Registro de todos os ciclos energéticos.
        alertas:           Lista de alertas gerados pelo sistema.
    """

    def __init__(self, nivel_bateria_inicial: int = 92) -> None:
        """Inicializa o gerenciador com o estado do primeiro ciclo.

        Args:
            nivel_bateria_inicial: Nível de bateria inicial em % (do JSON).
        """
        self.nivel_bateria_pct: float = float(nivel_bateria_inicial)
        self.paineis_ativos: int = NUM_PAINEIS_ATIVOS
        self.modulos_extras_on: bool = True
        self.historico: list[dict[str, Any]] = []
        self.alertas: list[str] = []

    # ── Cálculos de potência ──────────────────────────────

    def calcular_geracao_solar(self, eficiencia_percentual: float = 100.0) -> float:
        """Calcula a energia gerada pelos painéis solares no ciclo.

        A geração depende do número de painéis ativos e da eficiência,
        que pode ser reduzida por temperatura elevada ou danos.

        Args:
            eficiencia_percentual: Eficiência dos painéis (0–100%).

        Returns:
            Energia gerada em Wh para o ciclo atual.
        """
        eficiencia = eficiencia_percentual / 100.0
        potencia_total = POTENCIA_PAINEL_SOLAR_W * self.paineis_ativos * eficiencia
        energia_gerada_wh = potencia_total * DURACAO_CICLO_H
        return round(energia_gerada_wh, 2)

    def calcular_consumo_ciclo(self) -> float:
        """Calcula o consumo total de energia no ciclo atual.

        Se os módulos extras estão ativos, soma o consumo adicional.

        Returns:
            Energia consumida em Wh no ciclo.
        """
        consumo = CONSUMO_BASE_W
        if self.modulos_extras_on:
            consumo += CONSUMO_MODULOS_EXTRAS_W
        energia_consumida_wh = consumo * DURACAO_CICLO_H
        return round(energia_consumida_wh, 2)

    def calcular_balanco(self, energia_gerada: float, energia_consumida: float) -> float:
        """Calcula o balanço energético líquido do ciclo.

        Args:
            energia_gerada:   Energia produzida pelos painéis (Wh).
            energia_consumida: Energia consumida pela nave (Wh).

        Returns:
            Balanço líquido em Wh (positivo = superávit, negativo = déficit).
        """
        return round(energia_gerada - energia_consumida, 2)

    def atualizar_bateria(self, balanco_wh: float) -> float:
        """Atualiza o nível da bateria com base no balanço do ciclo.

        Converte o balanço em variação percentual e limita entre 0 e 100%.

        Args:
            balanco_wh: Balanço energético do ciclo em Wh.

        Returns:
            Novo nível da bateria em porcentagem.
        """
        variacao_pct = (balanco_wh / CAPACIDADE_BATERIA_WH) * 100.0
        self.nivel_bateria_pct = max(0.0, min(100.0, self.nivel_bateria_pct + variacao_pct))
        return round(self.nivel_bateria_pct, 1)

    # ── Automações de contingência ────────────────────────

    def executar_automacoes(self, temperatura: int) -> list[str]:
        """Executa as automações lógicas de contingência energética.

        Regras implementadas:
          1. Bateria < 20%  → desligar módulos não-essenciais
          2. Bateria > 50%  → reativar módulos (se temperatura OK)
          3. Temperatura > 35°C → reduzir eficiência dos painéis
          4. Eficiência < 75% → gerar alerta de painel degradado

        Args:
            temperatura: Temperatura atual do módulo em °C.

        Returns:
            Lista de ações automáticas executadas no ciclo.
        """
        acoes: list[str] = []

        # Automação 1 — Economia de energia crítica
        if self.nivel_bateria_pct < LIMIAR_BATERIA_CRITICO:
            if self.modulos_extras_on:
                self.modulos_extras_on = False
                acoes.append(
                    f"{RED}[AUTO] ECONOMIA CRÍTICA: módulos não-essenciais desligados.{RESET}"
                )
                for mod in MODULOS_NAO_ESSENCIAIS:
                    acoes.append(f"{DIM}       ✗ {mod} — OFFLINE{RESET}")

        # Automação 2 — Reativação de módulos (recuperação)
        elif self.nivel_bateria_pct > 50 and not self.modulos_extras_on:
            if temperatura <= 30:
                self.modulos_extras_on = True
                acoes.append(
                    f"{GREEN}[AUTO] RECUPERAÇÃO: módulos não-essenciais reativados.{RESET}"
                )

        # Automação 3 — Redução de eficiência por temperatura
        if temperatura > 35:
            acoes.append(
                f"{YELLOW}[AUTO] Temperatura crítica ({temperatura}°C): "
                f"eficiência dos painéis reduzida para 70%.{RESET}"
            )

        # Automação 4 — Alerta de atenção energética
        if LIMIAR_BATERIA_CRITICO <= self.nivel_bateria_pct < LIMIAR_BATERIA_ATENCAO:
            acoes.append(
                f"{YELLOW}[ALERTA] Bateria em zona de atenção ({self.nivel_bateria_pct:.1f}%). "
                f"Monitorar consumo.{RESET}"
            )

        return acoes

    # ── Processamento do ciclo ────────────────────────────

    def processar_ciclo(self, numero: int, bateria_telemetria: int, temperatura: int) -> dict[str, Any]:
        """Processa o ciclo energético completo da missão.

        Sincroniza o nível de bateria com a telemetria real,
        calcula geração e consumo, atualiza o balanço e executa
        as automações de contingência.

        Args:
            numero:             Número do ciclo (1-based).
            bateria_telemetria: Valor de bateria lido do JSON/matriz.
            temperatura:        Temperatura do ciclo para ajuste de eficiência.

        Returns:
            Dicionário com o resumo energético do ciclo.
        """
        # Sincronizar com telemetria real (fonte de verdade)
        self.nivel_bateria_pct = float(bateria_telemetria)

        # Calcular eficiência dos painéis (degrada com calor)
        eficiencia = 70.0 if temperatura > 35 else 100.0

        energia_gerada    = self.calcular_geracao_solar(eficiencia)
        energia_consumida = self.calcular_consumo_ciclo()
        balanco           = self.calcular_balanco(energia_gerada, energia_consumida)

        # Executar automações antes de atualizar bateria
        acoes = self.executar_automacoes(temperatura)

        # Projeção do próximo ciclo (informativo)
        projecao_bateria = self.atualizar_bateria(balanco)

        # Classificar status energético
        if bateria_telemetria < LIMIAR_BATERIA_CRITICO:
            status_energia = f"{RED}CRÍTICO{RESET}"
        elif bateria_telemetria < LIMIAR_BATERIA_ATENCAO:
            status_energia = f"{YELLOW}ATENÇÃO{RESET}"
        else:
            status_energia = f"{GREEN}NORMAL{RESET}"

        resultado = {
            "ciclo":              numero,
            "bateria_atual_pct":  bateria_telemetria,
            "eficiencia_painel":  eficiencia,
            "energia_gerada_wh":  energia_gerada,
            "energia_consumida_wh": energia_consumida,
            "balanco_wh":         balanco,
            "projecao_bateria_pct": projecao_bateria,
            "modulos_extras_on":  self.modulos_extras_on,
            "paineis_ativos":     self.paineis_ativos,
            "acoes_automaticas":  acoes,
            "status_energia":     status_energia,
        }

        self.historico.append(resultado)
        return resultado

    # ── Display ───────────────────────────────────────────

    def exibir_ciclo_energetico(self, resultado: dict[str, Any]) -> None:
        """Exibe o resumo energético de um ciclo no terminal.

        Args:
            resultado: Dicionário retornado por processar_ciclo().
        """
        ciclo = resultado["ciclo"]
        print(f"  {CYAN}{BOLD}⚡ ENERGIA — CICLO {ciclo}{RESET}")
        print(f"  {'─' * 54}")

        bat = resultado["bateria_atual_pct"]
        bar_len = int(bat / 5)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        cor_bat = RED if bat < 20 else (YELLOW if bat < 35 else GREEN)
        print(f"  Bateria atual    : {cor_bat}{BOLD}[{bar}] {bat}%{RESET}")

        print(f"  Painéis solares  : {BOLD}{resultado['paineis_ativos']} painéis{RESET}"
              f"  |  Eficiência: {BOLD}{resultado['eficiencia_painel']:.0f}%{RESET}")
        print(f"  Energia gerada   : {GREEN}{BOLD}{resultado['energia_gerada_wh']:.1f} Wh{RESET}")
        print(f"  Energia consumida: {RED}{BOLD}{resultado['energia_consumida_wh']:.1f} Wh{RESET}")

        balanco = resultado["balanco_wh"]
        cor_bal = GREEN if balanco >= 0 else RED
        sinal   = "+" if balanco >= 0 else ""
        print(f"  Balanço líquido  : {cor_bal}{BOLD}{sinal}{balanco:.1f} Wh{RESET}")

        status_mod = f"{GREEN}ATIVOS{RESET}" if resultado["modulos_extras_on"] else f"{RED}OFFLINE{RESET}"
        print(f"  Módulos extras   : {BOLD}{status_mod}")

        if resultado["acoes_automaticas"]:
            print()
            for acao in resultado["acoes_automaticas"]:
                print(f"  {acao}")

        print()

    def exibir_relatorio_energetico(self) -> None:
        """Exibe o relatório energético completo de toda a missão."""
        if not self.historico:
            print(f"{YELLOW}  Nenhum dado energético registrado.{RESET}")
            return

        print(f"\n{CYAN}{BOLD}{'═' * 62}{RESET}")
        print(f"{CYAN}{BOLD}  RELATÓRIO ENERGÉTICO DA MISSÃO{RESET}")
        print(f"{CYAN}{BOLD}{'═' * 62}{RESET}")

        total_gerado   = sum(r["energia_gerada_wh"] for r in self.historico)
        total_consumido = sum(r["energia_consumida_wh"] for r in self.historico)
        balanco_total  = total_gerado - total_consumido
        ciclos_criticos = sum(1 for r in self.historico if r["bateria_atual_pct"] < LIMIAR_BATERIA_CRITICO)
        ciclos_economia = sum(1 for r in self.historico if not r["modulos_extras_on"])

        print(f"  Total gerado pelos painéis : {GREEN}{BOLD}{total_gerado:.1f} Wh{RESET}")
        print(f"  Total consumido pela nave  : {RED}{BOLD}{total_consumido:.1f} Wh{RESET}")
        cor_bal = GREEN if balanco_total >= 0 else RED
        sinal   = "+" if balanco_total >= 0 else ""
        print(f"  Balanço total da missão    : {cor_bal}{BOLD}{sinal}{balanco_total:.1f} Wh{RESET}")
        print(f"  Ciclos com bateria crítica : {RED if ciclos_criticos else GREEN}{BOLD}{ciclos_criticos}{RESET}")
        print(f"  Ciclos em modo economia    : {YELLOW}{BOLD}{ciclos_economia}{RESET}")

        # Módulos essenciais — sempre ativos
        print(f"\n  {WHITE}Módulos essenciais (sempre protegidos):{RESET}")
        for mod in MODULOS_ESSENCIAIS:
            print(f"    {GREEN}✓{RESET} {mod}")

        print(f"\n{CYAN}{BOLD}{'═' * 62}{RESET}\n")


# ════════════════════════════════════════════════════════════
#  INTEGRAÇÃO COM mission_control.py
# ════════════════════════════════════════════════════════════

def executar_analise_energetica(dados_missao: list[list[int]]) -> GerenciadorEnergia:
    """Ponto de entrada para integração com o mission_control.

    Recebe a matriz dados_missao já carregada e processa o
    ciclo energético de cada linha, exibindo os resultados.

    Args:
        dados_missao: Matriz [[temp, comm, bat, o2, estab], ...].

    Returns:
        Instância do GerenciadorEnergia após processar todos os ciclos.
    """
    bateria_inicial = dados_missao[0][2] if dados_missao else 92
    gerenciador = GerenciadorEnergia(nivel_bateria_inicial=bateria_inicial)

    print(f"\n{CYAN}{BOLD}{'═' * 62}{RESET}")
    print(f"{CYAN}{BOLD}  ANÁLISE ENERGÉTICA — PAINÉIS SOLARES & BATERIA{RESET}")
    print(f"{CYAN}{BOLD}{'═' * 62}{RESET}\n")

    for i, ciclo in enumerate(dados_missao):
        temperatura = ciclo[0]
        bateria     = ciclo[2]
        resultado   = gerenciador.processar_ciclo(i + 1, bateria, temperatura)
        gerenciador.exibir_ciclo_energetico(resultado)

    gerenciador.exibir_relatorio_energetico()
    return gerenciador


# ════════════════════════════════════════════════════════════
#  EXECUÇÃO STANDALONE (teste isolado)
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Dados de exemplo para teste isolado
    dados_teste: list[list[int]] = [
        [22, 95, 92, 97, 91],
        [26, 88, 80, 95, 84],
        [31, 52, 65, 91, 72],
        [37, 41, 33, 86, 54],
        [40, 25, 17, 76, 32],
        [33, 58, 29, 83, 48],
    ]
    executar_analise_energetica(dados_teste)
