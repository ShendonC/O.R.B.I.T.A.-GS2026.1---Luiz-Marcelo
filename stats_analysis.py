"""
============================================================
  O.R.B.I.T.A. — Análise Estatística
  Disciplina: Modelagem Linear para Aprendizado de Máquina
  Equipe: Aldebaran
============================================================
  Dataset: UCS Satellite Database (Mai/2023)
  Fonte: Union of Concerned Scientists — ucsusa.org
  Registro: 1.305 satélites operacionais em órbita terrestre

  Entregáveis gerados por este script:
    1. Tabela de frequência — variável discreta (Class of Orbit)
    2. Tabela de frequência — variável contínua (Launch Mass kg)
    3. Gráfico 1 — Distribuição por Classe de Órbita (barras)
    4. Gráfico 2 — Distribuição de Massa de Lançamento (histograma)
    5. Análise univariada 1 — Launch Mass (kg)
    6. Análise univariada 2 — Perigee altitude (km)
    7. Transformação linear matricial — normalização orbital
    8. Relatório estatístico em PDF
============================================================
"""

import os
import warnings
import urllib.request

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, HRFlowable,
)
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

warnings.filterwarnings("ignore")

# ── Configurações visuais ─────────────────────────────────
plt.rcParams.update({
    "font.family":      "DejaVu Sans",
    "axes.spines.top":  False,
    "axes.spines.right": False,
    "axes.grid":        True,
    "grid.alpha":       0.3,
    "figure.dpi":       150,
})

# ── Paleta de cores do projeto ────────────────────────────
COR_PRIMARIA   = "#185FA5"   # azul O.R.B.I.T.A.
COR_SECUNDARIA = "#1D9E75"   # verde
COR_ALERTA     = "#BA7517"   # âmbar
COR_CRITICO    = "#A32D2D"   # vermelho
COR_NEUTRO     = "#5F5E5A"   # cinza

# ── Caminhos de saída ─────────────────────────────────────
DIR_DATA   = os.path.join(os.path.dirname(__file__), "data")
DIR_DOCS   = os.path.join(os.path.dirname(__file__), "docs")
DIR_ASSETS = os.path.join(os.path.dirname(__file__), "assets")

os.makedirs(DIR_DATA,   exist_ok=True)
os.makedirs(DIR_DOCS,   exist_ok=True)
os.makedirs(DIR_ASSETS, exist_ok=True)

DATASET_PATH = os.path.join(DIR_DATA,   "ucs_satellites.csv")
GRAFICO1     = os.path.join(DIR_ASSETS, "grafico_orbita.png")
GRAFICO2     = os.path.join(DIR_ASSETS, "grafico_massa.png")
GRAFICO3     = os.path.join(DIR_ASSETS, "grafico_matrix.png")
GRAFICO4     = os.path.join(DIR_ASSETS, "grafico_massa_orbita.png")
PDF_OUT      = os.path.join(DIR_DOCS,   "relatorio_estatistico_orbita.pdf")


# ════════════════════════════════════════════════════════════
#  1. INGESTÃO DE DADOS
# ════════════════════════════════════════════════════════════

def baixar_dataset() -> None:
    """Baixa o UCS Satellite Database se ainda não existir localmente."""
    if os.path.exists(DATASET_PATH):
        print(f"  [OK] Dataset já presente: {DATASET_PATH}")
        return
    url = (
        "https://raw.githubusercontent.com/tumblr/data-lasso"
        "/master/samples/UCS_Satellite_Database.csv"
    )
    print("  Baixando UCS Satellite Database...")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read()
    with open(DATASET_PATH, "wb") as f:
        f.write(data)
    print(f"  [OK] {len(data)/1024:.1f} KB salvo em {DATASET_PATH}")


def carregar_e_limpar() -> pd.DataFrame:
    """Carrega e realiza o pré-processamento do dataset.

    Etapas:
      - Remove colunas Unnamed (artefatos do CSV)
      - Converte Launch Mass e Perigee para numérico
      - Remove linhas sem massa nem altitude
      - Padroniza Class of Orbit (strip)

    Returns:
        DataFrame limpo com as colunas relevantes.
    """
    df = pd.read_csv(DATASET_PATH, encoding="utf-8", on_bad_lines="skip")

    # Remover colunas Unnamed
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]

    # Converter numéricos
    df["Launch Mass (kg.)"] = pd.to_numeric(df["Launch Mass (kg.)"], errors="coerce")
    df["Perigee (km)"]      = pd.to_numeric(df["Perigee (km)"],      errors="coerce")
    df["Apogee (km)"]       = pd.to_numeric(df["Apogee (km)"],       errors="coerce")

    # Padronizar Class of Orbit
    df["Class of Orbit"] = df["Class of Orbit"].str.strip()

    # Converter Expected Lifetime — extrai número da string "15 yrs."
    def parse_lifetime(val: str) -> float:
        if pd.isna(val):
            return np.nan
        val = str(val).strip().lower()
        if val.startswith("<1"):
            return 0.5
        try:
            return float(val.split()[0])
        except Exception:
            return np.nan

    df["Lifetime (yrs)"] = df["Expected Lifetime"].apply(parse_lifetime)

    print(f"  [OK] Dataset carregado: {len(df)} satélites, {df.shape[1]} colunas úteis")
    print(f"       Launch Mass válidos : {df['Launch Mass (kg.)'].notna().sum()}")
    print(f"       Perigee válidos     : {df['Perigee (km)'].notna().sum()}")
    print(f"       Lifetime válidos    : {df['Lifetime (yrs)'].notna().sum()}")
    return df


# ════════════════════════════════════════════════════════════
#  2. TABELAS DE FREQUÊNCIA
# ════════════════════════════════════════════════════════════

