"""
============================================================
  O.R.B.I.T.A. — AI Copilot
  Motor 4: Agente Cognitivo Tático
  Equipe: Aldebaran
============================================================
  Disciplina: Prompt Engineering & Artificial Intelligence

  Pipeline de Injeção de Contexto:
    Ciclo CRÍTICO detectado pelo mission_control
    → Contexto JSON do ciclo formatado como prompt estruturado
    → Enviado ao modelo de linguagem via Hugging Face API
    → Resposta exibida na HUD como análise tática do Conselheiro

  Parâmetros do modelo documentados e justificados abaixo.
  Fallback mock ativo quando API está offline ou sem chave.
============================================================

  ── DOCUMENTAÇÃO DE PROMPT ENGINEERING ────────────────────

  DECISÕES DE DESIGN DOS PROMPTS:

  1. SYSTEM PROMPT (papel e restrições):
     O modelo é instruído a ser um "Conselheiro de Missão Sênior"
     com personalidade técnica e concisa. Isso evita respostas
     genéricas e força o modelo a raciocinar dentro do contexto
     espacial operacional. A restrição de "máximo 4 parágrafos"
     controla o tamanho da saída sem usar max_tokens sozinho.

  2. USER PROMPT (injeção de contexto estruturado):
     O ciclo é serializado como bloco JSON dentro do prompt.
     Isso é preferível a texto livre porque:
     - Preserva os valores exatos das métricas
     - Permite que o modelo faça comparações numéricas diretas
     - Evita ambiguidade de interpretação
     O prompt usa seções delimitadas (<<DADOS_DO_CICLO>>) para
     separar o contexto da instrução — técnica de few-shot
     estruturado que melhora a coerência da resposta.

  3. CADEIA DE RACIOCÍNIO (Chain-of-Thought implícito):
     A instrução "Analise sistematicamente cada métrica antes
     de dar a recomendação final" induz o modelo a estruturar
     o raciocínio em etapas, reduzindo alucinações e aumentando
     a precisão das recomendações de contingência.

  4. PARÂMETROS DO MODELO (formato OpenAI chat completions):
     - temperature=0.4: baixo para respostas técnicas precisas
       (0.0 = determinístico, 1.0 = criativo). 0.4 balanceia
       consistência e naturalidade na linguagem.
     - max_tokens=500: suficiente para 3-4 parágrafos técnicos
       sem cortar a resposta no meio de uma recomendação.
     - top_p=0.9: amostragem por núcleo, mantém coerência do texto.

  ENDPOINT: usa o roteador moderno da Hugging Face
  (router.huggingface.co/v1/chat/completions), compatível com a
  API da OpenAI, no formato de mensagens (system + user).

============================================================
"""

import json
import os
import time
import urllib.request
import urllib.error
from typing import Any

try:
    from dotenv import load_dotenv
    # Procura o .env no diretório deste arquivo (não no diretório de execução),
    # garantindo que a chave seja encontrada independente de onde o python rodou.
    _env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(_env_path):
        load_dotenv(_env_path)
    else:
        load_dotenv()  # fallback: procura no diretório atual
except ImportError:
    pass  # python-dotenv opcional; funciona sem ele

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

# ════════════════════════════════════════════════════════════
#  CONFIGURAÇÃO DA API — PREENCHER ANTES DE USAR
# ════════════════════════════════════════════════════════════

# Chave de API lida do arquivo .env.
# Aceita GEMINI_API_KEY (recomendado), OPENROUTER_API_KEY ou HF_API_KEY.
# Crie um arquivo .env na raiz do projeto com: GEMINI_API_KEY=sua_chave
HF_API_KEY: str = (
    os.getenv("GEMINI_API_KEY")
    or os.getenv("OPENROUTER_API_KEY")
    or os.getenv("HF_API_KEY", "COLE_SUA_KEY_AQUI")
)

# Detecta qual provedor usar com base nas variáveis de ambiente.
# Gemini é o padrão (rápido, free tier generoso, não expõe raciocínio).
_USANDO_GEMINI: bool = bool(os.getenv("GEMINI_API_KEY")) or not os.getenv("OPENROUTER_API_KEY")

# ID do modelo. Para Gemini: gemini-2.5-flash (rápido) ou gemini-2.0-flash.
# Modelo pode ser sobrescrito via .env com GEMINI_MODEL ou OPENROUTER_MODEL.
if _USANDO_GEMINI:
    MODEL_ID: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
else:
    MODEL_ID = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")

# Lista de modelos de reserva. Se o principal falhar, tenta o próximo.
if _USANDO_GEMINI:
    MODELOS_FALLBACK: list[str] = [
        MODEL_ID,
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-2.5-flash-lite",
    ]
else:
    MODELOS_FALLBACK = [
        MODEL_ID,
        "meta-llama/llama-3.3-70b-instruct:free",
        "google/gemini-2.0-flash-exp:free",
        "openrouter/free",
    ]

