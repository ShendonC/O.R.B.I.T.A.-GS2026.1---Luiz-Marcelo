"""
============================================================
  O.R.B.I.T.A. — HUD (Heads-Up Display)
  Interface Gráfica — Mission Control AI
  Equipe: Aldebaran
============================================================
  Tecnologia: CustomTkinter (tema escuro cyberpunk/espacial)
  Arquitetura: UI completamente separada do backend.
    - mission_control.py → lógica de análise
    - energy_manager.py  → gestão energética
    - ai_copilot.py      → agente de IA
    - hud.py             → apenas apresentação e orquestração
  Threading: análise roda em thread separada para não travar a UI.
============================================================
"""

import threading
import time
import tkinter as tk
from typing import Any

import customtkinter as ctk

# ── Backend imports ───────────────────────────────────────
from mission_control import (
    carregar_telemetria,
    construir_matriz_de_json,
    analisar_ciclo,
    avaliar_alerta_booleano,
    analisar_tendencia,
    identificar_area_mais_afetada,
    classificar_ciclo,
    verificacao_automatica,
    ARQUIVO_TELEMETRIA,
    NOME_MISSAO,
    NOME_EQUIPE,
    areas_monitoradas,
    dados_missao as DADOS_PADRAO,
    nomes_ciclos as NOMES_PADRAO,
)
from energy_manager import GerenciadorEnergia
from ai_copilot import consultar_agente, consultar_agente_energia, conversar_com_aria
from voice import (
    VozARIA,
    gerar_resumo_falado,
    gerar_resumo_energia_falado,
)

# ── Tema global ───────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ── Paleta cyberpunk O.R.B.I.T.A. ────────────────────────
COR_BG_ESCURO   = "#0A0E1A"   # fundo principal
COR_BG_CARD     = "#111827"   # cards/painéis
COR_BG_BORDA    = "#1E293B"   # bordas sutis
COR_CYAN        = "#00D4FF"   # cor primária ciano
COR_MAGENTA     = "#C026D3"   # ARIA / IA
COR_VERDE       = "#10B981"   # NORMAL
COR_AMARELO     = "#F59E0B"   # ATENÇÃO
COR_VERMELHO    = "#EF4444"   # CRÍTICO
COR_BRANCO      = "#F1F5F9"   # texto principal
COR_CINZA       = "#64748B"   # texto secundário
COR_AZUL_ESC    = "#0F172A"   # fundo gauges

FONTE_TITULO    = ("Courier New", 13, "bold")
FONTE_SUBTITULO = ("Courier New", 10)
FONTE_MONO      = ("Courier New", 11)
FONTE_MONO_SM   = ("Courier New", 9)
FONTE_GAUGE     = ("Courier New", 18, "bold")
FONTE_GAUGE_SM  = ("Courier New", 10)
FONTE_HEADER    = ("Courier New", 20, "bold")
FONTE_BOTAO     = ("Courier New", 12, "bold")


# ════════════════════════════════════════════════════════════
#  COMPONENTES CUSTOMIZADOS
# ════════════════════════════════════════════════════════════

class GaugeWidget(ctk.CTkFrame):
    """Gauge circular simples desenhado em Canvas para cada métrica.

    Exibe valor numérico, rótulo, barra de arco colorida e status.
    """

    def __init__(self, master: Any, label: str, unidade: str = "%",
                 min_val: float = 0, max_val: float = 100, **kwargs) -> None:
        super().__init__(master, fg_color=COR_BG_CARD,
                         corner_radius=12, **kwargs)

        self.label    = label
        self.unidade  = unidade
        self.min_val  = min_val
        self.max_val  = max_val
        self._valor   = 0.0
        self._status  = "NORMAL"

        SIZE = 110

        self.canvas = tk.Canvas(self, width=SIZE, height=SIZE,
                                bg=COR_BG_CARD, highlightthickness=0)
        self.canvas.pack(pady=(10, 2))

        self.lbl_nome = ctk.CTkLabel(self, text=label.upper(),
                                     font=FONTE_GAUGE_SM, text_color=COR_CINZA)
        self.lbl_nome.pack()

        self.lbl_status = ctk.CTkLabel(self, text="NORMAL",
                                       font=FONTE_GAUGE_SM, text_color=COR_VERDE)
        self.lbl_status.pack(pady=(0, 8))

        self._SIZE = SIZE
        self._desenhar(0)

    def _cor_status(self, status: str) -> str:
        return {
            "CRITICO": COR_VERMELHO,
            "ATENCAO": COR_AMARELO,
        }.get(status, COR_VERDE)

    def _desenhar(self, valor: float) -> None:
        s = self._SIZE
        pad = 12
        c = self.canvas
        c.delete("all")

        # Arco de fundo
        c.create_arc(pad, pad, s - pad, s - pad,
                     start=220, extent=-260,
                     style="arc", outline=COR_BG_BORDA, width=8)

        # Arco de valor
        pct = max(0.0, min(1.0, (valor - self.min_val) / (self.max_val - self.min_val)))
        extent = -260 * pct
        cor = self._cor_status(self._status)
        if extent != 0:
            c.create_arc(pad, pad, s - pad, s - pad,
                         start=220, extent=extent,
                         style="arc", outline=cor, width=8)

        # Valor central
        fmt = f"{valor:.0f}" if self.unidade == "%" else f"{valor:.1f}"
        c.create_text(s // 2, s // 2 - 4,
                      text=fmt, fill=COR_BRANCO,
                      font=("Courier New", 16, "bold"))
        c.create_text(s // 2, s // 2 + 14,
                      text=self.unidade, fill=COR_CINZA,
                      font=("Courier New", 9))

    def atualizar(self, valor: float, status: str) -> None:
        """Atualiza o gauge com novo valor e status."""
        self._valor  = valor
        self._status = status
        cor = self._cor_status(status)
        self._desenhar(valor)
        self.lbl_status.configure(text=status, text_color=cor)