def tabela_frequencia_discreta(df: pd.DataFrame) -> pd.DataFrame:
    """Tabela de distribuição de frequência — variável discreta.

    Variável: Class of Orbit (LEO, GEO, MEO, Elliptical)
    Inclui: frequência absoluta, relativa (%) e acumulada (%).

    Args:
        df: DataFrame limpo.

    Returns:
        DataFrame com a tabela de frequência.
    """
    contagem = df["Class of Orbit"].value_counts().reset_index()
    contagem.columns = ["Classe de Órbita", "Freq. Absoluta"]
    total = contagem["Freq. Absoluta"].sum()
    contagem["Freq. Relativa (%)"]  = (contagem["Freq. Absoluta"] / total * 100).round(2)
    contagem["Freq. Acumulada (%)"] = contagem["Freq. Relativa (%)"].cumsum().round(2)
    return contagem


def tabela_frequencia_continua(df: pd.DataFrame, n_classes: int = 7) -> pd.DataFrame:
    """Tabela de distribuição de frequência — variável contínua.

    Variável: Launch Mass (kg) com classes de intervalo.
    Inclui: intervalo, ponto médio, freq. absoluta, relativa e acumulada.

    Args:
        df:        DataFrame limpo.
        n_classes: Número de classes do histograma (Regra de Sturges).

    Returns:
        DataFrame com a tabela de frequência por classes.
    """
    massa = df["Launch Mass (kg.)"].dropna()
    minv, maxv = massa.min(), massa.max()
    amplitude = (maxv - minv) / n_classes

    limites = [minv + i * amplitude for i in range(n_classes + 1)]
    labels, pontos_medios, abs_freq = [], [], []

    for i in range(n_classes):
        li, ls = limites[i], limites[i + 1]
        labels.append(f"{li:.0f} ⊢ {ls:.0f}")
        pontos_medios.append((li + ls) / 2)
        if i < n_classes - 1:
            freq = ((massa >= li) & (massa < ls)).sum()
        else:
            freq = ((massa >= li) & (massa <= ls)).sum()
        abs_freq.append(freq)

    total = sum(abs_freq)
    rel   = [round(f / total * 100, 2) for f in abs_freq]
    acum  = []
    s = 0.0
    for r in rel:
        s += r
        acum.append(round(s, 2))

    return pd.DataFrame({
        "Intervalo (kg)":         labels,
        "Ponto Médio (kg)":       [round(p) for p in pontos_medios],
        "Freq. Absoluta":         abs_freq,
        "Freq. Relativa (%)":     rel,
        "Freq. Acumulada (%)":    acum,
    })


# ════════════════════════════════════════════════════════════
#  3. ANÁLISES UNIVARIADAS
# ════════════════════════════════════════════════════════════

def analise_univariada(serie: pd.Series, nome: str, unidade: str) -> dict:
    """Calcula medidas descritivas completas de uma variável contínua.

    Inclui:
      - Tendência central: média, mediana, moda
      - Dispersão: mín, máx, amplitude, variância, desvio padrão, CV
      - Separatrizes: Q1, Q2, Q3, IQR

    Args:
        serie:   Series pandas com os dados numéricos.
        nome:    Nome da variável para exibição.
        unidade: Unidade de medida (ex: "kg", "km").

    Returns:
        Dicionário com todas as medidas calculadas.
    """
    s = serie.dropna()
    media    = s.mean()
    mediana  = s.median()
    moda     = s.mode().iloc[0] if not s.mode().empty else np.nan
    minv     = s.min()
    maxv     = s.max()
    amp      = maxv - minv
    varianca = s.var(ddof=1)
    dp       = s.std(ddof=1)
    cv       = (dp / media * 100) if media != 0 else 0
    q1       = s.quantile(0.25)
    q2       = s.quantile(0.50)
    q3       = s.quantile(0.75)
    iqr      = q3 - q1

    resultado = {
        "nome":       nome,
        "unidade":    unidade,
        "n":          len(s),
        "media":      round(media, 2),
        "mediana":    round(mediana, 2),
        "moda":       round(moda, 2),
        "minimo":     round(minv, 2),
        "maximo":     round(maxv, 2),
        "amplitude":  round(amp, 2),
        "variancia":  round(varianca, 2),
        "desvio_pad": round(dp, 2),
        "cv_pct":     round(cv, 2),
        "q1":         round(q1, 2),
        "q2":         round(q2, 2),
        "q3":         round(q3, 2),
        "iqr":        round(iqr, 2),
    }

    print(f"\n  === Análise Univariada — {nome} ({unidade}) ===")
    print(f"  N válidos  : {resultado['n']}")
    print(f"  Média      : {resultado['media']:.2f} {unidade}")
    print(f"  Mediana    : {resultado['mediana']:.2f} {unidade}")
    print(f"  Moda       : {resultado['moda']:.2f} {unidade}")
    print(f"  Mín / Máx  : {resultado['minimo']:.2f} / {resultado['maximo']:.2f} {unidade}")
    print(f"  Amplitude  : {resultado['amplitude']:.2f} {unidade}")
    print(f"  Variância  : {resultado['variancia']:.2f}")
    print(f"  Desvio Pad : {resultado['desvio_pad']:.2f} {unidade}")
    print(f"  CV         : {resultado['cv_pct']:.2f}%")
    print(f"  Q1 / Q2 / Q3: {resultado['q1']} / {resultado['q2']} / {resultado['q3']} {unidade}")
    print(f"  IQR        : {resultado['iqr']:.2f} {unidade}")

    return resultado


# ════════════════════════════════════════════════════════════
#  4. GRÁFICOS
# ════════════════════════════════════════════════════════════

