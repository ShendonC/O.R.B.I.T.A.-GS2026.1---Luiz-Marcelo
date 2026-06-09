"""
============================================================
  O.R.B.I.T.A. — Voice Module
  Text-to-Speech da ARIA (estilo assistente de bordo)
  Equipe: Aldebaran
============================================================
  Usa pyttsx3 (offline, voz do sistema operacional).
  Trata graciosamente a ausência de engine de áudio:
  se o sistema não tiver voz disponível, o app continua
  funcionando normalmente, apenas sem som.

  A ARIA NÃO fala tudo o que aparece no chat. Após uma
  análise, ela fala apenas um RESUMO DE UMA FRASE, no
  estilo de um assistente tipo Jarvis.
============================================================
"""

import threading
from typing import Any

# pyttsx3 é opcional — se não estiver instalado ou não houver
# engine de áudio, o módulo degrada graciosamente.
try:
    import pyttsx3
    _PYTTSX3_DISPONIVEL = True
except ImportError:
    _PYTTSX3_DISPONIVEL = False


class VozARIA:
    """Gerencia a síntese de voz da ARIA.

    Inicializa o engine pyttsx3 uma única vez e reaproveita.
    Toda fala roda em thread separada para não travar a interface.
    Se o engine não puder ser inicializado (sem áudio no sistema),
    o objeto entra em modo silencioso sem causar erros.

    Attributes:
        disponivel: True se a síntese de voz está operacional.
        habilitada: True se a fala está ligada (pode ser alternada).
    """

    def __init__(self, taxa: int = 190, volume: float = 0.9) -> None:
        """Inicializa o motor de voz.

        Args:
            taxa:   Velocidade da fala em palavras por minuto (padrão 190).
            volume: Volume de 0.0 a 1.0 (padrão 0.9).
        """
        self.disponivel: bool = False
        self.habilitada: bool = True
        self._engine: Any = None
        self._lock = threading.Lock()
        self._taxa = taxa
        self._volume = volume

        if _PYTTSX3_DISPONIVEL:
            try:
                self._engine = pyttsx3.init()
                self._engine.setProperty("rate", taxa)
                self._engine.setProperty("volume", volume)
                self._selecionar_voz_pt()
                self.disponivel = True
            except Exception:
                # Sem engine de áudio (ex: Linux sem eSpeak) — modo silencioso
                self.disponivel = False

    def _selecionar_voz_pt(self) -> None:
        """Tenta selecionar uma voz em português, se disponível no sistema."""
        try:
            vozes = self._engine.getProperty("voices")
            for voz in vozes:
                nome = (voz.name or "").lower()
                ident = (voz.id or "").lower()
                if any(t in nome or t in ident
                       for t in ["portug", "brazil", "brasil", "pt-br", "pt_br"]):
                    self._engine.setProperty("voice", voz.id)
                    return
        except Exception:
            pass  # mantém a voz padrão

    def falar(self, texto: str) -> None:
        """Fala um texto em voz alta, em thread separada (não bloqueia a UI).

        Se a voz não estiver disponível ou estiver desabilitada, não faz nada.

        Args:
            texto: Frase a ser falada (idealmente curta, 1 frase).
        """
        if not self.disponivel or not self.habilitada or not texto.strip():
            return

        t = threading.Thread(target=self._falar_sync, args=(texto,), daemon=True)
        t.start()

    def _falar_sync(self, texto: str) -> None:
        """Executa a síntese de voz de forma sincronizada (uso interno).

        Recria o engine a cada chamada. Isso contorna um problema conhecido
        do pyttsx3 em que, após o primeiro runAndWait(), chamadas seguintes
        não produzem som (o loop do engine fica travado). Recriar garante
        que a ARIA fale em todas as análises, não só na primeira.
        """
        with self._lock:
            try:
                import pyttsx3
                engine = pyttsx3.init()
                engine.setProperty("rate", self._taxa)
                engine.setProperty("volume", self._volume)
                # Reaplica voz em português se houver
                try:
                    for voz in engine.getProperty("voices"):
                        nome = (voz.name or "").lower()
                        ident = (voz.id or "").lower()
                        if any(t in nome or t in ident
                               for t in ["portug", "brazil", "brasil", "pt-br", "pt_br"]):
                            engine.setProperty("voice", voz.id)
                            break
                except Exception:
                    pass
                engine.say(texto)
                engine.runAndWait()
                try:
                    engine.stop()
                except Exception:
                    pass
            except Exception:
                pass  # falha de áudio não deve quebrar o app

    def alternar(self) -> bool:
        """Liga/desliga a fala da ARIA.

        Returns:
            True se a fala ficou habilitada, False se desabilitada.
        """
        self.habilitada = not self.habilitada
        return self.habilitada