class LogPanel(ctk.CTkFrame):
    """Painel de log rolável com formatação por severidade."""

    def __init__(self, master: Any, titulo: str, **kwargs) -> None:
        super().__init__(master, fg_color=COR_BG_CARD,
                         corner_radius=12, **kwargs)

        ctk.CTkLabel(self, text=f"◈ {titulo}",
                     font=FONTE_TITULO, text_color=COR_CYAN).pack(
            anchor="w", padx=14, pady=(10, 4))

        self.text = tk.Text(
            self, bg=COR_AZUL_ESC, fg=COR_BRANCO,
            font=FONTE_MONO_SM, relief="flat",
            padx=10, pady=8, wrap="word",
            state="disabled", cursor="arrow",
        )
        self.text.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # Tags de cor
        self.text.tag_config("normal",   foreground=COR_VERDE)
        self.text.tag_config("atencao",  foreground=COR_AMARELO)
        self.text.tag_config("critico",  foreground=COR_VERMELHO)
        self.text.tag_config("aria",     foreground=COR_MAGENTA)
        self.text.tag_config("header",   foreground=COR_CYAN)
        self.text.tag_config("dim",      foreground=COR_CINZA)
        self.text.tag_config("branco",   foreground=COR_BRANCO)

    def escrever(self, texto: str, tag: str = "branco") -> None:
        """Adiciona linha ao log com a tag de cor indicada."""
        self.text.configure(state="normal")
        self.text.insert("end", texto + "\n", tag)
        self.text.see("end")
        self.text.configure(state="disabled")

    def escrever_animado(self, texto: str, tag: str = "branco",
                         delay_ms: int = 12) -> None:
        """Escreve o texto caractere por caractere (efeito de digitação).

        Roda de forma síncrona dentro da thread chamadora usando update()
        para forçar o render a cada caractere. Use em threads de trabalho,
        nunca na thread principal da UI (travaria).

        Args:
            texto:    Linha a ser escrita.
            tag:      Tag de cor.
            delay_ms: Atraso entre caracteres em milissegundos.
        """
        self.text.configure(state="normal")
        for ch in texto:
            self.text.insert("end", ch, tag)
            self.text.see("end")
            self.text.update_idletasks()
            time.sleep(delay_ms / 1000.0)
        self.text.insert("end", "\n", tag)
        self.text.see("end")
        self.text.configure(state="disabled")

    def limpar(self) -> None:
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")


# ════════════════════════════════════════════════════════════
#  JANELA PRINCIPAL
# ════════════════════════════════════════════════════════════