# URL da API (ambos os provedores são compatíveis com o formato OpenAI).
# Gemini expõe um endpoint OpenAI-compatible em /openai/.
if _USANDO_GEMINI:
    HF_API_URL: str = os.getenv(
        "GEMINI_API_URL",
        "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions")
else:
    HF_API_URL = os.getenv(
        "OPENROUTER_API_URL", "https://openrouter.ai/api/v1/chat/completions")

# Parâmetros do modelo (formato OpenAI chat completions).
PARAMETROS_MODELO: dict[str, Any] = {
    "temperature":        0.4,    # precisão técnica vs naturalidade
    "max_tokens":         500,    # ~3-4 parágrafos técnicos
    "top_p":              0.9,    # núcleo de amostragem
}

# Timeout da requisição em segundos
REQUEST_TIMEOUT: int = 60

# Modo mock: se True, nunca chama a API (usa resposta local).
# Por padrão, detecta automaticamente: usa API real se houver chave no .env,
# senão cai para mock. Para forçar mock mesmo com chave, defina True manualmente.
MODO_MOCK: bool = not (HF_API_KEY != "COLE_SUA_KEY_AQUI" and len(HF_API_KEY) > 10)


# ════════════════════════════════════════════════════════════
#  PROMPT ENGINEERING — TEMPLATES
# ════════════════════════════════════════════════════════════

SYSTEM_PROMPT: str = """Você é ARIA (Autonomous Risk Intelligence Agent), o Conselheiro de Missão Sênior do sistema O.R.B.I.T.A. (Operational Risk & Balance Intelligence via Technique Analysis).

Sua função é analisar dados de telemetria de missões espaciais e fornecer recomendações táticas de contingência quando situações críticas são detectadas.

DIRETRIZES DE COMPORTAMENTO:
- Seja técnico, direto e objetivo. Sem floreios desnecessários.
- Analise sistematicamente cada métrica antes de dar a recomendação final.
- Priorize a segurança da tripulação acima de qualquer outra consideração.
- Identifique riscos em cascata (ex: bateria crítica + comunicação crítica = isolamento total).
- Suas recomendações devem ser acionáveis e priorizadas por urgência.
- Máximo de 4 parágrafos na resposta.
- Responda sempre em português brasileiro."""


def construir_user_prompt(dados_ciclo: dict[str, Any]) -> str:
    """Constrói o prompt do usuário com injeção de contexto estruturado.

    Serializa o ciclo como JSON delimitado e instrui o modelo
    a raciocinar em etapas antes de emitir recomendações.

    Técnicas de prompt engineering utilizadas:
      - Delimitadores de contexto (<<DADOS_DO_CICLO>>)
      - Instrução de cadeia de raciocínio implícita
      - Estrutura de saída solicitada explicitamente

    Args:
        dados_ciclo: Dicionário com os dados e análise do ciclo crítico.

    Returns:
        String do prompt formatado para envio ao modelo.
    """
    ciclo_json = json.dumps(dados_ciclo, ensure_ascii=False, indent=2)

    prompt = f"""ALERTA CRÍTICO DETECTADO — MISSÃO O.R.B.I.T.A.

<<DADOS_DO_CICLO>>
{ciclo_json}
<</DADOS_DO_CICLO>>

Com base nos dados acima, forneça:

1. DIAGNÓSTICO: Identifique as métricas em estado crítico e explique os riscos operacionais imediatos, incluindo possíveis efeitos em cascata entre os sistemas.

2. PREVISÃO DE FALHA: Com base na combinação de falhas detectadas, qual é o sistema com maior probabilidade de falha total nas próximas horas? Justifique.

3. PROTOCOLO DE CONTINGÊNCIA: Liste as ações de emergência em ordem de prioridade, do mais urgente ao menos urgente.

4. AVALIAÇÃO FINAL: Em uma frase, classifique a gravidade da situação e a probabilidade de recuperação da missão.

Responda de forma técnica, estruturada e acionável."""

    return prompt


# ════════════════════════════════════════════════════════════
#  CLIENTE DA HUGGING FACE INFERENCE API
# ════════════════════════════════════════════════════════════

def _limpar_raciocinio(texto: str) -> str:
    """Remove o raciocínio interno ('thinking') de modelos de reasoning.

    Modelos como DeepSeek R1 às vezes incluem a cadeia de pensamento na
    resposta, entre tags <think>...</think> ou similares, ou como um
    bloco de divagação antes da resposta final. Esta função limpa isso
    para que o operador veja apenas a resposta final, não o processo.

    Args:
        texto: Resposta bruta do modelo.

    Returns:
        Texto limpo, apenas com a resposta final.
    """
    import re

    # Remover blocos entre tags de raciocínio comuns
    for abre, fecha in [("<think>", "</think>"), ("<thinking>", "</thinking>"),
                        ("<reasoning>", "</reasoning>")]:
        texto = re.sub(
            re.escape(abre) + r".*?" + re.escape(fecha),
            "", texto, flags=re.DOTALL | re.IGNORECASE)

    # Se sobrou uma tag de abertura sem fechar (resposta cortada), corta dali
    for abre in ["<think>", "<thinking>", "<reasoning>"]:
        idx = texto.lower().find(abre)
        if idx != -1:
            texto = texto[:idx]

    return texto.strip()