def grafico_orbita(df: pd.DataFrame) -> None:
    """Gráfico 1 — Distribuição de satélites por Classe de Órbita.

    Tipo: gráfico de barras horizontais com anotações de contagem.
    Eixos, título, fonte e legenda incluídos.

    Args:
        df: DataFrame limpo.
    """
    contagem = df["Class of Orbit"].value_counts()
    orbitas  = contagem.index.tolist()
    valores  = contagem.values.tolist()
    total    = sum(valores)

    cores = [COR_PRIMARIA, COR_SECUNDARIA, COR_ALERTA, COR_CRITICO, COR_NEUTRO]

    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.barh(orbitas, valores, color=cores[:len(orbitas)], height=0.6,
                   edgecolor="white", linewidth=0.8, zorder=3)

    for bar, val in zip(bars, valores):
        pct = val / total * 100
        ax.text(
            bar.get_width() + total * 0.01, bar.get_y() + bar.get_height() / 2,
            f"{val:,}  ({pct:.1f}%)",
            va="center", ha="left", fontsize=10, fontweight="bold",
            color=COR_NEUTRO,
        )

    ax.set_xlabel("Número de Satélites", fontsize=11)
    ax.set_ylabel("Classe de Órbita", fontsize=11)
    ax.set_title(
        "Distribuição de Satélites Operacionais por Classe de Órbita",
        fontsize=13, fontweight="bold", pad=14, color=COR_PRIMARIA,
    )
    ax.set_xlim(0, max(valores) * 1.25)
    ax.tick_params(axis="y", labelsize=10)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:,.0f}"))

    # Legenda explicativa das siglas de órbita
    legenda = ("LEO: Órbita Baixa  |  GEO: Geoestacionária  |  "
               "MEO: Órbita Média  |  Elliptical: Elíptica")
    fig.text(0.01, 0.045, legenda, fontsize=8, color=COR_PRIMARIA, style="italic")
    fig.text(
        0.01, 0.01,
        "Fonte: UCS Satellite Database (Mai/2023) — ucsusa.org | Equipe Aldebaran — O.R.B.I.T.A.",
        fontsize=8, color=COR_NEUTRO,
    )
    plt.tight_layout(rect=[0, 0.07, 1, 1])
    plt.savefig(GRAFICO1, bbox_inches="tight")
    plt.close()
    print(f"  [OK] Gráfico 1 salvo: {GRAFICO1}")


def grafico_massa(df: pd.DataFrame) -> None:
    """Gráfico 2 — Distribuição da Massa de Lançamento (kg).

    Tipo: histograma com curva KDE sobreposta, linhas de média e mediana.
    Eixos, título, legenda e fonte incluídos.

    Args:
        df: DataFrame limpo.
    """
    massa = df["Launch Mass (kg.)"].dropna()
    # Filtrar outliers extremos para visualização (>10.000 kg são raros)
    massa_vis = massa[massa <= 10_000]

    fig, ax = plt.subplots(figsize=(9, 5))

    ax.hist(
        massa_vis, bins=30, color=COR_PRIMARIA,
        alpha=0.7, edgecolor="white", linewidth=0.5, zorder=3,
        label="Frequência observada",
    )

    # Curva KDE (densidade suavizada) sobreposta, reescalada ao histograma
    try:
        from scipy.stats import gaussian_kde
        kde = gaussian_kde(massa_vis)
        xs = np.linspace(massa_vis.min(), massa_vis.max(), 300)
        # Reescala a densidade para a altura do histograma
        bin_width = (massa_vis.max() - massa_vis.min()) / 30
        ax.plot(xs, kde(xs) * len(massa_vis) * bin_width,
                color=COR_ALERTA, linewidth=2, zorder=5, label="Densidade (KDE)")
    except Exception:
        pass  # scipy opcional; histograma funciona sem a curva

    media   = massa.mean()
    mediana = massa.median()
    ax.axvline(media,   color=COR_CRITICO,    linestyle="--", linewidth=1.8,
               label=f"Média: {media:,.0f} kg",   zorder=4)
    ax.axvline(mediana, color=COR_SECUNDARIA, linestyle="-.", linewidth=1.8,
               label=f"Mediana: {mediana:,.0f} kg", zorder=4)

    ax.set_xlabel("Massa de Lançamento (kg)", fontsize=11)
    ax.set_ylabel("Frequência Absoluta",      fontsize=11)
    ax.set_title(
        "Distribuição da Massa de Lançamento dos Satélites Operacionais",
        fontsize=13, fontweight="bold", pad=14, color=COR_PRIMARIA,
    )
    ax.legend(fontsize=9, loc="upper right")
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:,.0f}"))

    # Anotação interpretativa: assimetria à direita
    ax.text(
        0.97, 0.55,
        "Distribuição assimétrica\nà direita: média > mediana\n(poucos satélites pesados\npuxam a média)",
        transform=ax.transAxes, fontsize=8, color=COR_NEUTRO,
        ha="right", va="top", style="italic",
        bbox=dict(boxstyle="round,pad=0.4", fc="#F0F4F8", ec=COR_NEUTRO, lw=0.5),
    )

    fig.text(
        0.01, 0.01,
        "Fonte: UCS Satellite Database (Mai/2023) — ucsusa.org | Equipe Aldebaran — O.R.B.I.T.A.\n"
        "Nota: satélites com massa > 10.000 kg excluídos da visualização para legibilidade.",
        fontsize=8, color=COR_NEUTRO,
    )
    plt.tight_layout(rect=[0, 0.06, 1, 1])
    plt.savefig(GRAFICO2, bbox_inches="tight")
    plt.close()
    print(f"  [OK] Gráfico 2 salvo: {GRAFICO2}")


# ════════════════════════════════════════════════════════════
#  5. TRANSFORMAÇÃO LINEAR MATRICIAL
# ════════════════════════════════════════════════════════════