class OrbitalHUD(ctk.CTk):
    """Janela principal da HUD do O.R.B.I.T.A.

    Layout:
      ┌─ Header (título + status geral) ──────────────────┐
      ├─ Gauges (5 métricas) ──────────────────────────────┤
      ├─ [Log de Missão] │ [Painel ARIA] ─────────────────┤
      ├─ Barra de energia ─────────────────────────────────┤
      └─ Botões de controle ───────────────────────────────┘
    """

    def __init__(self) -> None:
        super().__init__()

        self.title(f"O.R.B.I.T.A. — Mission Control AI | Equipe {NOME_EQUIPE}")
        self.geometry("1240x900")
        self.minsize(1180, 800)
        self.configure(fg_color=COR_BG_ESCURO)

        # Estado interno
        self._resultados:  list[dict] = []
        self._alertas:     list[dict] = []
        self._analisando:  bool = False
        self._dados_missao: list[list[int]] = list(DADOS_PADRAO)
        self._nomes_ciclos: list[str] = list(NOMES_PADRAO)

        # Motor de voz da ARIA (degrada graciosamente se não houver áudio)
        self._voz = VozARIA()

        self._construir_ui()
        self._status_tick()

    # ── Construção da UI ──────────────────────────────────

    def _construir_ui(self) -> None:
        """Monta todos os widgets da HUD."""
        self._construir_header()
        self._construir_gauges()
        self._construir_botoes()    # ancora no fundo primeiro
        self._construir_energia()   # ancora no fundo
        self._construir_paineis()   # ocupa o espaço restante

    def _construir_header(self) -> None:
        frame = ctk.CTkFrame(self, fg_color=COR_BG_CARD,
                             corner_radius=0, height=64)
        frame.pack(fill="x", pady=(0, 2))
        frame.pack_propagate(False)

        # Logo e título
        left = ctk.CTkFrame(frame, fg_color="transparent")
        left.pack(side="left", padx=18, pady=10)

        ctk.CTkLabel(left, text="[ O.R.B.I.T.A. ]",
                     font=FONTE_HEADER, text_color=COR_CYAN).pack(anchor="w")
        ctk.CTkLabel(left, text="Operational Risk & Balance Intelligence via Technique Analysis",
                     font=FONTE_MONO_SM, text_color=COR_CINZA).pack(anchor="w")

        # Status geral (direita)
        right = ctk.CTkFrame(frame, fg_color="transparent")
        right.pack(side="right", padx=18)

        ctk.CTkLabel(right, text="EQUIPE", font=FONTE_GAUGE_SM,
                     text_color=COR_CINZA).pack(anchor="e")
        ctk.CTkLabel(right, text=NOME_EQUIPE.upper(), font=FONTE_TITULO,
                     text_color=COR_CYAN).pack(anchor="e")

        # Status badge (centro-direita)
        center = ctk.CTkFrame(frame, fg_color="transparent")
        center.pack(side="right", padx=30)

        ctk.CTkLabel(center, text="STATUS DA MISSÃO",
                     font=FONTE_GAUGE_SM, text_color=COR_CINZA).pack()
        self.lbl_status_geral = ctk.CTkLabel(
            center, text="AGUARDANDO ANÁLISE",
            font=("Courier New", 14, "bold"), text_color=COR_CINZA)
        self.lbl_status_geral.pack()

    def _construir_gauges(self) -> None:
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="x", padx=12, pady=(4, 4))

        configs = [
            ("Temperatura", "°C", 0,  50),
            ("Comunicação", "%",  0, 100),
            ("Bateria",     "%",  0, 100),
            ("Oxigênio",    "%",  0, 100),
            ("Estabilidade","%",  0, 100),
        ]

        self.gauges: list[GaugeWidget] = []
        for i, (lbl, unit, mn, mx) in enumerate(configs):
            g = GaugeWidget(frame, label=lbl, unidade=unit,
                            min_val=mn, max_val=mx)
            g.grid(row=0, column=i, padx=5, pady=4, sticky="nsew")
            frame.columnconfigure(i, weight=1)
            self.gauges.append(g)

        # Indicador de ciclo atual
        self.lbl_ciclo = ctk.CTkLabel(
            frame, text="─  CICLO: –  ─",
            font=FONTE_MONO, text_color=COR_CINZA)
        self.lbl_ciclo.grid(row=1, column=0, columnspan=5, pady=(0, 2))

    def _construir_paineis(self) -> None:
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=12, pady=2)
        frame.columnconfigure(0, weight=3)
        frame.columnconfigure(1, weight=2)
        frame.rowconfigure(0, weight=1)

        # Log de missão (esquerda)
        self.log_missao = LogPanel(frame, titulo="LOG DA MISSÃO")
        self.log_missao.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        # Coluna direita: painel ARIA + campo de mensagem
        col_aria = ctk.CTkFrame(frame, fg_color="transparent")
        col_aria.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        col_aria.rowconfigure(0, weight=1)
        col_aria.columnconfigure(0, weight=1)

        self.log_aria = LogPanel(col_aria, titulo="ARIA — AGENTE COGNITIVO")
        self.log_aria.grid(row=0, column=0, sticky="nsew")

        # Campo de mensagem para conversar com a ARIA
        barra_msg = ctk.CTkFrame(col_aria, fg_color=COR_BG_CARD, corner_radius=10)
        barra_msg.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        barra_msg.columnconfigure(0, weight=1)

        self.entrada_msg = ctk.CTkEntry(
            barra_msg, font=FONTE_MONO,
            placeholder_text="Pergunte algo à ARIA...",
            fg_color=COR_AZUL_ESC, border_color=COR_MAGENTA, border_width=1,
            height=40)
        self.entrada_msg.grid(row=0, column=0, sticky="ew", padx=(8, 6), pady=8)
        self.entrada_msg.bind("<Return>", lambda _e: self._enviar_mensagem_aria())

        self.btn_enviar = ctk.CTkButton(
            barra_msg, text="➤ ENVIAR", command=self._enviar_mensagem_aria,
            font=FONTE_BOTAO, fg_color="transparent",
            border_color=COR_MAGENTA, border_width=2, text_color=COR_MAGENTA,
            hover_color=COR_BG_BORDA, width=110, height=40, corner_radius=8,
            anchor="center")
        self.btn_enviar.grid(row=0, column=1, padx=(0, 8), pady=8)

        self.log_aria.escrever(
            "ARIA inicializada. Aguardando dados críticos...", "dim")
        self.log_aria.escrever(
            "Sistema de análise preditiva em standby.", "dim")
        self.log_aria.escrever(
            "Digite uma mensagem abaixo para conversar comigo.", "dim")

    def _enviar_mensagem_aria(self) -> None:
        """Envia a pergunta do operador para a ARIA em thread separada."""
        pergunta = self.entrada_msg.get().strip()
        if not pergunta:
            return
        self.entrada_msg.delete(0, "end")
        self.log_aria.escrever(f"\n▸ VOCÊ: {pergunta}", "header")
        self.log_aria.escrever("  ARIA está pensando...", "dim")
        self.btn_enviar.configure(state="disabled")

        t = threading.Thread(
            target=self._mensagem_aria_thread, args=(pergunta,), daemon=True)
        t.start()

    def _mensagem_aria_thread(self, pergunta: str) -> None:
        """Thread que consulta a ARIA e exibe a resposta no painel."""
        resposta, origem = conversar_com_aria(pergunta, self._resultados or None)
        self.after(0, self._exibir_resposta_chat, resposta, origem)

    def _exibir_resposta_chat(self, resposta: str, origem: str = "ia") -> None:
        """Exibe a resposta da conversa no painel ARIA.

        Args:
            resposta: Texto da resposta da ARIA.
            origem:   "ia" se veio do modelo real, "mock" se foi resposta local.
        """
        # Indicador da origem da resposta
        if origem == "ia":
            self.log_aria.escrever("  [IA] resposta do modelo online", "dim")
        else:
            self.log_aria.escrever("  [LOCAL] resposta sem IA (verifique o .env)", "dim")

        for linha in resposta.strip().split("\n"):
            linha = linha.strip()
            if not linha:
                self.log_aria.escrever("", "branco")
            elif linha.startswith("**") and linha.endswith("**"):
                self.log_aria.escrever("  " + linha.replace("**", ""), "aria")
            else:
                self.log_aria.escrever("  " + linha, "branco")
        self.btn_enviar.configure(state="normal")

    def _construir_energia(self) -> None:
        frame = ctk.CTkFrame(self, fg_color=COR_BG_CARD,
                             corner_radius=10, height=52)
        frame.pack(fill="x", side="bottom", padx=12, pady=4)
        frame.pack_propagate(False)

        ctk.CTkLabel(frame, text="⚡ ENERGIA",
                     font=FONTE_TITULO, text_color=COR_AMARELO).pack(
            side="left", padx=14)

        # Barra de bateria
        self.barra_bat = ctk.CTkProgressBar(
            frame, width=300, height=16,
            progress_color=COR_VERDE, fg_color=COR_BG_BORDA)
        self.barra_bat.pack(side="left", padx=10, pady=16)
        self.barra_bat.set(0.92)

        self.lbl_bat_pct = ctk.CTkLabel(
            frame, text="92%", font=FONTE_TITULO, text_color=COR_VERDE)
        self.lbl_bat_pct.pack(side="left")

        # Balanço energético
        self.lbl_balanco = ctk.CTkLabel(
            frame, text="Balanço: —  |  Painéis: 4 ativos  |  Módulos extras: ONLINE",
            font=FONTE_MONO_SM, text_color=COR_CINZA)
        self.lbl_balanco.pack(side="left", padx=20)

        # X=1 indicator
        self.lbl_x1 = ctk.CTkLabel(
            frame, text="X = 0  (sem alerta)",
            font=FONTE_TITULO, text_color=COR_VERDE)
        self.lbl_x1.pack(side="right", padx=14)

    def _construir_botoes(self) -> None:
        frame = ctk.CTkFrame(self, fg_color=COR_BG_CARD,
                             corner_radius=0, height=132)
        frame.pack(fill="x", side="bottom", pady=(2, 0))
        frame.pack_propagate(False)

        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.pack(expand=True)

        # Fileira 1 — gestão de dados
        linha1 = ctk.CTkFrame(inner, fg_color="transparent")
        linha1.pack(pady=(2, 0))
        botoes_dados = [
            ("＋  INSERIR / SIMULAR",   self._inserir_dados,      COR_BRANCO),
            ("◷  VISUALIZAR STATUS",    self._visualizar_status,  COR_BRANCO),
            ("≣  HISTÓRICO",            self._mostrar_historico,  COR_BRANCO),
        ]
        for texto, cmd, cor_fg in botoes_dados:
            ctk.CTkButton(
                linha1, text=texto, command=cmd,
                font=FONTE_BOTAO,
                fg_color="transparent",
                border_color=COR_CINZA, border_width=2,
                text_color=cor_fg,
                hover_color=COR_BG_BORDA,
                width=200, height=44, corner_radius=8,
                anchor="center",
            ).pack(side="left", padx=9, pady=8)

        # Botão de alternar voz da ARIA
        self.btn_voz = ctk.CTkButton(
            linha1, text="🔊  VOZ: ON", command=self._alternar_voz,
            font=FONTE_BOTAO, fg_color="transparent",
            border_color=COR_MAGENTA, border_width=2, text_color=COR_MAGENTA,
            hover_color=COR_BG_BORDA, width=160, height=44, corner_radius=8,
            anchor="center")
        self.btn_voz.pack(side="left", padx=9, pady=8)

        # Fileira 2 — análise e ações principais
        linha2 = ctk.CTkFrame(inner, fg_color="transparent")
        linha2.pack(pady=(0, 2))
        botoes_acao = [
            ("▶  EXECUTAR ANÁLISE",   self._executar_analise, COR_CYAN),
            ("⚡  ANÁLISE ENERGÉTICA", self._analise_energia,  COR_AMARELO),
            ("◈  CONSULTAR ARIA",      self._consultar_aria,   COR_MAGENTA),
            ("📋  RELATÓRIO FINAL",    self._relatorio_final,  COR_VERDE),
            ("✕  ENCERRAR",            self.destroy,           COR_VERMELHO),
        ]
        for texto, cmd, cor_fg in botoes_acao:
            ctk.CTkButton(
                linha2, text=texto, command=cmd,
                font=FONTE_BOTAO,
                fg_color="transparent",
                border_color=cor_fg, border_width=2,
                text_color=cor_fg,
                hover_color=COR_BG_BORDA,
                width=210, height=44, corner_radius=8,
                anchor="center",
            ).pack(side="left", padx=9, pady=8)

    # ── Animação de status ────────────────────────────────

    def _status_tick(self) -> None:
        """Pisca o cursor no header para efeito terminal."""
        atual = self.lbl_status_geral.cget("text")
        if "AGUARDANDO" in atual:
            pass  # estático enquanto aguarda
        self.after(800, self._status_tick)

    # ── Ações dos botões ──────────────────────────────────

    def _executar_analise(self) -> None:
        """Roda análise completa em thread separada para não travar UI."""
        if self._analisando:
            return
        self._analisando = True
        self.log_missao.limpar()
        self.log_missao.escrever("═" * 54, "header")
        self.log_missao.escrever(f"  INICIANDO ANÁLISE — MISSÃO {NOME_MISSAO}", "header")
        self.log_missao.escrever("═" * 54, "header")
        t = threading.Thread(target=self._analise_thread, daemon=True)
        t.start()

    def _analise_thread(self) -> None:
        """Thread de análise — executa no background."""
        try:
            # Tentar carregar JSON
            ciclos_json = carregar_telemetria(ARQUIVO_TELEMETRIA)
            if ciclos_json:
                self._dados_missao = construir_matriz_de_json(ciclos_json)
                self._nomes_ciclos = [c.get("nome", f"Ciclo {c['id']}") for c in ciclos_json]

            resultados: list[dict] = []
            alertas:    list[dict] = []

            for i, ciclo in enumerate(self._dados_missao):
                nome = self._nomes_ciclos[i] if i < len(self._nomes_ciclos) else f"Ciclo {i+1}"

                resultado = analisar_ciclo(ciclo)
                alerta    = avaliar_alerta_booleano(ciclo)
                resultados.append(resultado)
                alertas.append(alerta)

                # Atualizar gauges/labels na thread principal (rápido)
                self.after(0, self._atualizar_ciclo_ui,
                           i, nome, ciclo, resultado, alerta)
                time.sleep(0.4)  # deixa os gauges atualizarem antes do log

                # Escrever o log do ciclo com animação de digitação (nesta thread)
                self._escrever_log_ciclo(i, nome, ciclo, resultado, alerta)

                time.sleep(1.3)  # pausa entre ciclos para o operador ler com calma

            self._resultados = resultados
            self._alertas    = alertas
            self.after(0, self._pos_analise)

        except Exception as e:
            self.after(0, self.log_missao.escrever,
                       f"ERRO: {e}", "critico")
        finally:
            self._analisando = False

    def _atualizar_ciclo_ui(self, idx: int, nome: str,
                             ciclo: list[int],
                             resultado: dict, alerta: dict) -> None:
        """Atualiza gauges e log para o ciclo recém-analisado."""
        temp, comm, bat, o2, estab = ciclo
        classifs = resultado["classificacoes"]

        # Gauges
        valores_gauge = [temp, comm, bat, o2, estab]
        for j, gauge in enumerate(self.gauges):
            st = classifs[j][0]
            gauge.atualizar(valores_gauge[j], st)

        # Label ciclo
        self.lbl_ciclo.configure(
            text=f"─  CICLO {idx + 1}: {nome.upper()}  ─",
            text_color=COR_CYAN)

        # Status geral
        status_txt  = resultado["status"]
        cor_status  = (COR_VERMELHO if "CRITICA" in status_txt
                       else COR_AMARELO if "ATENCAO" in status_txt
                       else COR_VERDE)
        self.lbl_status_geral.configure(
            text=status_txt, text_color=cor_status)

        # X=1
        x_val = alerta["X"]
        self.lbl_x1.configure(
            text=f"X = {x_val}  {'⚠ ALERTA ATIVO' if x_val else '(sem alerta)'}",
            text_color=COR_VERMELHO if x_val else COR_VERDE)

        # Bateria
        bat_pct = bat / 100
        bat_cor = (COR_VERMELHO if bat < 20
                   else COR_AMARELO if bat < 35
                   else COR_VERDE)
        self.barra_bat.configure(progress_color=bat_cor)
        self.barra_bat.set(bat_pct)
        self.lbl_bat_pct.configure(text=f"{bat}%", text_color=bat_cor)

    def _escrever_log_ciclo(self, idx: int, nome: str, ciclo: list[int],
                            resultado: dict, alerta: dict) -> None:
        """Escreve o log de um ciclo com animação de digitação.

        Roda na thread de análise (não na principal), usando escrever_animado
        para o efeito de texto sendo digitado em tempo real.
        """
        temp, comm, bat, o2, estab = ciclo
        classifs = resultado["classificacoes"]
        status_map = {"NORMAL": "normal", "ATENCAO": "atencao", "CRITICO": "critico"}
        valores_gauge = [temp, comm, bat, o2, estab]
        status_txt = resultado["status"]
        x_val = alerta["X"]

        tag_ciclo = status_map.get(
            "CRITICO" if "CRITICA" in status_txt
            else "ATENCAO" if "ATENCAO" in status_txt
            else "NORMAL", "normal")

        # Cabeçalho do ciclo (animado)
        self.log_missao.escrever_animado(f"\n▸ CICLO {idx+1} — {nome}", "header", delay_ms=8)

        # Cada métrica digitada linha a linha
        labels_log = ["Temperatura", "Comunicação", "Bateria", "Oxigênio", "Estabilidade"]
        unids_log  = ["°C", "%", "%", "%", "%"]
        for j in range(5):
            st, pts, msg = classifs[j]
            tag = status_map.get(st, "normal")
            linha = (f"  {labels_log[j]:12}: {valores_gauge[j]:>3}{unids_log[j]}"
                     f"  [{st:^8}]  {msg}")
            self.log_missao.escrever_animado(linha, tag, delay_ms=10)
            time.sleep(0.25)  # pequena pausa entre métricas

        vars_str = "  ".join(f"{k}={v}" for k, v in alerta["variaveis"].items())
        self.log_missao.escrever(f"  Lógica: {vars_str}  →  X={x_val}", "dim")
        self.log_missao.escrever(
            f"  Pontuação: {resultado['pontuacao']}/10  |  {status_txt}", tag_ciclo)
        self.log_missao.escrever(f"  {resultado['recomendacao']}", "atencao")

    def _pos_analise(self) -> None:
        """Chamado após todos os ciclos serem analisados."""
        self.log_missao.escrever("\n" + "═" * 54, "header")
        self.log_missao.escrever("  ANÁLISE CONCLUÍDA", "header")
        self.log_missao.escrever("═" * 54, "header")

        tendencia = analisar_tendencia(self._resultados)
        area, acum = identificar_area_mais_afetada(self._resultados)
        self.log_missao.escrever(f"\n  Tendência: {tendencia}", "branco")
        self.log_missao.escrever(f"  Área mais afetada: {area}", "atencao")

        # Gerar o resumo de 1 frase (será falado ao fim do processamento ARIA)
        resumo_voz = gerar_resumo_falado(self._resultados)

        # Trigger ARIA para críticos automaticamente
        criticos = [(i, r) for i, r in enumerate(self._resultados)
                    if "CRITICA" in r["status"]]
        if criticos:
            self.log_missao.escrever(
                f"\n  {len(criticos)} ciclo(s) crítico(s) → ativando ARIA...",
                "critico")
            t = threading.Thread(
                target=self._aria_auto_thread, args=(criticos, resumo_voz), daemon=True)
            t.start()
        else:
            # Sem críticos: fala o resumo direto no painel
            self._falar_resumo(resumo_voz)

    def _falar_resumo(self, frase: str) -> None:
        """Exibe e fala um resumo de 1 frase da ARIA (estilo Jarvis).

        Mostra a frase no painel da ARIA com destaque de voz e a
        envia ao motor de TTS (que fala em thread separada).

        Args:
            frase: Frase única de resumo a ser falada.
        """
        self.log_aria.escrever(f"\n🔊 ARIA (voz): {frase}", "aria")
        self._voz.falar(frase)

    def _alternar_voz(self) -> None:
        """Liga/desliga a voz da ARIA e atualiza o botão."""
        ligada = self._voz.alternar()
        if not self._voz.disponivel:
            self.btn_voz.configure(text="🔇 SEM ÁUDIO", text_color=COR_CINZA)
            self.log_aria.escrever(
                "\n(Voz indisponível neste sistema — instale o motor de áudio.)", "dim")
            return
        self.btn_voz.configure(
            text="🔊  VOZ: ON" if ligada else "🔇  VOZ: OFF",
            text_color=COR_MAGENTA if ligada else COR_CINZA)

    def _aria_auto_thread(self, criticos: list, resumo_voz: str = "") -> None:
        """Processa ciclos críticos e envia para o painel ARIA.

        Args:
            criticos:   Lista de (índice, resultado) dos ciclos críticos.
            resumo_voz: Frase de resumo a ser falada ao final (estilo Jarvis).
        """
        self.after(0, self.log_aria.limpar)
        self.after(0, self.log_aria.escrever,
                   "◈ ARIA ATIVADA — ANALISANDO CICLOS CRÍTICOS", "header")
        self.after(0, self.log_aria.escrever, "─" * 44, "dim")

        for idx, resultado in criticos:
            nome = (self._nomes_ciclos[idx]
                    if idx < len(self._nomes_ciclos)
                    else f"Ciclo {idx+1}")

            self.after(0, self.log_aria.escrever,
                       f"\n▸ CICLO {idx+1} — {nome.upper()}", "aria")
            self.after(0, self.log_aria.escrever,
                       f"  Pontuação: {resultado['pontuacao']}/10", "critico")

            resposta = consultar_agente(
                idx + 1, nome, resultado, exibir_no_terminal=False)

            self.after(0, self._exibir_resposta_aria, resposta)
            time.sleep(1.5)

        self.after(0, self.log_aria.escrever,
                   "\n" + "─" * 44, "dim")
        self.after(0, self.log_aria.escrever,
                   "ARIA: análise concluída.", "aria")

        # Falar o resumo de 1 frase ao final (após todo o processamento)
        if resumo_voz:
            self.after(0, self._falar_resumo, resumo_voz)

    def _exibir_resposta_aria(self, resposta: str) -> None:
        """Exibe resposta da ARIA no painel com formatação."""
        for linha in resposta.strip().split("\n"):
            linha = linha.strip()
            if not linha:
                self.log_aria.escrever("", "branco")
                continue
            if linha.startswith("**") and linha.endswith("**"):
                self.log_aria.escrever(
                    "  " + linha.replace("**", "").upper(), "aria")
            elif linha[0].isdigit() and ". " in linha[:4]:
                self.log_aria.escrever("  " + linha, "atencao")
            else:
                self.log_aria.escrever("  " + linha, "branco")

    def _analise_energia(self) -> None:
        """Executa análise energética e exibe no log."""
        if not self._dados_missao:
            self.log_missao.escrever("Execute a análise primeiro.", "atencao")
            return

        self.log_missao.escrever("\n" + "═" * 54, "header")
        self.log_missao.escrever("  ANÁLISE ENERGÉTICA — PAINÉIS & BATERIA", "header")
        self.log_missao.escrever("═" * 54, "header")

        bat_ini = self._dados_missao[0][2]
        ger = GerenciadorEnergia(bat_ini)

        total_gerado    = 0.0
        total_consumido = 0.0

        for i, ciclo in enumerate(self._dados_missao):
            temp = ciclo[0]
            bat  = ciclo[2]
            res  = ger.processar_ciclo(i + 1, bat, temp)

            total_gerado    += res["energia_gerada_wh"]
            total_consumido += res["energia_consumida_wh"]

            bat_pct = res["bateria_atual_pct"]
            tag = ("critico" if bat_pct < 20
                   else "atencao" if bat_pct < 35
                   else "normal")

            self.log_missao.escrever(
                f"\n  ⚡ Ciclo {i+1}: Bat={bat_pct}%  "
                f"Gerado={res['energia_gerada_wh']:.0f}Wh  "
                f"Consumido={res['energia_consumida_wh']:.0f}Wh  "
                f"Balanço={res['balanco_wh']:+.0f}Wh", tag)

            for acao in res["acoes_automaticas"]:
                acao_limpa = acao
                for code in ["\033[0m","\033[1m","\033[91m","\033[92m",
                              "\033[93m","\033[95m","\033[96m","\033[97m",
                              "\033[2m","\033[31m"]:
                    acao_limpa = acao_limpa.replace(code, "")
                tag_acao = ("critico" if "CRÍTICA" in acao_limpa
                            else "atencao" if "ALERTA" in acao_limpa
                            else "normal")
                self.log_missao.escrever(f"    {acao_limpa.strip()}", tag_acao)

        balanco_total = total_gerado - total_consumido
        sinal = "+" if balanco_total >= 0 else ""
        tag_bal = "normal" if balanco_total >= 0 else "critico"

        self.log_missao.escrever("\n  ─" * 27, "dim")
        self.log_missao.escrever(
            f"  Total gerado   : {total_gerado:.0f} Wh", "normal")
        self.log_missao.escrever(
            f"  Total consumido: {total_consumido:.0f} Wh", "atencao")
        self.log_missao.escrever(
            f"  Balanço final  : {sinal}{balanco_total:.0f} Wh", tag_bal)

        # Atualizar barra de energia com último ciclo
        ultimo_bat = self._dados_missao[-1][2]
        bat_cor = (COR_VERMELHO if ultimo_bat < 20
                   else COR_AMARELO if ultimo_bat < 35
                   else COR_VERDE)
        self.barra_bat.configure(progress_color=bat_cor)
        self.barra_bat.set(ultimo_bat / 100)
        self.lbl_bat_pct.configure(text=f"{ultimo_bat}%", text_color=bat_cor)
        self.lbl_balanco.configure(
            text=f"Balanço: {sinal}{balanco_total:.0f}Wh  |  "
                 f"Painéis: {ger.paineis_ativos} ativos  |  "
                 f"Módulos extras: {'ONLINE' if ger.modulos_extras_on else 'OFFLINE'}")

        # Acionar ARIA para comentar o contexto energético
        bateria_minima = min(c[2] for c in self._dados_missao)
        ciclos_economia = sum(1 for r in ger.historico if not r["modulos_extras_on"])
        dados_energia = {
            "missao":              NOME_MISSAO,
            "total_gerado_wh":     round(total_gerado, 1),
            "total_consumido_wh":  round(total_consumido, 1),
            "balanco_total_wh":    round(balanco_total, 1),
            "bateria_minima_pct":  bateria_minima,
            "ciclos_em_economia":  ciclos_economia,
            "paineis_ativos":      ger.paineis_ativos,
        }
        t = threading.Thread(
            target=self._aria_energia_thread, args=(dados_energia,), daemon=True)
        t.start()

    def _aria_energia_thread(self, dados_energia: dict) -> None:
        """Consulta a ARIA sobre o balanço energético e exibe no painel."""
        self.after(0, self.log_aria.limpar)
        self.after(0, self.log_aria.escrever,
                   "◈ ARIA — ANÁLISE ENERGÉTICA", "header")
        self.after(0, self.log_aria.escrever, "─" * 44, "dim")
        self.after(0, self.log_aria.escrever,
                   f"Balanço: {dados_energia['balanco_total_wh']:+.0f} Wh  |  "
                   f"Bateria mín: {dados_energia['bateria_minima_pct']}%", "atencao")

        resposta = consultar_agente_energia(dados_energia, exibir_no_terminal=False)
        self.after(0, self._exibir_resposta_aria, resposta)
        self.after(0, self.log_aria.escrever, "\n" + "─" * 44, "dim")
        self.after(0, self.log_aria.escrever, "ARIA: análise energética concluída.", "aria")

        # ARIA fala um resumo de 1 frase sobre energia
        resumo_voz = gerar_resumo_energia_falado(dados_energia)
        self.after(0, self._falar_resumo, resumo_voz)

    def _consultar_aria(self) -> None:
        """Consulta ARIA manualmente para todos os ciclos críticos."""
        if not self._resultados:
            self.log_aria.escrever(
                "Execute a análise primeiro (▶ EXECUTAR ANÁLISE).", "atencao")
            return
        criticos = [(i, r) for i, r in enumerate(self._resultados)
                    if "CRITICA" in r["status"]]
        if not criticos:
            self.log_aria.limpar()
            self.log_aria.escrever(
                "Nenhum ciclo crítico detectado. ARIA em standby.", "normal")
            resumo = gerar_resumo_falado(self._resultados)
            self._falar_resumo(resumo)
            return
        resumo_voz = gerar_resumo_falado(self._resultados)
        t = threading.Thread(
            target=self._aria_auto_thread, args=(criticos, resumo_voz), daemon=True)
        t.start()

    def _visualizar_status(self) -> None:
        """Exibe resumo compacto do status de cada ciclo no log."""
        if not self._resultados:
            self.log_missao.escrever(
                "\nExecute a análise primeiro (▶ EXECUTAR ANÁLISE).", "atencao")
            return

        self.log_missao.escrever("\n" + "═" * 54, "header")
        self.log_missao.escrever(
            f"  STATUS ATUAL — {len(self._resultados)} ciclos monitorados", "header")
        self.log_missao.escrever("═" * 54, "header")

        for i, (r, a) in enumerate(zip(self._resultados, self._alertas)):
            status = r["status"]
            tag = ("critico" if "CRITICA" in status
                   else "atencao" if "ATENCAO" in status
                   else "normal")
            x_marca = "⚠" if a["X"] else "·"
            self.log_missao.escrever(
                f"  Ciclo {i+1:>2} | Risco {r['pontuacao']:>2}/10 | "
                f"{status:<18} | X={a['X']} {x_marca}", tag)
        self.log_missao.escrever("")

    def _mostrar_historico(self) -> None:
        """Exibe a tabela bruta de todas as leituras da missão no log."""
        self.log_missao.escrever("\n" + "═" * 54, "header")
        self.log_missao.escrever("  HISTÓRICO DE LEITURAS", "header")
        self.log_missao.escrever("═" * 54, "header")
        self.log_missao.escrever(
            f"  {'Ciclo':<7}{'Temp':>6}{'Comm':>7}{'Bat':>6}{'O2':>6}{'Estab':>7}", "dim")
        self.log_missao.escrever("  " + "─" * 50, "dim")

        for i, linha in enumerate(self._dados_missao):
            t, c, b, o, e = linha
            self.log_missao.escrever(
                f"  {i+1:<7}{t:>5}°{c:>6}%{b:>5}%{o:>5}%{e:>6}%", "branco")
        self.log_missao.escrever("")

    def _inserir_dados(self) -> None:
        """Abre janela modal para inserir manualmente ou simular um ciclo."""
        import random

        janela = ctk.CTkToplevel(self)
        janela.title("Inserir / Simular Ciclo — O.R.B.I.T.A.")
        janela.geometry("440x560")
        janela.configure(fg_color=COR_BG_ESCURO)
        janela.transient(self)

        ctk.CTkLabel(janela, text="＋ NOVO CICLO DE LEITURA",
                     font=FONTE_HEADER, text_color=COR_CYAN).pack(pady=(16, 4))
        ctk.CTkLabel(janela, text="Digite os valores ou simule os sensores",
                     font=FONTE_SUBTITULO, text_color=COR_CINZA).pack(pady=(0, 14))

        # Campos de entrada
        campos_cfg = [
            ("Temperatura (°C)", "22", -50, 150),
            ("Comunicação (%)",  "95", 0, 100),
            ("Bateria (%)",      "92", 0, 100),
            ("Oxigênio (%)",     "97", 0, 100),
            ("Estabilidade (%)", "91", 0, 100),
        ]
        entradas: list[ctk.CTkEntry] = []
        form = ctk.CTkFrame(janela, fg_color="transparent")
        form.pack(padx=30, fill="x")

        for rotulo, default, _mn, _mx in campos_cfg:
            linha = ctk.CTkFrame(form, fg_color="transparent")
            linha.pack(fill="x", pady=5)
            ctk.CTkLabel(linha, text=rotulo, font=FONTE_MONO,
                         text_color=COR_BRANCO, width=160, anchor="w").pack(side="left")
            ent = ctk.CTkEntry(linha, font=FONTE_MONO, width=110,
                               fg_color=COR_BG_CARD, border_color=COR_BG_BORDA)
            ent.insert(0, default)
            ent.pack(side="right")
            entradas.append(ent)

        # Área de feedback
        feedback = ctk.CTkLabel(janela, text="", font=FONTE_MONO_SM,
                                text_color=COR_AMARELO, wraplength=380, justify="left")
        feedback.pack(pady=10, padx=30)

        def simular() -> None:
            valores = [
                random.randint(15, 45), random.randint(20, 100),
                random.randint(10, 100), random.randint(70, 100),
                random.randint(30, 100),
            ]
            for ent, val in zip(entradas, valores):
                ent.delete(0, "end")
                ent.insert(0, str(val))
            feedback.configure(text="Sensores simulados. Confira e confirme.",
                               text_color=COR_VERDE)

        def confirmar() -> None:
            try:
                novo = [int(e.get()) for e in entradas]
            except ValueError:
                feedback.configure(
                    text="Erro: todos os campos devem ser números inteiros.",
                    text_color=COR_VERMELHO)
                return

            # Validar faixas
            for (rotulo, _d, mn, mx), val in zip(campos_cfg, novo):
                if not (mn <= val <= mx):
                    feedback.configure(
                        text=f"Erro: {rotulo} fora da faixa ({mn} a {mx}).",
                        text_color=COR_VERMELHO)
                    return

            # Adicionar ao histórico
            self._dados_missao.append(novo)
            self._nomes_ciclos.append("Ciclo inserido pelo operador")

            # Verificação automática básica (DSA)
            alertas_basicos = verificacao_automatica(novo[0], novo[2], novo[1])

            # Analisar o ciclo e refletir nos gauges
            resultado = analisar_ciclo(novo)
            alerta    = avaliar_alerta_booleano(novo)
            idx = len(self._dados_missao) - 1
            self._atualizar_ciclo_ui(idx, "Ciclo inserido pelo operador",
                                     novo, resultado, alerta)

            # Log
            self.log_missao.escrever(
                f"\n＋ Ciclo {idx+1} inserido: {novo}", "header")
            if alertas_basicos:
                for a in alertas_basicos:
                    self.log_missao.escrever(f"  ⚠ {a}", "critico")
            else:
                self.log_missao.escrever("  Verificação automática: sem alertas básicos.", "normal")
            self.log_missao.escrever(
                f"  Pontuação: {resultado['pontuacao']}/10 | {resultado['status']}",
                "atencao" if resultado['pontuacao'] >= 3 else "normal")

            feedback.configure(
                text=f"Ciclo {idx+1} adicionado à missão com sucesso!",
                text_color=COR_VERDE)

        # Botões
        botoes = ctk.CTkFrame(janela, fg_color="transparent")
        botoes.pack(pady=14)
        ctk.CTkButton(botoes, text="⟳  SIMULAR SENSORES", command=simular,
                      font=FONTE_BOTAO, fg_color="transparent",
                      border_color=COR_AMARELO, border_width=2,
                      text_color=COR_AMARELO, hover_color=COR_BG_BORDA,
                      width=190, height=42, corner_radius=8).pack(side="left", padx=6)
        ctk.CTkButton(botoes, text="✓  CONFIRMAR", command=confirmar,
                      font=FONTE_BOTAO, fg_color="transparent",
                      border_color=COR_VERDE, border_width=2,
                      text_color=COR_VERDE, hover_color=COR_BG_BORDA,
                      width=150, height=42, corner_radius=8).pack(side="left", padx=6)

    def _relatorio_final(self) -> None:
        """Abre janela de relatório final."""
        if not self._resultados:
            self.log_missao.escrever(
                "Execute a análise primeiro.", "atencao")
            return

        janela = ctk.CTkToplevel(self)
        janela.title("Relatório Final — O.R.B.I.T.A.")
        janela.geometry("720x600")
        janela.configure(fg_color=COR_BG_ESCURO)

        ctk.CTkLabel(janela, text="[ RELATÓRIO FINAL DA MISSÃO ]",
                     font=FONTE_HEADER, text_color=COR_CYAN).pack(pady=12)

        log = LogPanel(janela, titulo="Dados consolidados")
        log.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        # Preencher relatório
        n = len(self._resultados)
        pontuacoes = [r["pontuacao"] for r in self._resultados]
        risco_medio = sum(pontuacoes) / n

        log.escrever("═" * 52, "header")
        log.escrever(f"  Missão : {NOME_MISSAO}", "branco")
        log.escrever(f"  Equipe : {NOME_EQUIPE}", "branco")
        log.escrever(f"  Ciclos : {n}", "branco")
        log.escrever("═" * 52, "header")

        labels_med = ["Temperatura","Comunicação","Bateria","Oxigênio","Estabilidade"]
        unids      = ["°C","%","%","%","%"]
        medias     = [sum(r["valores"][i] for r in self._resultados) / n
                      for i in range(5)]
        for i, lbl in enumerate(labels_med):
            log.escrever(f"  Média de {lbl:13}: {medias[i]:.1f}{unids[i]}", "branco")

        log.escrever("─" * 52, "dim")
        criticos_idx = [i+1 for i, r in enumerate(self._resultados)
                        if "CRITICA" in r["status"]]
        ciclo_max    = max(self._resultados, key=lambda r: r["pontuacao"])
        alertas_x1   = sum(1 for a in self._alertas if a["X"] == 1)

        tag_crit = "critico" if criticos_idx else "normal"
        log.escrever(f"  Ciclos críticos       : {criticos_idx or 'Nenhum'}", tag_crit)
        log.escrever(f"  Maior pontuação       : {ciclo_max['pontuacao']}/10", "atencao")
        log.escrever(f"  Risco médio           : {risco_medio:.2f}", "branco")
        log.escrever(f"  Alertas X=1 acionados : {alertas_x1}", tag_crit)

        log.escrever("─" * 52, "dim")
        tendencia = analisar_tendencia(self._resultados)
        area, acum = identificar_area_mais_afetada(self._resultados)
        log.escrever(f"  Tendência     : {tendencia}", "branco")
        log.escrever(f"  Área mais afetada: {area}", "atencao")

        log.escrever("─" * 52, "dim")
        log.escrever("  Pontuação acumulada por área:", "header")
        for i, ar in enumerate(areas_monitoradas):
            tag = "critico" if ar == area else "branco"
            log.escrever(f"    {ar:30}: {acum[i]} pontos", tag)

        log.escrever("═" * 52, "header")
        conclusao_map = {
            "MISSAO ESTAVEL":    "Missão transcorreu dentro dos parâmetros normais.",
            "MISSAO EM ATENCAO": "Missão apresentou instabilidade. Plano de contingência recomendado.",
            "MISSAO CRITICA":    "Missão enfrentou risco severo. Protocolo de emergência necessário.",
        }
        status_final = classificar_ciclo(round(risco_medio))
        cor_sf = ("critico" if "CRITICA" in status_final
                  else "atencao" if "ATENCAO" in status_final
                  else "normal")
        log.escrever(f"  Status final: {status_final}", cor_sf)
        log.escrever(f"  {conclusao_map.get(status_final,'')}", "branco")
        log.escrever("═" * 52, "header")


# ════════════════════════════════════════════════════════════
#  PONTO DE ENTRADA
# ════════════════════════════════════════════════════════════

def main() -> None:
    """Inicia a HUD do O.R.B.I.T.A."""
    app = OrbitalHUD()
    app.mainloop()


if __name__ == "__main__":
    main()
