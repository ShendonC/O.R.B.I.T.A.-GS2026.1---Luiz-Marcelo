"""
============================================================
  O.R.B.I.T.A. — Modelagem Matemática Computacional
  Disciplina: Modelagem Matemática (1º Semestre)
  Equipe: Aldebaran
============================================================
  Dois modelos contínuos que descrevem fenômenos físicos
  reais de uma missão espacial:

    1. P(t) = A · t² · e^(−k·t)
       Pressão aerodinâmica sobre o foguete ao longo do tempo.
       Sobe rápido na subida pela atmosfera densa, atinge um
       pico (Max Q) e decai conforme o ar rarefaz. O ponto de
       máximo é encontrado analiticamente pela derivada P'(t).

    2. R(T) = R_min + (1 − R_min) / (1 + e^(c·(T − T0)))
       Risco de falha em função da temperatura (inspirado no
       caso Challenger / O-rings). Função logística decrescente:
       satura em 1 no frio extremo e tende à assíntota R_min
       (risco residual) no calor. Respeita o limite [0, 1].

  Entregáveis gerados por este script:
    - Gráfico de P(t) com a reta tangente horizontal no Max Q
    - Gráfico de R(T) com a assíntota do risco residual
    - Relatório PDF com a validação matemática completa
============================================================
"""

import os
import math

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, HRFlowable,
)
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

# ── Configurações visuais ─────────────────────────────────
plt.rcParams.update({
    "font.family":       "DejaVu Sans",
    "axes.spines.top":   False,
    "axes.spines.right": False,
    "axes.grid":         True,
    "grid.alpha":        0.3,
    "figure.dpi":        150,
})

COR_PRIMARIA   = "#185FA5"
COR_SECUNDARIA = "#1D9E75"
COR_ALERTA     = "#BA7517"
COR_CRITICO    = "#A32D2D"
COR_NEUTRO     = "#5F5E5A"

DIR_DOCS   = os.path.join(os.path.dirname(__file__), "docs")
DIR_ASSETS = os.path.join(os.path.dirname(__file__), "assets")
os.makedirs(DIR_DOCS,   exist_ok=True)
os.makedirs(DIR_ASSETS, exist_ok=True)

GRAFICO_PRESSAO = os.path.join(DIR_ASSETS, "grafico_pressao.png")
GRAFICO_RISCO   = os.path.join(DIR_ASSETS, "grafico_risco.png")
PDF_OUT         = os.path.join(DIR_DOCS,   "relatorio_matematico_orbita.pdf")


# ════════════════════════════════════════════════════════════
#  1. MODELO DE PRESSÃO AERODINÂMICA — P(t)
# ════════════════════════════════════════════════════════════

# Parâmetros do modelo P(t) = A * t^2 * e^(-k*t)
#   A: fator de escala (intensidade da pressão)
#   k: taxa de decaimento (quão rápido a pressão cai após o pico)
P_A: float = 2.5    # kPa/s² — escala de pressão
P_K: float = 0.08   # 1/s    — decaimento atmosférico


def pressao(t: float) -> float:
    """Pressão aerodinâmica no instante t (em segundos).

    Modelo: P(t) = A · t² · e^(−k·t)

    Args:
        t: Tempo desde o lançamento, em segundos (t >= 0).

    Returns:
        Pressão aerodinâmica (unidade relativa, kPa).
    """
    return P_A * (t ** 2) * math.exp(-P_K * t)


def derivada_pressao(t: float) -> float:
    """Derivada P'(t) — taxa de variação da pressão aerodinâmica.

    P'(t) = A · e^(−k·t) · (2t − k·t²) = A · t · e^(−k·t) · (2 − k·t)

    A derivada representa a rapidez com que o foguete entra (ou sai)
    do estresse aerodinâmico. No ponto de máximo (Max Q), P'(t) = 0.

    Args:
        t: Tempo desde o lançamento, em segundos.

    Returns:
        Taxa de variação da pressão (kPa/s).
    """
    return P_A * t * math.exp(-P_K * t) * (2 - P_K * t)