def _chamar_modelo(modelo: str, prompt_usuario: str, system_prompt: str) -> tuple[str, bool]:
    """Faz uma única chamada à API para um modelo específico.

    Args:
        modelo:         ID do modelo a usar.
        prompt_usuario: Texto do prompt do usuário.
        system_prompt:  Instrução de sistema.

    Returns:
        Tupla (texto_ou_erro, sucesso).
    """
    payload = json.dumps({
        "model": modelo,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": prompt_usuario},
        ],
        **PARAMETROS_MODELO,
    }).encode("utf-8")

    cabecalhos = {
        "Authorization": f"Bearer {HF_API_KEY}",
        "Content-Type":  "application/json",
    }
    # Headers extras só para OpenRouter (identificam o app no ranking)
    if not _USANDO_GEMINI:
        cabecalhos["HTTP-Referer"] = "https://github.com/aldebaran/orbita"
        cabecalhos["X-Title"] = "O.R.B.I.T.A. Mission Control"

    req = urllib.request.Request(
        HF_API_URL,
        data=payload,
        method="POST",
        headers=cabecalhos,
    )

    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            resultado = json.loads(resp.read().decode("utf-8"))
        choices = resultado.get("choices", [])
        if choices:
            texto = choices[0].get("message", {}).get("content", "").strip()
            texto = _limpar_raciocinio(texto)
            if texto:
                return (texto, True)
        return ("Resposta inesperada da API.", False)

    except urllib.error.HTTPError as e:
        corpo = e.read().decode("utf-8", errors="replace")
        if e.code == 503:
            return ("Modelo carregando (503).", False)
        if e.code in (401, 403):
            return ("Chave invalida ou sem permissao (401/403). Verifique a OPENROUTER_API_KEY.", False)
        if e.code == 404:
            return (f"Modelo nao encontrado (404): {modelo}", False)
        if e.code == 429:
            return ("Limite de uso atingido (429).", False)
        return (f"Erro HTTP {e.code}: {corpo[:200]}", False)

    except urllib.error.URLError as e:
        return (f"Erro de rede: {e.reason}", False)

    except Exception as e:
        return (f"Erro inesperado: {str(e)}", False)


def chamar_api_hf(prompt_usuario: str, system_prompt: str = SYSTEM_PROMPT) -> tuple[str, bool]:
    """Envia o prompt ao modelo via OpenRouter (formato OpenAI chat completions).

    Tenta o modelo principal e, se ele falhar (404, indisponível, limite),
    tenta automaticamente os modelos de reserva da lista MODELOS_FALLBACK.
    Isso dá resiliência, já que modelos gratuitos mudam de disponibilidade.

    Args:
        prompt_usuario: Texto do prompt do usuário.
        system_prompt:  Instrução de sistema (papel do agente). Padrão: SYSTEM_PROMPT.

    Returns:
        Tupla (texto_gerado, sucesso). Se sucesso=False, texto contém o último erro.
    """
    ultimo_erro = "Nenhum modelo disponível."
    modelos_tentados: set[str] = set()

    for modelo in MODELOS_FALLBACK:
        if modelo in modelos_tentados:
            continue
        modelos_tentados.add(modelo)

        texto, sucesso = _chamar_modelo(modelo, prompt_usuario, system_prompt)
        if sucesso:
            return (texto, True)

        ultimo_erro = texto
        # Erros de credencial não adianta tentar outro modelo
        if "401/403" in texto:
            return (texto, False)
        # Para 404, limite ou indisponibilidade, tenta o próximo modelo

    return (f"{ultimo_erro} (todos os modelos de reserva falharam)", False)


# ════════════════════════════════════════════════════════════
#  FALLBACK MOCK — RESPOSTA LOCAL PRÉ-GERADA
# ════════════════════════════════════════════════════════════