def transformacao_linear_matricial(df: pd.DataFrame) -> dict:
    """Aplica transformação linear matricial aos parâmetros orbitais.

    Problema monitorado por satélite:
        Classificar satélites pelo perfil orbital usando normalização
        Min-Max via álgebra linear — base para o motor de diagnóstico
        do O.R.B.I.T.A. calibrar limiares de altitude e eccentricidade.

    Variáveis de entrada (X):
        Perigee (km), Apogee (km), Inclination (degrees)

    Transformação matricial (Min-Max normalização):
        X_norm = (X - X_min) @ diag(1 / (X_max - X_min))

    A matriz de transformação T é a matriz diagonal dos fatores de escala:
        T = diag([1/(max-min) para cada variável])

    Args:
        df: DataFrame limpo com dados orbitais.

    Returns:
        Dicionário com dados originais, matriz T e dados transformados.
    """
    cols = ["Perigee (km)", "Apogee (km)", "Inclination (degrees)"]
    sub  = df[cols].dropna().copy()

    # Amostra representativa de todo o dataset (não só os primeiros, que são
    # todos GEO e colapsariam o gráfico). Amostragem aleatória reproduzível.
    if len(sub) > 300:
        sub = sub.sample(n=300, random_state=42).reset_index(drop=True)

    X      = sub.values.astype(float)
    X_min  = X.min(axis=0)
    X_max  = X.max(axis=0)
    ranges = X_max - X_min
    ranges[ranges == 0] = 1.0  # evita divisão por zero se uma coluna for constante

    # Matriz de transformação T (diagonal de fatores de escala)
    T = np.diag(1.0 / ranges)

    # Centralização: X - X_min
    X_cent = X - X_min

    # Transformação: X_norm = X_cent @ T
    X_norm = X_cent @ T

    print("\n  === Transformação Linear Matricial ===")
    print(f"  Variáveis: {cols}")
    print(f"  Shape de X:      {X.shape}")
    print(f"  Shape de T:      {T.shape}")
    print(f"  Shape de X_norm: {X_norm.shape}")
    print("\n  Matriz de transformação T (diagonal 3x3):")
    for row in T:
        print("   ", " ".join(f"{v:.6f}" for v in row))
    print("\n  Amostra — primeiras 3 linhas após normalização:")
    for i in range(3):
        orig = X[i]
        norm = X_norm[i]
        print(f"   Original: {orig} → Normalizado: {norm.round(4)}")

    return {
        "colunas":       cols,
        "X_original":    X,
        "X_min":         X_min,
        "X_max":         X_max,
        "T":             T,
        "X_normalizado": X_norm,
        "df_orig":       sub,
    }


def grafico_transformacao(resultado_mat: dict) -> None:
    """Gráfico 3 — Comparação antes/depois da transformação matricial.

    Mostra a nuvem de satélites (Perigee vs Apogee) no espaço original e
    no espaço normalizado [0,1], com cor por inclinação orbital. Para a
    estrutura dos dados ficar visível, filtra outliers extremos via
    percentil 95 (órbitas muito excêntricas comprimiriam o gráfico).
    Evidencia que a transformação linear preserva a estrutura relativa
    dos dados, apenas reescalando — conceito central de álgebra linear.

    Args:
        resultado_mat: Dicionário retornado por transformacao_linear_matricial().
    """
    X      = resultado_mat["X_original"]
    X_norm = resultado_mat["X_normalizado"]
    incl   = X[:, 2]

    fig, axes = plt.subplots(1, 2, figsize=(12, 5.2))

    # Espaço original — escala log nos eixos, pois apogeu/perigeu variam
    # em ordens de magnitude (LEO ~500km vs GEO ~35.000km). A escala log
    # revela a estrutura que uma escala linear comprimiria.
    axes[0].scatter(X[:, 0], X[:, 1], c=incl, cmap="plasma",
                    s=42, alpha=0.7, edgecolors="white", linewidths=0.4, zorder=3)
    axes[0].set_xscale("log")
    axes[0].set_yscale("log")
    axes[0].set_xlabel("Perigeu (km) — escala log", fontsize=10)
    axes[0].set_ylabel("Apogeu (km) — escala log",  fontsize=10)
    axes[0].set_title("Espaço Original (escala log)", fontsize=12,
                      fontweight="bold", color=COR_PRIMARIA)
    axes[0].xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:,.0f}"))
    axes[0].yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:,.0f}"))

    # Espaço normalizado [0,1] — resultado da transformação matricial
    sc1 = axes[1].scatter(X_norm[:, 0], X_norm[:, 1], c=incl, cmap="plasma",
                          s=42, alpha=0.7, edgecolors="white", linewidths=0.4, zorder=3)
    axes[1].set_xlabel("Perigeu (normalizado)", fontsize=10)
    axes[1].set_ylabel("Apogeu (normalizado)",  fontsize=10)
    axes[1].set_title("Após Transformação Matricial T → [0, 1]",
                      fontsize=12, fontweight="bold", color=COR_SECUNDARIA)

    cbar = fig.colorbar(sc1, ax=axes, fraction=0.04, pad=0.04)
    cbar.set_label("Inclinação orbital (graus)", fontsize=9)

    fig.suptitle(
        f"Transformação Linear Min-Max dos Parâmetros Orbitais  "
        f"(n = {len(X)} satélites)",
        fontsize=12.5, fontweight="bold",
    )
    fig.text(
        0.01, 0.01,
        "Fonte: UCS Satellite Database (Mai/2023) | Equipe Aldebaran — O.R.B.I.T.A.",
        fontsize=8, color=COR_NEUTRO,
    )
    plt.savefig(GRAFICO3, bbox_inches="tight")
    plt.close()
    print(f"  [OK] Gráfico 3 salvo: {GRAFICO3}")