def calcular_max_q() -> tuple[float, float]:
    """Calcula o ponto de máximo da pressão (Max Q) analiticamente.

    Resolvendo P'(t) = 0:
        A · t · e^(−k·t) · (2 − k·t) = 0
    As soluções são t = 0 (mínimo) e t = 2/k (máximo).
    O Max Q ocorre em t* = 2/k.

    Returns:
        Tupla (t_max, p_max): instante e valor do pico de pressão.
    """
    t_max = 2.0 / P_K
    p_max = pressao(t_max)
    return (t_max, p_max)


# ════════════════════════════════════════════════════════════
#  2. MODELO DE RISCO POR TEMPERATURA — R(T)
# ════════════════════════════════════════════════════════════

# Parâmetros do modelo logístico R(T) = R_min + (1 − R_min) / (1 + e^(c·(T − T0)))
#   R_min: risco residual mínimo (assíntota quando T → +∞)
#   c:     inclinação da transição (quão abrupta é a mudança de risco)
#   T0:    temperatura de transição (ponto de risco intermediário)
R_MIN: float = 0.05   # 5% de risco residual irredutível
R_C:   float = 0.20   # 1/°C — inclinação da curva logística
R_T0:  float = 5.0    # °C  — temperatura central da transição de risco


def risco(temp: float) -> float:
    """Risco de falha em função da temperatura (modelo logístico).

    Modelo: R(T) = R_min + (1 − R_min) / (1 + e^(c·(T − T0)))

    Função sigmoide decrescente, fisicamente correta para uma
    probabilidade (sempre entre R_min e 1):
      - No frio extremo (T → −∞): R → 1 (risco máximo, caso Challenger).
      - No calor (T → +∞): R → R_min (assíntota — risco residual).
      - Em T = T0: risco no ponto médio da transição.

    Args:
        temp: Temperatura em °C.

    Returns:
        Probabilidade de falha (entre R_min e 1).
    """
    return R_MIN + (1 - R_MIN) / (1 + math.exp(R_C * (temp - R_T0)))


def derivada_risco(temp: float) -> float:
    """Derivada R'(T) — taxa de variação do risco com a temperatura.

    R'(T) = −(1 − R_min) · c · e^(c·(T − T0)) / (1 + e^(c·(T − T0)))²

    Sempre negativa: o risco só decresce conforme a temperatura sobe.
    O módulo é máximo em T = T0 (transição mais rápida) e tende a zero
    nos extremos, onde a curva achata contra as assíntotas.

    Args:
        temp: Temperatura em °C.

    Returns:
        Taxa de variação do risco (por °C).
    """
    e = math.exp(R_C * (temp - R_T0))
    return -(1 - R_MIN) * R_C * e / ((1 + e) ** 2)


# ════════════════════════════════════════════════════════════
#  3. GERAÇÃO DOS GRÁFICOS
# ════════════════════════════════════════════════════════════

def gerar_grafico_pressao() -> None:
    """Gera o gráfico de P(t) destacando o ponto Max Q."""
    t_max, p_max = calcular_max_q()
    ts = np.linspace(0, 60, 500)
    ps = [pressao(t) for t in ts]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(ts, ps, color=COR_PRIMARIA, linewidth=2.2, label="P(t) = A·t²·e^(−k·t)")

    # Ponto de Max Q
    ax.scatter([t_max], [p_max], color=COR_CRITICO, zorder=5, s=70)
    ax.annotate(
        f"Max Q\nt* = {t_max:.1f}s\nP = {p_max:.1f} kPa",
        xy=(t_max, p_max), xytext=(t_max + 8, p_max - 55),
        fontsize=9, color=COR_CRITICO,
        arrowprops=dict(arrowstyle="->", color=COR_CRITICO))

    # Reta tangente horizontal no Max Q (derivada = 0)
    ax.axhline(y=p_max, xmin=0, xmax=1, color=COR_ALERTA,
               linestyle="--", linewidth=1, alpha=0.7,
               label="Tangente no Max Q (P'(t)=0)")

    ax.set_title("Modelo de Pressão Aerodinâmica — P(t)",
                 fontsize=12, fontweight="bold", color=COR_PRIMARIA)
    ax.set_xlabel("Tempo desde o lançamento (s)")
    ax.set_ylabel("Pressão aerodinâmica (kPa)")
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    fig.savefig(GRAFICO_PRESSAO, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] Gráfico de pressão salvo: {GRAFICO_PRESSAO}")