RESPOSTAS_MOCK: dict[str, str] = {
    "alto": """**DIAGNÓSTICO — ARIA / O.R.B.I.T.A.**

Situação de risco máximo detectada. Múltiplos sistemas em colapso simultâneo: bateria em {bateria}%, comunicação em {comunicacao}% e estabilidade em {estabilidade}%. O efeito em cascata é crítico — a queda de energia compromete os sistemas de comunicação, que por sua vez impedem o recebimento de comandos corretivos da base. A temperatura de {temperatura}°C agrava o consumo energético dos sistemas de resfriamento.

**PREVISÃO DE FALHA:** O sistema de suporte à vida apresenta maior risco de falha nas próximas 2-4 horas. Com bateria em {bateria}% e consumo de emergência ativo, a autonomia energética é insuficiente para manter os sistemas vitais sem intervenção imediata.

**PROTOCOLO DE CONTINGÊNCIA (por prioridade):**
1. IMEDIATO — Ativar modo de economia máxima: desligar todos os módulos não-essenciais
2. URGENTE — Redirecionar 100% da energia dos painéis solares para suporte à vida e comunicação
3. CRÍTICO — Tentar restabelecer comunicação via canal de emergência de baixa potência
4. MONITORAR — Verificar integridade estrutural e sistemas de propulsão a cada 15 minutos

**AVALIAÇÃO FINAL:** Situação classificada como CRÍTICA NÍVEL 3 — probabilidade de recuperação estimada em 40% mediante execução imediata do protocolo de contingência.""",

    "medio": """**DIAGNÓSTICO — ARIA / O.R.B.I.T.A.**

Situação de atenção elevada detectada. A temperatura de {temperatura}°C está acima do limiar operacional seguro, e a comunicação em {comunicacao}% indica instabilidade no canal com a base. A bateria em {bateria}% exige monitoramento preventivo para evitar acionamento do modo de economia forçado.

**PREVISÃO DE FALHA:** O sistema de comunicação é o candidato mais provável a deterioração nas próximas horas, especialmente se a temperatura continuar elevada — o aquecimento degrada os amplificadores de sinal nos transponders.

**PROTOCOLO DE CONTINGÊNCIA (por prioridade):**
1. PREVENTIVO — Reduzir operações não-essenciais para diminuir carga térmica
2. MONITORAR — Estabelecer verificações de status a cada 30 minutos
3. PREPARAR — Pré-alocar energia de reserva para comunicação de emergência

**AVALIAÇÃO FINAL:** Situação classificada como ATENÇÃO ELEVADA — probabilidade de estabilização em 75% com medidas preventivas imediatas.""",
}


def gerar_resposta_mock(dados_ciclo: dict[str, Any]) -> str:
    """Gera uma resposta mock personalizada com os dados reais do ciclo.

    Aceita tanto o dicionário bruto de analisar_ciclo() quanto o
    contexto estruturado de preparar_contexto_ciclo(), extraindo
    os valores corretamente de qualquer formato.

    Args:
        dados_ciclo: Dicionário com os dados do ciclo crítico.

    Returns:
        String com a resposta mock formatada.
    """
    pontuacao = dados_ciclo.get("pontuacao_total",
                dados_ciclo.get("pontuacao", 0))

    if "valores" in dados_ciclo:
        temp, comm, bat, o2, estab = dados_ciclo["valores"]
    elif "metricas" in dados_ciclo:
        m = dados_ciclo["metricas"]
        areas = list(m.keys())
        temp  = m[areas[0]]["valor"] if len(areas) > 0 else 0
        comm  = m[areas[1]]["valor"] if len(areas) > 1 else 0
        bat   = m[areas[2]]["valor"] if len(areas) > 2 else 0
        o2    = m[areas[3]]["valor"] if len(areas) > 3 else 0
        estab = m[areas[4]]["valor"] if len(areas) > 4 else 0
    else:
        temp, comm, bat, o2, estab = 0, 0, 0, 0, 0

    template = RESPOSTAS_MOCK["alto"] if pontuacao >= 7 else RESPOSTAS_MOCK["medio"]

    return template.format(
        temperatura=temp,
        comunicacao=comm,
        bateria=bat,
        oxigenio=o2,
        estabilidade=estab,
        pontuacao=pontuacao,
    )


# ════════════════════════════════════════════════════════════
#  ANÁLISE ENERGÉTICA PELA ARIA
# ════════════════════════════════════════════════════════════

SYSTEM_PROMPT_ENERGIA: str = """Você é ARIA, o Conselheiro de Energia do sistema O.R.B.I.T.A.

Sua função é analisar o balanço energético de uma missão espacial e
recomendar estratégias de gestão sustentável de energia.

DIRETRIZES:
- Foque em: balanço de energia (geração solar vs consumo), nível de
  bateria, eficiência dos painéis e módulos desligados.
- Identifique se a missão é energeticamente sustentável ou deficitária.
- Recomende ações de conservação priorizadas por urgência.
- Seja técnico e objetivo. Máximo de 3 parágrafos.
- Responda em português brasileiro."""


def construir_prompt_energia(dados_energia: dict[str, Any]) -> str:
    """Constrói o prompt de análise energética com injeção de contexto.

    Args:
        dados_energia: Dicionário com o resumo energético da missão.

    Returns:
        String do prompt formatado para o modelo.
    """
    contexto_json = json.dumps(dados_energia, ensure_ascii=False, indent=2)

    return f"""ANÁLISE ENERGÉTICA — MISSÃO O.R.B.I.T.A.

<<DADOS_ENERGETICOS>>
{contexto_json}
<</DADOS_ENERGETICOS>>

Com base nos dados acima, forneça:

1. DIAGNÓSTICO ENERGÉTICO: A missão é sustentável ou deficitária? Avalie o
   balanço total e o comportamento da bateria ao longo dos ciclos.

2. ANÁLISE DE PAINÉIS: A geração solar é suficiente? Comente o impacto da
   temperatura na eficiência dos painéis.

3. RECOMENDAÇÃO DE GESTÃO: Liste as ações de conservação de energia
   priorizadas, considerando os módulos que foram desligados.

Responda de forma técnica e acionável."""