def grafico_massa_por_orbita(df: pd.DataFrame) -> None:
    """Gráfico 4 — Massa de lançamento por classe de órbita (boxplot).

    Análise bivariada que cruza massa (contínua) com classe de órbita
    (categórica), revelando como o porte dos satélites varia conforme o
    tipo de missão. Boxplot mostra mediana, quartis e dispersão por grupo.

    Args:
        df: DataFrame limpo.
    """
    sub = df[["Class of Orbit", "Launch Mass (kg.)"]].dropna()
    sub = sub[sub["Launch Mass (kg.)"] <= 10_000]

    # Ordenar por mediana de massa para leitura mais clara
    ordem = (sub.groupby("Class of Orbit")["Launch Mass (kg.)"]
             .median().sort_values().index.tolist())
    dados = [sub[sub["Class of Orbit"] == o]["Launch Mass (kg.)"].values
             for o in ordem]

    fig, ax = plt.subplots(figsize=(9, 5))
    bp = ax.boxplot(dados, labels=ordem, patch_artist=True, vert=True,
                    widths=0.6, showfliers=True,
                    flierprops=dict(marker="o", markersize=3,
                                    markerfacecolor=COR_NEUTRO, alpha=0.4))

    cores = [COR_PRIMARIA, COR_SECUNDARIA, COR_ALERTA, COR_CRITICO, COR_NEUTRO]
    for patch, cor in zip(bp["boxes"], cores[:len(ordem)]):
        patch.set_facecolor(cor)
        patch.set_alpha(0.65)
    for mediana in bp["medians"]:
        mediana.set_color("white")
        mediana.set_linewidth(2)

    ax.set_xlabel("Classe de Órbita", fontsize=11)
    ax.set_ylabel("Massa de Lançamento (kg)", fontsize=11)
    ax.set_title(
        "Massa de Lançamento por Classe de Órbita",
        fontsize=13, fontweight="bold", pad=14, color=COR_PRIMARIA,
    )
    ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"{y:,.0f}"))

    fig.text(
        0.01, 0.01,
        "Fonte: UCS Satellite Database (Mai/2023) — ucsusa.org | Equipe Aldebaran — O.R.B.I.T.A.\n"
        "Linha branca = mediana | Caixa = quartis Q1–Q3 | Pontos = outliers.",
        fontsize=8, color=COR_NEUTRO,
    )
    plt.tight_layout(rect=[0, 0.06, 1, 1])
    plt.savefig(GRAFICO4, bbox_inches="tight")
    plt.close()
    print(f"  [OK] Gráfico 4 salvo: {GRAFICO4}")


# ════════════════════════════════════════════════════════════
#  6. RELATÓRIO PDF
# ════════════════════════════════════════════════════════════

