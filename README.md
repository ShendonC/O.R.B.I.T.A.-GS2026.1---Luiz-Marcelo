# O.R.B.I.T.A. — Mission Control AI

**Operational Risk & Balance Intelligence via Technique Analysis**

> Sistema inteligente de monitoramento e análise de missão espacial experimental.  
> Equipe Aldebaran | Global Solution FIAP 2026.1

---

## Visão Geral

O O.R.B.I.T.A. é uma plataforma de controle de missão que monitora dados de telemetria espacial em tempo real, classifica riscos operacionais, gerencia sistemas energéticos e aciona um agente de inteligência artificial para análise de situações críticas.

```
[Telemetria JSON] → [Motor de Diagnóstico] → [Gestor de Energia] → [Agente ARIA (IA)]
                                                                  → [HUD Gráfica + Voz]
                                                                  → [Relatório Terminal]
```

O projeto integra cinco frentes acadêmicas em um único sistema: Pensamento Computacional, Estrutura de Dados (DSA), Soluções em Energias Renováveis, Prompt & Inteligência Artificial, e Modelagem (Linear e Matemática).

---

## Equipe Aldebaran

| Nome | RM |
|------|----|
| Luiz Otávio Brito Freixo | 569977 |
| Marcelo Francisco Josafá Ribeiro Martins | 573905 |

---

## Estrutura do Projeto

```
O.R.B.I.T.A./
├── mission_control.py      # Motor principal — Pensamento Comp. + DSA
├── energy_manager.py       # Gestão energética — Energias Renováveis
├── ai_copilot.py           # Agente ARIA — Prompt & AI
├── hud.py                  # Interface gráfica cyberpunk — CustomTkinter
├── voice.py                # Síntese de voz da ARIA (text-to-speech)
├── stats_analysis.py       # Análise estatística — Modelagem Linear
├── math_models.py          # Modelos P(t) e R(T) — Modelagem Matemática
├── diagnostico_ia.py       # Diagnóstico da conexão com a IA
│
├── data/
│   ├── telemetria.json     # Mock API com 6 ciclos da missão
│   └── ucs_satellites.csv  # Base de satélites (Modelagem Linear)
│
├── docs/                   # Relatórios técnicos (.docx) e PDFs
├── assets/                 # Gráficos gerados pelos scripts de modelagem
│
├── .env.example            # Template para variáveis de ambiente
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Instalação e Execução

### 1. Pré-requisitos

- Python 3.10 ou superior
- pip

### 2. Instalar dependências

```bash
pip install -r requirements.txt
```

### 3. Configurar a API de IA (opcional)

```bash
# Copiar o template
cp .env.example .env
```

Edite o arquivo `.env` com sua chave do Google AI Studio (gratuita, sem cartão):

```
GEMINI_API_KEY=sua_chave_aqui
GEMINI_MODEL=gemini-2.5-flash
```

A chave é obtida em https://aistudio.google.com/apikey. Sem ela, o sistema opera em **modo mock** com respostas locais pré-estruturadas — isso não afeta nenhuma outra funcionalidade. Para confirmar a conexão, rode `python diagnostico_ia.py`.

> O sistema também é compatível com OpenRouter: basta usar `OPENROUTER_API_KEY` e `OPENROUTER_MODEL` no `.env`.

### 4. Executar

**Interface gráfica (HUD):**
```bash
python hud.py
```

**Terminal (modo compliance acadêmico):**
```bash
python mission_control.py
```

**Análise estatística (gera PDF e gráficos):**
```bash
python stats_analysis.py
```

**Modelagem matemática (gera gráficos P(t) e R(T) + relatório):**
```bash
python math_models.py
```

---

## Regras de Alerta

| Métrica | NORMAL | ATENÇÃO | CRÍTICO |
|---------|--------|---------|---------|
| Temperatura | 18–30°C | <18°C ou 30–35°C | >35°C |
| Comunicação | ≥60% | 30–59% | <30% |
| Bateria | ≥50% | 20–49% | <20% |
| Oxigênio | ≥90% | 80–89% | <80% |
| Estabilidade | ≥70% | 40–69% | <40% |

**Pontuação:** NORMAL=0 | ATENÇÃO=1 | CRÍTICO=2 (máx 10/ciclo)

**Classificação do ciclo:** 0–2=Estável | 3–5=Atenção | 6–10=Crítica

A verificação automática também aplica as condições do enunciado de DSA: temperatura > 80, energia < 20 e comunicação = 0.

---

## Lógica Booleana de Alerta

Variáveis de entrada (binárias):
- **A** = Falha de comunicação (comunicação < 30%)
- **B** = Temperatura crítica (temperatura > 35°C)
- **C** = Baixo nível de energia (bateria < 20%)
- **D** = Falha operacional (estabilidade < 40%)
- **E** = Suporte de vida crítico (oxigênio < 80%)

**Expressão:** `X = A OR B OR C OR D OR E`  
**Notação booleana:** `X = A + B + C + D + E`

X=1 aciona o alerta principal do sistema.

---

## Agente ARIA

O sistema aciona automaticamente o agente **ARIA** (Autonomous Risk Intelligence Agent) em ciclos classificados como CRÍTICOS. O agente:

1. Recebe o contexto da missão como injeção de contexto no prompt
2. Analisa os riscos em cascata entre sistemas
3. Recomenda protocolos de contingência priorizados
4. Resume o diagnóstico em uma frase falada (voz, estilo assistente de bordo)

A ARIA também aceita **conversa livre** pelo campo de mensagem da HUD, respondendo perguntas sobre a missão ou qualquer outro assunto. Os parâmetros do modelo (temperatura 0.4, top_p 0.9) são ajustados para respostas técnicas e consistentes.

---

## Dataset (Modelagem Linear)

**UCS Satellite Database** — Union of Concerned Scientists  
Fonte: https://ucsusa.org/resources/satellite-database  
Versão: Maio de 2023 | 1.305 satélites operacionais

Análises realizadas:
- Tabela de frequência discreta: Classe de Órbita (LEO/GEO/MEO/Elliptical)
- Tabela de frequência contínua: Massa de Lançamento (kg)
- Análise univariada: Launch Mass e Altitude do Perigeu
- Análise bivariada: Massa por classe de órbita (boxplot)
- Transformação linear matricial: normalização Min-Max dos parâmetros orbitais

---

## Modelagem Matemática

Dois modelos contínuos descrevem fenômenos físicos da missão:

- **P(t) = A·t²·e^(−k·t)** — pressão aerodinâmica sobre o foguete. O ponto de máxima pressão (Max Q) é encontrado analiticamente pela derivada, em t* = 2/k = 25s.
- **R(T) = R_min + (1−R_min)/(1+e^(c·(T−T0)))** — risco de falha por temperatura, modelado por uma função logística que respeita o intervalo de probabilidade [0, 1] e tende a um risco residual mínimo (assíntota).

---

## Relatórios Técnicos

A pasta `docs/` contém um relatório técnico (`.docx`) para cada disciplina, explicando as decisões de projeto e a lógica adotada, além dos relatórios em PDF da Modelagem Linear e Matemática.

---

## Repositório

**GitHub:** https://github.com/ShendonC/O.R.B.I.T.A.-GS2026.1---Luiz-Marcelo/tree/main