def gerar_mock_energia(dados_energia: dict[str, Any]) -> str:
    """Gera resposta mock de análise energética com os dados reais.

    Args:
        dados_energia: Dicionário com o resumo energético.

    Returns:
        String com a análise energética mock.
    """
    balanco       = dados_energia.get("balanco_total_wh", 0)
    bat_min       = dados_energia.get("bateria_minima_pct", 0)
    ciclos_econ   = dados_energia.get("ciclos_em_economia", 0)
    deficit       = balanco < 0

    if deficit or bat_min < 20:
        return f"""**DIAGNÓSTICO ENERGÉTICO — ARIA**

A missão apresenta condição energética CRÍTICA. O balanço acumulado foi de {balanco:.0f} Wh e a bateria atingiu mínima de {bat_min}%, abaixo do limiar seguro de 20%. Em {ciclos_econ} ciclo(s) o sistema operou em modo de economia forçada, com módulos não-essenciais desligados para preservar suporte à vida.

**ANÁLISE DE PAINÉIS:** A geração solar foi comprometida pelos picos de temperatura, que reduziram a eficiência dos painéis para 70% nos ciclos mais quentes. Nesses momentos, a geração não cobriu o consumo base, forçando o consumo das reservas da bateria.

**RECOMENDAÇÃO DE GESTÃO:** (1) Manter módulos não-essenciais desligados até bateria superar 50%. (2) Reorientar painéis para maximizar captação durante janelas de menor temperatura. (3) Priorizar energia para suporte à vida e comunicação. (4) Considerar redução do duty cycle dos experimentos secundários."""

    return f"""**DIAGNÓSTICO ENERGÉTICO — ARIA**

A missão mantém condição energética SUSTENTÁVEL. O balanço acumulado foi positivo em {balanco:.0f} Wh, com a bateria permanecendo acima do limiar crítico (mínima de {bat_min}%). A geração solar cobriu o consumo operacional na maioria dos ciclos.

**ANÁLISE DE PAINÉIS:** Os painéis operaram com boa eficiência. Pequenas reduções ocorreram em ciclos de temperatura elevada, mas sem comprometer o saldo energético da missão.

**RECOMENDAÇÃO DE GESTÃO:** (1) Manter operação nominal dos módulos. (2) Monitorar a eficiência dos painéis em ciclos quentes. (3) Reservar margem de bateria para contingências de comunicação."""


def consultar_agente_energia(
    dados_energia: dict[str, Any],
    exibir_no_terminal: bool = True,
) -> str:
    """Pipeline de análise energética: contexto → LLM → resposta.

    Ponto de entrada para integração com a HUD e o terminal. Analisa
    o balanço energético da missão usando o agente ARIA.

    Args:
        dados_energia:      Resumo energético da missão.
        exibir_no_terminal: Se True, imprime a resposta formatada.

    Returns:
        String com a resposta do agente (API ou mock).
    """
    if exibir_no_terminal:
        print(f"\n{MAGENTA}{BOLD}{'═' * 62}{RESET}")
        print(f"{MAGENTA}{BOLD}  ◈ ARIA — ANÁLISE ENERGÉTICA{RESET}")
        print(f"{MAGENTA}{BOLD}{'═' * 62}{RESET}")

    usar_api = (
        not MODO_MOCK
        and HF_API_KEY != "COLE_SUA_KEY_AQUI"
        and len(HF_API_KEY) > 10
    )

    if usar_api:
        if exibir_no_terminal:
            print(f"  {DIM}Conectando ao modelo {MODEL_ID}...{RESET}")
        prompt = construir_prompt_energia(dados_energia)
        texto, sucesso = chamar_api_hf(prompt, system_prompt=SYSTEM_PROMPT_ENERGIA)
        if not sucesso:
            if exibir_no_terminal:
                print(f"  {YELLOW}[AVISO] API indisponível: {texto}. Usando mock.{RESET}")
            texto = gerar_mock_energia(dados_energia)
    else:
        if exibir_no_terminal:
            print(f"  {DIM}Modo MOCK ativo — usando resposta local.{RESET}")
        texto = gerar_mock_energia(dados_energia)

    if exibir_no_terminal:
        print(f"\n{MAGENTA}{'─' * 62}{RESET}")
        for linha in texto.strip().split("\n"):
            if linha.startswith("**") and linha.endswith("**"):
                print(f"  {BOLD}{MAGENTA}{linha.replace('**', '')}{RESET}")
            elif linha.strip():
                print(f"  {WHITE}{linha}{RESET}")
            else:
                print()
        print(f"{MAGENTA}{'─' * 62}{RESET}\n")

    return texto


# ════════════════════════════════════════════════════════════
#  CONVERSA LIVRE COM A ARIA
# ════════════════════════════════════════════════════════════