def gerar_grafico_risco() -> None:
    """Gera o gráfico de R(T) destacando a assíntota do risco residual."""
    temps = np.linspace(-30, 60, 500)
    rs = [risco(t) for t in temps]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(temps, rs, color=COR_SECUNDARIA, linewidth=2.2,
            label="R(T) = R_min + (1−R_min)/(1+e^(c·(T−T0)))")

    # Assíntota horizontal (risco residual)
    ax.axhline(y=R_MIN, color=COR_CRITICO, linestyle="--", linewidth=1.2,
               label=f"Risco residual R_min = {R_MIN:.2f}")

    # Marcar temperatura ótima de operação (exemplo: 20°C)
    t_op = 20
    ax.scatter([t_op], [risco(t_op)], color=COR_PRIMARIA, zorder=5, s=60)
    ax.annotate(
        f"Operação típica\nT = {t_op}°C\nR = {risco(t_op):.2f}",
        xy=(t_op, risco(t_op)), xytext=(t_op + 8, risco(t_op) + 0.25),
        fontsize=9, color=COR_PRIMARIA,
        arrowprops=dict(arrowstyle="->", color=COR_PRIMARIA))

    ax.set_title("Modelo de Risco por Temperatura — R(T)",
                 fontsize=12, fontweight="bold", color=COR_SECUNDARIA)
    ax.set_xlabel("Temperatura (°C)")
    ax.set_ylabel("Probabilidade de falha")
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    fig.savefig(GRAFICO_RISCO, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] Gráfico de risco salvo: {GRAFICO_RISCO}")


# ════════════════════════════════════════════════════════════
#  4. RELATÓRIO PDF
# ════════════════════════════════════════════════════════════