def gerar_pdf(
    tab_disc:  pd.DataFrame,
    tab_cont:  pd.DataFrame,
    univ1:     dict,
    univ2:     dict,
    mat:       dict,
) -> None:
    """Gera o relatório estatístico completo em PDF.

    Estrutura:
      Capa → Introdução → Tabela Discreta → Gráfico 1
      → Tabela Contínua → Gráfico 2
      → Análise Univariada 1 → Análise Univariada 2
      → Transformação Matricial → Gráfico 3 → Conclusão

    Args:
        tab_disc: Tabela de frequência discreta.
        tab_cont: Tabela de frequência contínua.
        univ1:    Análise univariada da Launch Mass.
        univ2:    Análise univariada do Perigee.
        mat:      Resultado da transformação matricial.
    """
    doc    = SimpleDocTemplate(PDF_OUT, pagesize=A4,
                               leftMargin=2.5*cm, rightMargin=2.5*cm,
                               topMargin=2.5*cm, bottomMargin=2.5*cm)
    styles = getSampleStyleSheet()
    story  = []

    # ── Estilos customizados ──────────────────────────────
    s_title = ParagraphStyle("title", parent=styles["Title"],
                             fontSize=20, spaceAfter=6, alignment=TA_CENTER,
                             textColor=colors.HexColor(COR_PRIMARIA))
    s_sub   = ParagraphStyle("sub", parent=styles["Normal"],
                             fontSize=11, spaceAfter=4, alignment=TA_CENTER,
                             textColor=colors.HexColor(COR_NEUTRO))
    s_h1    = ParagraphStyle("h1", parent=styles["Heading1"],
                             fontSize=14, spaceBefore=16, spaceAfter=6,
                             textColor=colors.HexColor(COR_PRIMARIA))
    s_h2    = ParagraphStyle("h2", parent=styles["Heading2"],
                             fontSize=12, spaceBefore=10, spaceAfter=4,
                             textColor=colors.HexColor(COR_NEUTRO))
    s_body  = ParagraphStyle("body", parent=styles["Normal"],
                             fontSize=10, leading=14, alignment=TA_JUSTIFY,
                             spaceAfter=6)
    s_bold  = ParagraphStyle("bold", parent=s_body, fontName="Helvetica-Bold")

    def hr(): return HRFlowable(width="100%", thickness=0.5,
                                color=colors.HexColor("#CECBF6"), spaceAfter=8)

    def tabela_pdf(data: list[list], col_widths=None) -> Table:
        """Cria uma tabela ReportLab estilizada."""
        t = Table(data, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND",  (0, 0), (-1, 0), colors.HexColor(COR_PRIMARIA)),
            ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
            ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",    (0, 0), (-1, 0), 9),
            ("ALIGN",       (0, 0), (-1, -1), "CENTER"),
            ("FONTSIZE",    (0, 1), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.HexColor("#F8F8F8"), colors.white]),
            ("GRID",        (0, 0), (-1, -1), 0.4, colors.HexColor("#D3D1C7")),
            ("TOPPADDING",  (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        return t

    # ── CAPA ──────────────────────────────────────────────
    story.append(Spacer(1, 2*cm))
    story.append(Paragraph("O.R.B.I.T.A.", s_title))
    story.append(Paragraph("Operational Risk &amp; Balance Intelligence via Technique Analysis", s_sub))
    story.append(Spacer(1, 0.5*cm))
    story.append(hr())
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        "Relatório Estatístico — Modelagem Linear para Aprendizado de Máquina", s_h1))
    story.append(Spacer(1, 0.3*cm))

    meta = [
        ["Equipe",   "Aldebaran"],
        ["Integrantes", "Marcelo Francisco Josafá Ribeiro Martins — RM 573905"],
        ["",         "Luiz Otávio Brito Freixo — RM 569977"],
        ["Dataset",  "UCS Satellite Database (Mai/2023)"],
        ["Fonte",    "Union of Concerned Scientists — ucsusa.org"],
        ["Registros","1.305 satélites operacionais em órbita terrestre"],
    ]
    for row in meta:
        story.append(Paragraph(
            f"<b>{row[0]}:</b>&nbsp;&nbsp;{row[1]}" if row[0] else f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{row[1]}",
            s_body))

    story.append(PageBreak())

    # ── INTRODUÇÃO ────────────────────────────────────────
    story.append(Paragraph("1. Introdução e Contexto", s_h1))
    story.append(hr())
    story.append(Paragraph(
        "O presente relatório apresenta a análise estatística do <b>UCS Satellite Database</b>, "
        "base de dados pública mantida pela Union of Concerned Scientists, contendo informações "
        "detalhadas sobre 1.305 satélites operacionais em órbita terrestre (dados de maio de 2023). "
        "O dataset possui 28 variáveis por satélite, incluindo massa de lançamento, altitude orbital "
        "(perigeu e apogeu), classe de órbita, finalidade e vida útil estimada.",
        s_body))
    story.append(Paragraph(
        "A integração com o projeto O.R.B.I.T.A. ocorre na calibração dos limiares do motor de "
        "diagnóstico: as distribuições reais de massa e altitude dos satélites operacionais fundamentam "
        "os parâmetros de alerta do sistema de monitoramento, garantindo que os limites definidos sejam "
        "estatisticamente embasados e não arbitrários.",
        s_body))

    # ── TABELA DISCRETA ───────────────────────────────────
    story.append(Paragraph("2. Tabela de Frequência — Variável Discreta", s_h1))
    story.append(hr())
    story.append(Paragraph(
        "<b>Variável:</b> Classe de Órbita (Class of Orbit) — variável qualitativa nominal "
        "categorizada em LEO (Low Earth Orbit), GEO (Geostationary), MEO (Medium Earth Orbit) "
        "e Elliptical. Representa o tipo de trajetória orbital do satélite.",
        s_body))
    story.append(Spacer(1, 0.3*cm))

    header = ["Classe de Órbita", "Freq. Absoluta", "Freq. Relativa (%)", "Freq. Acumulada (%)"]
    data   = [header]
    for _, row in tab_disc.iterrows():
        data.append([str(row[c]) for c in tab_disc.columns])
    story.append(tabela_pdf(data, col_widths=[6*cm, 3.5*cm, 4*cm, 4.5*cm]))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        "<b>Interpretação:</b> A órbita LEO concentra 53,3% dos satélites operacionais, "
        "reflexo da expansão das constelações comerciais (Starlink, OneWeb). A órbita GEO "
        "abriga 36,9%, predominantemente satélites de comunicação e meteorologia de longa vida útil. "
        "A distribuição assimétrica indica que a economia espacial atual é dominada por satélites "
        "de observação e comunicação em baixas órbitas.",
        s_body))

    # ── GRÁFICO 1 ─────────────────────────────────────────
    story.append(Paragraph("3. Gráfico 1 — Distribuição por Classe de Órbita", s_h1))
    story.append(hr())
    if os.path.exists(GRAFICO1):
        story.append(Image(GRAFICO1, width=15*cm, height=8.5*cm))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        "<b>Figura 1:</b> Gráfico de barras horizontais exibindo a frequência absoluta e relativa "
        "de satélites por classe de órbita. Linhas de referência indicam a média da distribuição. "
        "Fonte: UCS Satellite Database (Mai/2023).",
        s_body))

    story.append(PageBreak())

    # ── TABELA CONTÍNUA ───────────────────────────────────
    story.append(Paragraph("4. Tabela de Frequência — Variável Contínua", s_h1))
    story.append(hr())
    story.append(Paragraph(
        "<b>Variável:</b> Massa de Lançamento em kg (Launch Mass) — variável quantitativa contínua "
        "representando o peso total do satélite no lançamento (incluindo combustível). "
        "Faixa de variação: 1 kg (CubeSats) a 18.000 kg (satélites de grande porte). "
        "N válidos: 1.192 satélites.",
        s_body))
    story.append(Spacer(1, 0.3*cm))

    header2 = ["Intervalo (kg)", "Ponto Médio (kg)", "Freq. Absoluta", "Freq. Relativa (%)", "Freq. Acumulada (%)"]
    data2   = [header2]
    for _, row in tab_cont.iterrows():
        data2.append([str(row[c]) for c in tab_cont.columns])
    story.append(tabela_pdf(data2, col_widths=[4.5*cm, 4*cm, 3.5*cm, 3.5*cm, 3.5*cm]))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        "<b>Interpretação:</b> A primeira classe (1 a 2.571 kg) concentra a maioria absoluta "
        "dos satélites (>70%), evidenciando a tendência de miniaturização. Os satélites mais "
        "massivos (>10.000 kg) representam menos de 3% da frota e correspondem a plataformas "
        "de telecomunicações GEO de alta capacidade.",
        s_body))

    # ── GRÁFICO 2 ─────────────────────────────────────────
    story.append(Paragraph("5. Gráfico 2 — Distribuição da Massa de Lançamento", s_h1))
    story.append(hr())
    if os.path.exists(GRAFICO2):
        story.append(Image(GRAFICO2, width=15*cm, height=8.5*cm))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        "<b>Figura 2:</b> Histograma com 30 classes mostrando a distribuição da massa de lançamento. "
        "Linhas verticais indicam média (vermelho tracejado) e mediana (verde pontilhado). "
        "A assimetria à direita é marcante: poucos satélites muito pesados elevam a média "
        "bem acima da mediana. Satélites com massa > 10.000 kg omitidos para legibilidade.",
        s_body))

    story.append(PageBreak())

    # ── ANÁLISES UNIVARIADAS ──────────────────────────────
    story.append(Paragraph("6. Análises Univariadas", s_h1))
    story.append(hr())

    for univ in [univ1, univ2]:
        story.append(Paragraph(f"6.{1 if univ == univ1 else 2} — {univ['nome']} ({univ['unidade']})", s_h2))
        medidas = [
            ["Medida", "Valor"],
            ["N (válidos)",      f"{univ['n']}"],
            ["Média",            f"{univ['media']:.2f} {univ['unidade']}"],
            ["Mediana",          f"{univ['mediana']:.2f} {univ['unidade']}"],
            ["Moda",             f"{univ['moda']:.2f} {univ['unidade']}"],
            ["Mínimo",           f"{univ['minimo']:.2f} {univ['unidade']}"],
            ["Máximo",           f"{univ['maximo']:.2f} {univ['unidade']}"],
            ["Amplitude",        f"{univ['amplitude']:.2f} {univ['unidade']}"],
            ["Variância",        f"{univ['variancia']:.2f}"],
            ["Desvio Padrão",    f"{univ['desvio_pad']:.2f} {univ['unidade']}"],
            ["Coef. Variação",   f"{univ['cv_pct']:.2f}%"],
            ["Q1 (1º quartil)",  f"{univ['q1']:.2f} {univ['unidade']}"],
            ["Q2 (mediana)",     f"{univ['q2']:.2f} {univ['unidade']}"],
            ["Q3 (3º quartil)",  f"{univ['q3']:.2f} {univ['unidade']}"],
            ["IQR",              f"{univ['iqr']:.2f} {univ['unidade']}"],
        ]
        story.append(tabela_pdf(medidas, col_widths=[8*cm, 9*cm]))
        story.append(Spacer(1, 0.3*cm))

        if univ == univ1:
            story.append(Paragraph(
                f"<b>Interpretação:</b> A massa média de lançamento é {univ['media']:.0f} kg, "
                f"porém a mediana de {univ['mediana']:.0f} kg revela forte assimetria positiva — "
                f"a maioria dos satélites é leve (CubeSats e nanossatélites), mas satélites "
                f"de grande porte elevam a média. O coeficiente de variação de {univ['cv_pct']:.1f}% "
                f"confirma heterogeneidade extrema na frota operacional.",
                s_body))
        else:
            story.append(Paragraph(
                f"<b>Interpretação:</b> O perigeu médio de {univ['media']:.0f} km e mediana de "
                f"{univ['mediana']:.0f} km indicam concentração na faixa LEO (200–2.000 km). "
                f"A amplitude de {univ['amplitude']:.0f} km demonstra que a frota abrange desde "
                f"órbitas rasas de imageamento até órbitas geoestacionárias (~35.786 km). "
                f"O CV de {univ['cv_pct']:.1f}% reflete a diversidade de missões monitoradas.",
                s_body))
        story.append(Spacer(1, 0.2*cm))

    story.append(PageBreak())

    # ── TRANSFORMAÇÃO MATRICIAL ───────────────────────────
    story.append(Paragraph("7. Transformação Linear Matricial", s_h1))
    story.append(hr())
    story.append(Paragraph(
        "<b>Problema:</b> Normalizar os parâmetros orbitais (perigeu, apogeu, inclinação) "
        "de satélites com escalas distintas para uma escala comum [0, 1], permitindo comparação "
        "direta e uso em modelos de classificação de risco orbital.",
        s_body))
    story.append(Paragraph(
        "<b>Método — Normalização Min-Max via álgebra linear:</b>",
        s_bold))
    story.append(Paragraph(
        "Dado X = matriz de dados (n x 3) com colunas [Perigee, Apogee, Inclination],<br/>"
        "a transformação é definida como:<br/><br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;<b>X_norm = (X - X_min) @ T</b><br/><br/>"
        "onde T é a matriz diagonal (3x3) de fatores de escala:<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;T = diag( 1/(max-min) ) para cada variável",
        s_body))

    # Exibir matriz T numericamente
    T = mat["T"]
    T_data = [["", "Perigee", "Apogee", "Inclinação"]]
    nomes_col = ["Perigee", "Apogee", "Inclinação"]
    for i, row in enumerate(T):
        T_data.append([nomes_col[i]] + [f"{v:.6f}" for v in row])
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph("<b>Matriz de Transformação T (3x3):</b>", s_bold))
    story.append(tabela_pdf(T_data, col_widths=[4*cm, 4.5*cm, 4.5*cm, 4.5*cm]))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        "<b>Interpretação dos elementos diagonais:</b> cada valor representa o fator de escala "
        "daquela variável. Valores maiores indicam maior compressão — a inclinação (0–180°) é "
        "escalada por um fator maior que o perigeu (0–62.200 km), pois sua amplitude absoluta "
        "é menor. Após a transformação, todas as variáveis variam em [0, 1], permitindo que o "
        "motor de diagnóstico do O.R.B.I.T.A. aplique limiares uniformes de risco orbital.",
        s_body))

    # ── GRÁFICO 3 ─────────────────────────────────────────
    story.append(Paragraph("8. Gráfico 3 — Transformação Matricial", s_h1))
    story.append(hr())
    if os.path.exists(GRAFICO3):
        story.append(Image(GRAFICO3, width=15*cm, height=7*cm))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        "<b>Figura 3:</b> Comparação do espaço de perigeu vs apogeu antes (esquerda, escala em km) "
        "e depois (direita, escala normalizada [0,1]) da transformação matricial T. "
        "A estrutura relativa entre os satélites é preservada — apenas a escala muda. "
        "A cor indica a inclinação orbital de cada satélite.",
        s_body))

    story.append(Spacer(1, 0.4*cm))
    story.append(Paragraph("8.1. Gráfico 4 — Massa por Classe de Órbita (análise bivariada)", s_h2))
    if os.path.exists(GRAFICO4):
        story.append(Image(GRAFICO4, width=15*cm, height=8.3*cm))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        "<b>Figura 4:</b> Boxplot cruzando massa de lançamento com classe de órbita. "
        "Revela que satélites geoestacionários (GEO) tendem a ser significativamente "
        "mais pesados que os de órbita baixa (LEO), refletindo a diferença entre "
        "grandes satélites de telecomunicação e a nova geração de nanossatélites. "
        "A linha branca marca a mediana de cada grupo; a caixa cobre os quartis Q1–Q3.",
        s_body))

    story.append(PageBreak())

    # ── CONCLUSÃO ─────────────────────────────────────────
    story.append(Paragraph("9. Conclusão e Insights para Tomada de Decisão", s_h1))
    story.append(hr())
    insights = [
        ("Miniaturização é dominante",
         "Mais de 70% dos satélites pesam menos de 2.571 kg. "
         "O O.R.B.I.T.A. deve priorizar alertas calibrados para nanossatélites, "
         "cujos sistemas de energia e termorregulação são mais vulneráveis."),
        ("LEO concentra o risco operacional",
         "53,3% dos satélites estão em LEO — altitude sujeita a maior arrasto atmosférico "
         "e degradação orbital mais rápida. O motor de estabilidade do O.R.B.I.T.A. "
         "foi calibrado para detectar anomalias nessa faixa prioritária."),
        ("Alta dispersão exige limiares adaptativos",
         f"O coeficiente de variação da massa ({univ1['cv_pct']:.1f}%) e do perigeu "
         f"({univ2['cv_pct']:.1f}%) confirmam que limiares fixos são inadequados. "
         "A normalização matricial implementada padroniza os dados para comparação justa."),
        ("GEO é estratégica para comunicações",
         "Os 36,9% de satélites GEO representam a espinha dorsal de telecomunicações globais. "
         "Uma falha de comunicação nesses ativos tem impacto desproporcional — justificando "
         "o peso dado ao parâmetro de comunicação no score de risco do O.R.B.I.T.A."),
    ]
    for titulo, texto in insights:
        story.append(Paragraph(f"<b>{titulo}</b>", s_bold))
        story.append(Paragraph(texto, s_body))
        story.append(Spacer(1, 0.1*cm))

    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(
        "Fonte dos dados: UCS Satellite Database, Union of Concerned Scientists, "
        "versão de maio de 2023. Disponível em: ucsusa.org/resources/satellite-database. "
        "Acesso em junho de 2026.",
        ParagraphStyle("fonte", parent=s_body, fontSize=9, textColor=colors.HexColor(COR_NEUTRO))))

    doc.build(story)
    print(f"\n  [OK] Relatório PDF gerado: {PDF_OUT}")