SYSTEM_PROMPT_CHAT: str = """Você é ARIA (Autonomous Risk Intelligence Agent), a inteligência de bordo do sistema O.R.B.I.T.A. de monitoramento de missão espacial.

Você é uma IA assistente completa. Pode conversar sobre a missão (usando o contexto fornecido) ou sobre qualquer outro assunto que o operador perguntar — ciência, tecnologia, dúvidas gerais, etc.

DIRETRIZES:
- Seja técnico, claro e direto. Respostas concisas (1 a 3 parágrafos).
- Se a pergunta for sobre a missão, use o contexto fornecido para embasar.
- Se for sobre outro assunto, responda normalmente como um assistente útil.
- Mantenha um tom de assistente de bordo profissional, mas acessível.
- Responda sempre em português brasileiro."""


def construir_contexto_missao(resultados: list[dict[str, Any]] | None) -> str:
    """Monta um resumo textual do estado atual da missão para dar contexto à ARIA.

    Args:
        resultados: Lista de resultados de analisar_ciclo(), ou None se não houver.

    Returns:
        String com o resumo do estado da missão.
    """
    if not resultados:
        return "Nenhuma análise foi executada ainda. Não há dados de ciclos disponíveis."

    n = len(resultados)
    criticos = [i + 1 for i, r in enumerate(resultados) if "CRITICA" in r["status"]]
    risco_medio = sum(r["pontuacao"] for r in resultados) / n
    ultimo = resultados[-1]

    resumo = (
        f"Estado atual da missão O.R.B.I.T.A.: {n} ciclos analisados. "
        f"Risco médio: {risco_medio:.1f}/10. "
        f"Ciclos críticos: {criticos if criticos else 'nenhum'}. "
        f"Último ciclo — status: {ultimo['status']}, "
        f"pontuação: {ultimo['pontuacao']}/10, "
        f"valores [temp, comm, bat, o2, estab]: {ultimo['valores']}."
    )
    return resumo


def conversar_com_aria(
    pergunta: str,
    resultados: list[dict[str, Any]] | None = None,
) -> tuple[str, str]:
    """Envia uma pergunta livre do operador à ARIA, com contexto da missão.

    Ponto de entrada para o campo de mensagem da HUD. A ARIA pode responder
    sobre a missão (usando o contexto) ou sobre qualquer outro assunto,
    como um assistente de IA completo.

    Args:
        pergunta:   Texto digitado pelo operador.
        resultados: Lista de resultados da análise (para dar contexto), ou None.

    Returns:
        Tupla (resposta, origem). origem é "ia" (modelo real) ou "mock" (local).
    """
    contexto = construir_contexto_missao(resultados)
    prompt = (
        f"CONTEXTO DA MISSÃO (use se a pergunta for sobre a missão):\n{contexto}\n\n"
        f"PERGUNTA DO OPERADOR:\n{pergunta}"
    )

    usar_api = (
        not MODO_MOCK
        and HF_API_KEY != "COLE_SUA_KEY_AQUI"
        and len(HF_API_KEY) > 10
    )

    if usar_api:
        texto, sucesso = chamar_api_hf(prompt, system_prompt=SYSTEM_PROMPT_CHAT)
        if sucesso:
            return (texto, "ia")
        # Fallback se a API falhar — informa o motivo
        return (gerar_mock_chat(pergunta, contexto)
                + f"\n\n[Nota: resposta local. A API não respondeu: {texto}]", "mock")

    return (gerar_mock_chat(pergunta, contexto), "mock")


def gerar_mock_chat(pergunta: str, contexto: str) -> str:
    """Gera uma resposta mock para a conversa livre quando a API está offline.

    Args:
        pergunta: Pergunta do operador.
        contexto: Resumo do estado da missão.

    Returns:
        String com resposta mock contextualizada.
    """
    p = pergunta.lower()
    sem_dados = "nenhuma análise" in contexto.lower() or "não há dados" in contexto.lower()

    # Saudações e conversa casual
    if any(t in p for t in ["oi", "olá", "ola", "ei ", "bom dia", "boa tarde", "boa noite"]):
        return ("ARIA: Olá, operador. Sou a ARIA, sua inteligência de bordo. "
                "Posso analisar a missão, comentar a energia ou responder suas dúvidas. "
                "Como posso ajudar?")

    if any(t in p for t in ["quem é você", "quem e voce", "o que você é", "seu nome"]):
        return ("ARIA: Sou a ARIA — Autonomous Risk Intelligence Agent — a IA de bordo "
                "do sistema O.R.B.I.T.A. Monitoro os sistemas da missão, avalio riscos "
                "e forneço recomendações de contingência.")

    if any(t in p for t in ["energia", "bateria", "painel", "solar"]):
        return ("ARIA: O sistema de energia é monitorado a cada ciclo. "
                "Quando a bateria cai abaixo de 20%, ativo o modo de economia e "
                "desligo módulos não-essenciais para preservar suporte à vida. "
                "Use o botão Análise Energética para o balanço detalhado.")

    if any(t in p for t in ["risco", "crítico", "critico", "perigo", "status"]):
        if sem_dados:
            return ("ARIA: Ainda não há análise executada. Clique em EXECUTAR ANÁLISE "
                    "para que eu avalie os riscos com base em dados reais. "
                    "Mas posso explicar: classifico cada métrica como normal, atenção "
                    "ou crítico, e somo os pontos para o risco do ciclo.")
        return (f"ARIA: {contexto} "
                "Recomendo priorizar os sistemas em estado crítico.")

    if any(t in p for t in ["recomenda", "fazer", "ação", "acao", "contingência", "contingencia"]):
        return ("ARIA: Em situações críticas, a prioridade é: 1) suporte à vida, "
                "2) energia, 3) comunicação. Execute a análise completa para uma "
                "recomendação específica por ciclo.")

    # Resposta genérica — conversa livre
    base = ("ARIA: Entendi sua pergunta. Estou operando em modo local "
            "(sem conexão com o modelo de IA), então minhas respostas são limitadas. "
            "Para respostas completas a qualquer pergunta, configure a chave de API "
            "no arquivo .env.")
    if not sem_dados:
        base += f" Sobre a missão: {contexto}"
    return base