def gerar_relatorio_pdf() -> None:
    """Gera o relatório PDF com a validação matemática completa."""
    estilos = getSampleStyleSheet()
    estilo_titulo = ParagraphStyle(
        "TituloORBITA", parent=estilos["Title"],
        fontSize=20, textColor=colors.HexColor(COR_PRIMARIA),
        spaceAfter=6, alignment=TA_CENTER)
    estilo_sub = ParagraphStyle(
        "Subtitulo", parent=estilos["Heading2"],
        fontSize=13, textColor=colors.HexColor(COR_PRIMARIA),
        spaceBefore=14, spaceAfter=6)
    estilo_corpo = ParagraphStyle(
        "Corpo", parent=estilos["BodyText"],
        fontSize=10, leading=15, alignment=TA_JUSTIFY, spaceAfter=8)
    estilo_formula = ParagraphStyle(
        "Formula", parent=estilos["BodyText"],
        fontSize=12, leading=18, alignment=TA_CENTER,
        textColor=colors.HexColor(COR_CRITICO), spaceAfter=8,
        fontName="Courier-Bold")

    t_max, p_max = calcular_max_q()
    doc = SimpleDocTemplate(
        PDF_OUT, pagesize=A4,
        topMargin=2 * cm, bottomMargin=2 * cm,
        leftMargin=2 * cm, rightMargin=2 * cm)
    elems = []

    # Cabeçalho
    elems.append(Paragraph("O.R.B.I.T.A.", estilo_titulo))
    elems.append(Paragraph(
        "Modelagem Matemática Computacional — Equipe Aldebaran",
        ParagraphStyle("s", parent=estilo_corpo, alignment=TA_CENTER,
                       textColor=colors.HexColor(COR_NEUTRO))))
    elems.append(Spacer(1, 6))
    elems.append(HRFlowable(width="100%", thickness=1,
                            color=colors.HexColor(COR_PRIMARIA)))
    elems.append(Spacer(1, 10))

    # Introdução
    elems.append(Paragraph("1. Introdução", estilo_sub))
    elems.append(Paragraph(
        "Este relatório apresenta dois modelos matemáticos contínuos que "
        "descrevem fenômenos físicos reais de uma missão espacial: a pressão "
        "aerodinâmica sobre o foguete durante a subida, P(t), e o risco de "
        "falha em função da temperatura, R(T). O objetivo é traduzir o "
        "comportamento físico real para a linguagem matemática, validando "
        "cada modelo pelo seu domínio, derivada e pontos críticos.",
        estilo_corpo))

    # Modelo P(t)
    elems.append(Paragraph("2. Modelo de Pressão Aerodinâmica — P(t)", estilo_sub))
    elems.append(Paragraph("P(t) = A · t² · e^(−k·t)", estilo_formula))
    elems.append(Paragraph(
        f"Com os parâmetros adotados A = {P_A} e k = {P_K}, a função modela "
        "o comportamento de subida e queda da pressão. No instante do "
        "lançamento (t = 0), a pressão é zero — o foguete está parado na base. "
        "Conforme ganha velocidade nas camadas densas da atmosfera, a pressão "
        "cresce de forma acelerada (o termo t² domina). Após o pico, o termo "
        "exponencial e^(−k·t) domina e a pressão decai, pois o ar rarefaz com "
        "a altitude. Uma função de 1º grau seria insuficiente, pois cresceria "
        "infinitamente, o que não tem sentido físico.", estilo_corpo))
    elems.append(Paragraph(
        "A derivada, que representa a rapidez com que o foguete entra em "
        "estresse aerodinâmico, é:", estilo_corpo))
    elems.append(Paragraph("P'(t) = A · t · e^(−k·t) · (2 − k·t)", estilo_formula))
    elems.append(Paragraph(
        f"Igualando P'(t) = 0, obtemos as soluções t = 0 (mínimo) e t = 2/k "
        f"(máximo). Portanto, o ponto de pressão máxima — o <b>Max Q</b> — "
        f"ocorre em t* = 2/k = {t_max:.1f} segundos, com pressão de "
        f"{p_max:.1f} kPa. Nesse ponto, a reta tangente à curva é horizontal "
        f"(inclinação zero), confirmando o máximo.", estilo_corpo))
    if os.path.exists(GRAFICO_PRESSAO):
        elems.append(Spacer(1, 6))
        elems.append(Image(GRAFICO_PRESSAO, width=15 * cm, height=8.4 * cm))

    elems.append(PageBreak())

    # Modelo R(T)
    elems.append(Paragraph("3. Modelo de Risco por Temperatura — R(T)", estilo_sub))
    elems.append(Paragraph("R(T) = R_min + (1 − R_min) / (1 + e^(c·(T − T0)))", estilo_formula))
    elems.append(Paragraph(
        f"Inspirado no caso do ônibus espacial Challenger, em que as vedações "
        f"(O-rings) falharam devido à baixa temperatura, este modelo logístico "
        f"usa R_min = {R_MIN}, c = {R_C} e T0 = {R_T0}°C. Optou-se por uma "
        "função sigmoide (e não uma exponencial pura) porque o risco é uma "
        "probabilidade e deve permanecer no intervalo [0, 1]. No frio extremo "
        "(T → −∞), o risco satura em 1 (falha praticamente certa); conforme a "
        "temperatura sobe, o risco decai suavemente. Crucialmente, a função "
        "nunca toca o eixo horizontal: tende à assíntota R_min, representando "
        "o risco residual irredutível (falhas mecânicas, erro humano, "
        "problemas de combustível) que existe independentemente da temperatura.",
        estilo_corpo))
    elems.append(Paragraph(
        "A derivada do risco em relação à temperatura é:", estilo_corpo))
    elems.append(Paragraph(
        "R'(T) = −(1−R_min)·c·e^(c·(T−T0)) / (1 + e^(c·(T−T0)))²", estilo_formula))
    elems.append(Paragraph(
        "A derivada é sempre negativa, confirmando que o risco só diminui com "
        "o aumento da temperatura. Seu módulo é máximo em T = T0 (onde a "
        "transição de risco é mais rápida) e tende a zero nos extremos, onde "
        "a curva se achata contra as assíntotas — no calor, isso reflete o "
        "'risco mínimo aceitável' que não diminui mais por aquecer.",
        estilo_corpo))
    if os.path.exists(GRAFICO_RISCO):
        elems.append(Spacer(1, 6))
        elems.append(Image(GRAFICO_RISCO, width=15 * cm, height=8.4 * cm))

    # Validação
    elems.append(Paragraph("4. Validação e Rigor Matemático", estilo_sub))
    dados_validacao = [
        ["Aspecto", "P(t) — Pressão", "R(T) — Risco"],
        ["Domínio", "t ≥ 0 (segundos)", "T ∈ ℝ (°C realista: −40 a 60)"],
        ["Imagem", "P ≥ 0 (kPa)", "R ∈ [R_min, 1] (probabilidade)"],
        ["Derivada", "P'(t) = A·t·e^(−k·t)·(2−k·t)", "R'(T) < 0 (sempre decrescente)"],
        ["Ponto crítico", f"Max Q em t = {t_max:.1f}s", "Transição em T0 (assíntota R_min)"],
        ["Comportamento", "Sobe e desce (pico)", "Sigmoide decrescente (frio→1, calor→R_min)"],
    ]
    tabela = Table(dados_validacao, colWidths=[3 * cm, 6 * cm, 6 * cm])
    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(COR_PRIMARIA)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor(COR_NEUTRO)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#F0F4F8")]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    elems.append(tabela)
    elems.append(Spacer(1, 10))

    # Conclusão
    elems.append(Paragraph("5. Conclusão", estilo_sub))
    elems.append(Paragraph(
        "Ambos os modelos passam no teste de realidade física. O modelo P(t) "
        "captura corretamente o fenômeno do Max Q — o instante de máximo "
        "estresse aerodinâmico que todo foguete enfrenta. O modelo R(T) "
        "representa fielmente a relação entre temperatura e risco, incluindo "
        "o conceito de risco residual via assíntota horizontal. Os pontos "
        "críticos encontrados pelas derivadas são coerentes com a operação "
        "real de um lançamento, integrando-se ao monitoramento do sistema "
        "O.R.B.I.T.A.", estilo_corpo))

    doc.build(elems)
    print(f"  [OK] Relatório PDF gerado: {PDF_OUT}")