# ════════════════════════════════════════════════════════════
#  GERAÇÃO DO RESUMO FALADO (1 FRASE — ESTILO JARVIS)
# ════════════════════════════════════════════════════════════

def gerar_resumo_falado(resultados: list[dict[str, Any]] | None) -> str:
    """Gera uma única frase de resumo para a ARIA falar após uma análise.

    A frase é curta e acionável, no estilo de um assistente de bordo:
    informa o estado geral da missão e a recomendação principal, sem
    repetir toda a análise detalhada que aparece no chat.

    Args:
        resultados: Lista de resultados de analisar_ciclo(), ou None.

    Returns:
        Frase única para ser falada pela ARIA.
    """
    if not resultados:
        return "Aguardando dados da missão para análise."

    n = len(resultados)
    criticos = [i + 1 for i, r in enumerate(resultados) if "CRITICA" in r["status"]]
    atencao = [i + 1 for i, r in enumerate(resultados) if "ATENCAO" in r["status"]]
    risco_medio = sum(r["pontuacao"] for r in resultados) / n

    # Identificar a área mais crítica para a recomendação
    if criticos:
        # Pega o ciclo mais crítico e identifica a pior métrica
        ciclo_pior = max(resultados, key=lambda r: r["pontuacao"])
        areas = ["temperatura", "comunicação", "energia", "oxigênio", "estabilidade"]
        acoes = {
            "temperatura":  "recomendo verificar o controle térmico",
            "comunicação":  "recomendo restabelecer contato com a base",
            "energia":      "recomendo ativar o modo de economia de energia",
            "oxigênio":     "recomendo acionar o protocolo de suporte à vida",
            "estabilidade": "recomendo reduzir operações não essenciais",
        }
        # Encontrar a primeira métrica crítica do pior ciclo
        area_critica = None
        for i, (status, _, _) in enumerate(ciclo_pior["classificacoes"]):
            if status == "CRITICO":
                area_critica = areas[i]
                break

        if len(criticos) >= 2:
            base = f"Atenção: {len(criticos)} ciclos em estado crítico."
        else:
            base = "Atenção: missão em estado crítico."

        if area_critica:
            return f"{base} {acoes[area_critica].capitalize()} imediatamente."
        return f"{base} Recomendo ativar o protocolo de contingência."

    if atencao:
        return ("Missão em estado de atenção. "
                "Recomendo monitoramento contínuo e medidas preventivas.")

    if risco_medio < 1:
        return "Todos os sistemas operando normalmente. Nenhuma ação necessária."

    return "Missão estável. Mantendo monitoramento de rotina."


def gerar_resumo_energia_falado(dados_energia: dict[str, Any]) -> str:
    """Gera uma frase de resumo falado sobre o estado energético.

    Args:
        dados_energia: Dicionário com o resumo energético da missão.

    Returns:
        Frase única para a ARIA falar sobre energia.
    """
    balanco = dados_energia.get("balanco_total_wh", 0)
    bat_min = dados_energia.get("bateria_minima_pct", 100)

    if balanco < 0 or bat_min < 20:
        return ("Alerta energético: balanço deficitário. "
                "Recomendo priorizar suporte à vida e desligar módulos não essenciais.")
    return "Balanço energético sustentável. Sistemas de energia sob controle."


# ════════════════════════════════════════════════════════════
#  TESTE STANDALONE
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Teste do módulo de voz da ARIA")
    print(f"pyttsx3 disponível: {_PYTTSX3_DISPONIVEL}")

    voz = VozARIA()
    print(f"Engine de voz operacional: {voz.disponivel}")

    # Testar geração de resumos
    resultado_critico = [{
        "valores": [40, 25, 17, 76, 32],
        "classificacoes": [
            ("CRITICO", 2, ""), ("CRITICO", 2, ""), ("CRITICO", 2, ""),
            ("CRITICO", 2, ""), ("CRITICO", 2, ""),
        ],
        "pontuacao": 10, "status": "MISSAO CRITICA",
    }]
    frase = gerar_resumo_falado(resultado_critico)
    print(f"\nResumo falado (crítico): '{frase}'")

    resultado_estavel = [{
        "valores": [22, 95, 92, 97, 91],
        "classificacoes": [("NORMAL", 0, "")] * 5,
        "pontuacao": 0, "status": "MISSAO ESTAVEL",
    }]
    frase2 = gerar_resumo_falado(resultado_estavel)
    print(f"Resumo falado (estável): '{frase2}'")

    if voz.disponivel:
        print("\nFalando o resumo crítico...")
        voz._falar_sync(frase)
        print("Concluído.")
    else:
        print("\n(Sem áudio neste ambiente — na sua máquina a ARIA falaria a frase.)")