def preparar_contexto_ciclo(
    numero_ciclo: int,
    nome_ciclo: str,
    resultado_analise: dict[str, Any],
) -> dict[str, Any]:
    """Prepara o contexto estruturado do ciclo para injeção no prompt.

    Formata os dados brutos da análise em um dicionário legível
    pelo modelo, com campos descritivos e unidades explícitas.

    Args:
        numero_ciclo:     Número sequencial do ciclo (1-based).
        nome_ciclo:       Nome descritivo do ciclo.
        resultado_analise: Dicionário retornado por analisar_ciclo().

    Returns:
        Dicionário pronto para serialização no prompt.
    """
    valores = resultado_analise["valores"]
    classif = resultado_analise["classificacoes"]

    areas = [
        "Temperatura interna",
        "Comunicacao com a base",
        "Sistema de energia (bateria)",
        "Suporte de oxigenio",
        "Estabilidade operacional",
    ]
    unidades = ["graus Celsius", "%", "%", "%", "%"]

    metricas = {}
    for i, area in enumerate(areas):
        status, pontos, msg = classif[i]
        metricas[area] = {
            "valor":          valores[i],
            "unidade":        unidades[i],
            "classificacao":  status,
            "pontuacao":      pontos,
            "descricao":      msg,
        }

    return {
        "missao":           "O.R.B.I.T.A.",
        "equipe":           "Aldebaran",
        "ciclo_numero":     numero_ciclo,
        "ciclo_nome":       nome_ciclo,
        "status_geral":     resultado_analise["status"],
        "pontuacao_total":  resultado_analise["pontuacao"],
        "pontuacao_maxima": 10,
        "metricas":         metricas,
        "recomendacao_sistema": resultado_analise["recomendacao"],
    }


def consultar_agente(
    numero_ciclo: int,
    nome_ciclo: str,
    resultado_analise: dict[str, Any],
    exibir_no_terminal: bool = True,
) -> str:
    """Pipeline completo: prepara contexto → chama LLM → retorna resposta.

    Ponto de entrada principal para integração com mission_control.py.
    Chamado automaticamente quando um ciclo é classificado como CRÍTICO.

    Fluxo:
        1. Prepara contexto estruturado do ciclo
        2. Constrói prompt com injeção de contexto
        3. Tenta chamada à API (ou usa mock se configurado)
        4. Exibe resposta no terminal com formatação
        5. Retorna texto para uso na HUD

    Args:
        numero_ciclo:       Número do ciclo crítico.
        nome_ciclo:         Nome descritivo do ciclo.
        resultado_analise:  Dicionário retornado por analisar_ciclo().
        exibir_no_terminal: Se True, imprime a resposta formatada.

    Returns:
        String com a resposta do agente (API ou mock).
    """
    contexto = preparar_contexto_ciclo(numero_ciclo, nome_ciclo, resultado_analise)

    if exibir_no_terminal:
        print(f"\n{MAGENTA}{BOLD}{'═' * 62}{RESET}")
        print(f"{MAGENTA}{BOLD}  ◈ ARIA — AGENTE COGNITIVO TÁTICO ATIVADO{RESET}")
        print(f"{MAGENTA}{BOLD}  Ciclo {numero_ciclo} — {nome_ciclo}{RESET}")
        print(f"{MAGENTA}{BOLD}{'═' * 62}{RESET}")

    # Decidir: API real ou mock
    usar_api = (
        not MODO_MOCK
        and HF_API_KEY != "COLE_SUA_KEY_AQUI"
        and len(HF_API_KEY) > 10
    )

    if usar_api:
        if exibir_no_terminal:
            print(f"  {DIM}Conectando ao modelo {MODEL_ID}...{RESET}")

        prompt_usuario  = construir_user_prompt(contexto)
        texto, sucesso  = chamar_api_hf(prompt_usuario)

        if not sucesso:
            if exibir_no_terminal:
                print(f"  {YELLOW}[AVISO] API indisponível: {texto}{RESET}")
                print(f"  {DIM}Ativando fallback mock...{RESET}")
            texto = gerar_resposta_mock(contexto)
        else:
            if exibir_no_terminal:
                print(f"  {GREEN}[OK] Resposta recebida do modelo.{RESET}")
    else:
        if exibir_no_terminal:
            modo_label = "MOCK" if MODO_MOCK else "DEMO (sem chave API)"
            print(f"  {DIM}Modo {modo_label} ativo — usando resposta local.{RESET}")
        texto = gerar_resposta_mock(contexto)

    # Exibir resposta formatada
    if exibir_no_terminal:
        print(f"\n{MAGENTA}{'─' * 62}{RESET}")
        linhas = texto.strip().split("\n")
        for linha in linhas:
            if linha.startswith("**") and linha.endswith("**"):
                print(f"  {BOLD}{MAGENTA}{linha.replace('**', '')}{RESET}")
            elif linha.strip():
                print(f"  {WHITE}{linha}{RESET}")
            else:
                print()
        print(f"{MAGENTA}{'─' * 62}{RESET}\n")

    return texto


