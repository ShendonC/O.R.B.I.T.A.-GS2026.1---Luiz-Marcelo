# O.R.B.I.T.A. — Mission Control AI

**Operational Risk & Balance Intelligence via Technique Analysis**

> Sistema inteligente de monitoramento e análise de missão espacial experimental.  
> Equipe Aldebaran | Global Solution FIAP 2026.1

---

## Visão Geral

O O.R.B.I.T.A. é uma plataforma de controle de missão que monitora dados de telemetria espacial em tempo real, classifica riscos operacionais, gerencia sistemas energéticos e aciona um agente de inteligência artificial para análise de situações críticas.

```
[Telemetria JSON] → [Motor de Diagnóstico] → [Gestor de Energia] → [Agente ARIA (IA)]
                                                                  → [HUD Gráfica]
                                                                  → [Relatório Terminal]
```

---

## Equipe

| Nome | RM |
|------|----|
| Marcelo Francisco Josafá Ribeiro Martins | 573905 |
| Luiz Otávio Brito Freixo | 569977 |

---

## Estrutura do Projeto

```
orbita-mission-control/
├── mission_control.py      # Motor principal — Pensamento Comp. + DSA
├── energy_manager.py       # Gestão energética — Energias Renováveis
├── ai_copilot.py           # Agente ARIA — Prompt & AI
├── hud.py                  # Interface gráfica — CustomTkinter
├── stats_analysis.py       # Análise estatística — Modelagem Linear
│
├── data/
│   └── telemetria.json     # Mock API com 6 ciclos da missão
│
├── docs/
│   └── relatorio_estatistico_orbita.pdf
│
├── assets/                 # Gráficos gerados pelo stats_analysis.py
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

# Editar .env com sua chave do Hugging Face
# HF_API_KEY=hf_suachaveaqui
```

Sem a chave, o sistema opera em **modo mock** com respostas pré-geradas. Isso não afeta nenhuma outra funcionalidade.

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

---

## Lógica Booleana (Computer Science)

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

1. Recebe o contexto JSON do ciclo como injeção de contexto
2. Analisa os riscos em cascata entre sistemas
3. Prevê o sistema com maior probabilidade de falha
4. Gera protocolo de contingência priorizado

**Para usar a API real:** configure `HF_API_KEY` no arquivo `.env` e defina `MODO_MOCK = False` no `ai_copilot.py`.

---

## Dataset (Modelagem Linear)

**UCS Satellite Database** — Union of Concerned Scientists  
Fonte: https://ucsusa.org/resources/satellite-database  
Versão: Maio de 2023 | 1.305 satélites operacionais

Análises realizadas:
- Tabela de frequência discreta: Classe de Órbita (LEO/GEO/MEO/Elliptical)
- Tabela de frequência contínua: Massa de Lançamento (kg)
- Análise univariada: Launch Mass e Altitude do Perigeu
- Transformação linear matricial: normalização Min-Max dos parâmetros orbitais

---

## Links

- **GitHub:** https://github.com/ShendonC/O.R.B.I.T.A.-GS2026.1---Luiz-Marcelo
- **Vídeo Pitch:** [PREENCHER]