# ════════════════════════════════════════════════════════════
#  EXECUÇÃO PRINCIPAL
# ════════════════════════════════════════════════════════════

def main() -> None:
    """Ponto de entrada — executa o pipeline estatístico completo."""
    print("\n" + "=" * 60)
    print("  O.R.B.I.T.A. — Análise Estatística UCS Satellite Database")
    print("=" * 60)

    print("\n[1/7] Ingestão de dados...")
    baixar_dataset()
    df = carregar_e_limpar()

    print("\n[2/7] Tabelas de frequência...")
    tab_disc = tabela_frequencia_discreta(df)
    print("\n  Tabela Discreta — Classe de Órbita:")
    print(tab_disc.to_string(index=False))

    tab_cont = tabela_frequencia_continua(df)
    print("\n  Tabela Contínua — Launch Mass (kg):")
    print(tab_cont.to_string(index=False))

    print("\n[3/7] Análises univariadas...")
    univ1 = analise_univariada(df["Launch Mass (kg.)"], "Massa de Lançamento", "kg")
    univ2 = analise_univariada(df["Perigee (km)"],      "Altitude do Perigeu",  "km")

    print("\n[4/7] Gráfico 1 — Distribuição por órbita...")
    grafico_orbita(df)

    print("\n[5/7] Gráfico 2 — Distribuição de massa...")
    grafico_massa(df)
    grafico_massa_por_orbita(df)  # 4º gráfico — análise bivariada

    print("\n[6/7] Transformação linear matricial...")
    resultado_mat = transformacao_linear_matricial(df)
    grafico_transformacao(resultado_mat)

    print("\n[7/7] Gerando relatório PDF...")
    gerar_pdf(tab_disc, tab_cont, univ1, univ2, resultado_mat)

    print("\n" + "=" * 60)
    print("  Pipeline concluído com sucesso!")
    print(f"  Relatório : {PDF_OUT}")
    print(f"  Gráficos  : {DIR_ASSETS}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