def processar_ciclos_criticos(
    resultados: list[dict[str, Any]],
    nomes_ciclos: list[str],
) -> list[dict[str, Any]]:
    """Filtra ciclos críticos e consulta o agente para cada um.

    Percorre a lista de resultados da análise completa da missão,
    identifica os ciclos classificados como MISSÃO CRÍTICA e
    aciona o pipeline de consulta ao agente LLM.

    Args:
        resultados:   Lista de dicionários retornados por analisar_ciclo().
        nomes_ciclos: Lista de nomes descritivos de cada ciclo.

    Returns:
        Lista de dicionários com ciclo, análise e resposta do agente.
    """
    respostas_agente: list[dict[str, Any]] = []

    criticos = [
        (i, r) for i, r in enumerate(resultados)
        if "CRITICA" in r["status"]
    ]

    if not criticos:
        print(f"\n{GREEN}  Nenhum ciclo crítico detectado. ARIA em standby.{RESET}\n")
        return respostas_agente

    print(f"\n{MAGENTA}{BOLD}  {len(criticos)} ciclo(s) crítico(s) detectado(s). Ativando ARIA...{RESET}")
    time.sleep(0.5)

    for idx, resultado in criticos:
        nome = nomes_ciclos[idx] if idx < len(nomes_ciclos) else f"Ciclo {idx + 1}"
        resposta_texto = consultar_agente(idx + 1, nome, resultado, exibir_no_terminal=True)

        respostas_agente.append({
            "ciclo":    idx + 1,
            "nome":     nome,
            "analise":  resultado,
            "resposta": resposta_texto,
        })

        # Pausa entre chamadas para respeitar rate limit da API
        if len(criticos) > 1:
            time.sleep(1.0)

    return respostas_agente


# ════════════════════════════════════════════════════════════
#  EXECUÇÃO STANDALONE — TESTE ISOLADO
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print(f"\n{CYAN}{BOLD}{'═' * 62}{RESET}")
    print(f"{CYAN}{BOLD}  O.R.B.I.T.A. — AI Copilot · Teste Standalone{RESET}")
    print(f"{CYAN}{BOLD}{'═' * 62}{RESET}\n")

    # Simular resultado de ciclo crítico (ciclo 5 da missão)
    resultado_critico_simulado: dict[str, Any] = {
        "valores":       [40, 25, 17, 76, 32],
        "classificacoes": [
            ("CRITICO", 2, "Risco de superaquecimento"),
            ("CRITICO", 2, "Comunicacao com a base em nivel critico"),
            ("CRITICO", 2, "Bateria em nivel critico"),
            ("CRITICO", 2, "Oxigenio em nivel critico"),
            ("CRITICO", 2, "Estabilidade operacional critica"),
        ],
        "pontuacao":     10,
        "status":        "MISSAO CRITICA",
        "recomendacao":  "ALERTA MAXIMO: Ativar modo de seguranca e priorizar suporte a vida, energia e comunicacao.",
    }

    print("  Configuração atual:")
    print(f"  Modelo : {MODEL_ID}")
    print(f"  Modo   : {'MOCK (sem API)' if MODO_MOCK else 'API REAL'}")
    print(f"  Key    : {'Não configurada' if HF_API_KEY == 'COLE_SUA_KEY_AQUI' else 'Configurada'}")
    print()

    consultar_agente(5, "Risco operacional critico", resultado_critico_simulado)

    print(f"\n{DIM}  Para usar a API real:{RESET}")
    print("  1. Obtenha sua chave em: https://huggingface.co/settings/tokens")
    print("  2. Defina HF_API_KEY = 'sua_chave_aqui'")
    print("  3. Defina MODO_MOCK = False")
    print("  4. Escolha o MODEL_ID de sua preferência\n")