# ════════════════════════════════════════════════════════════
#  PONTO DE ENTRADA
# ════════════════════════════════════════════════════════════

def main() -> None:
    """Executa o pipeline completo de modelagem matemática."""
    print("=" * 60)
    print("  O.R.B.I.T.A. — Modelagem Matemática Computacional")
    print("=" * 60)

    t_max, p_max = calcular_max_q()
    print("\n[1/3] Modelo de Pressão P(t) = A·t²·e^(−k·t)")
    print(f"      Parâmetros: A = {P_A}, k = {P_K}")
    print(f"      Max Q analítico: t* = 2/k = {t_max:.2f}s → P = {p_max:.2f} kPa")
    print(f"      Verificação P'(t*) = {derivada_pressao(t_max):.6f} (≈ 0, confirma máximo)")

    print("\n[2/3] Modelo de Risco R(T) = R_min + (1−R_min)/(1+e^(c·(T−T0)))")
    print(f"      Parâmetros: R_min = {R_MIN}, c = {R_C}, T0 = {R_T0}")
    print(f"      Risco a −20°C: {risco(-20):.3f}  |  a 5°C: {risco(5):.3f}  |  a 50°C: {risco(50):.3f}")
    print(f"      Assíntota (risco residual): R_min = {R_MIN}")

    print("\n[3/3] Gerando gráficos e relatório...")
    gerar_grafico_pressao()
    gerar_grafico_risco()
    gerar_relatorio_pdf()

    print("\n" + "=" * 60)
    print("  Pipeline de modelagem matemática concluído!")
    print(f"  Relatório : {PDF_OUT}")
    print(f"  Gráficos  : {DIR_ASSETS}")
    print("=" * 60)


if __name__ == "__main__":
    main()
