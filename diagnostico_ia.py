"""
============================================================
  O.R.B.I.T.A. — Diagnóstico da IA (ARIA)
============================================================
  Rode este script para descobrir por que a ARIA está
  respondendo em modo local (mock) em vez de usar a IA real.

  Uso:  python diagnostico_ia.py
============================================================
"""

import os


def main() -> None:
    print("=" * 56)
    print("  DIAGNÓSTICO DA ARIA — O.R.B.I.T.A.")
    print("=" * 56)

    # 1. Verificar se o .env existe
    aqui = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(aqui, ".env")
    print(f"\n[1] Procurando .env em: {env_path}")
    if os.path.exists(env_path):
        print("    OK — arquivo .env encontrado.")
        with open(env_path, encoding="utf-8") as f:
            linhas = [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]
        print(f"    Variaveis: {[ln.split('=')[0] for ln in linhas]}")
    else:
        print("    ERRO — arquivo .env NAO encontrado nesta pasta!")
        print("    Solucao: crie um arquivo chamado .env aqui com:")
        print("      OPENROUTER_API_KEY=sk-or-v1-suachave")
        print("      OPENROUTER_MODEL=deepseek/deepseek-chat-v3-0324:free")
        return

    # 2. Verificar se python-dotenv carrega
    print("\n[2] Carregando python-dotenv...")
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
        print("    OK — dotenv carregado.")
    except ImportError:
        print("    ERRO — python-dotenv nao instalado.")
        print("    Solucao: pip install python-dotenv")
        return

    # 3. Verificar a chave
    print("\n[3] Verificando a chave...")
    import ai_copilot
    chave = ai_copilot.HF_API_KEY
    modelo = ai_copilot.MODEL_ID
    placeholders = ("COLE_SUA_CHAVE_OPENROUTER_AQUI", "COLE_SUA_KEY_AQUI",
                    "COLE_SUA_CHAVE_AQUI")
    if not chave or chave in placeholders:
        print("    ERRO — chave nao configurada ou ainda e o placeholder.")
        print("    Edite o .env e coloque sua chave real do OpenRouter.")
        print("    Obtenha em: https://openrouter.ai/keys")
        return
    print(f"    OK — chave detectada: {chave[:10]}...{chave[-4:]}")
    print(f"    Modelo: {modelo}")
    print(f"    Endpoint: {ai_copilot.HF_API_URL}")

    # 4. Testar a chamada real à API
    print("\n[4] Testando chamada real a API (pode levar alguns segundos)...")
    print(f"    MODO_MOCK do sistema: {ai_copilot.MODO_MOCK}")
    if ai_copilot.MODO_MOCK:
        print("    ATENCAO — o sistema esta em MODO_MOCK mesmo com chave.")
        print("    Verifique se a chave tem mais de 10 caracteres.")
        return

    texto, sucesso = ai_copilot.chamar_api_hf(
        "Responda apenas com a frase: Conexao bem-sucedida.",
        system_prompt="Voce e um assistente de teste.",
    )
    if sucesso:
        print("    OK — A IA RESPONDEU! A ARIA esta usando IA real.")
        print(f"    Resposta do modelo: {texto[:120]}")
        print("    (Se o modelo principal falhar, o sistema usa um de reserva")
        print("     automaticamente — lista em MODELOS_FALLBACK no ai_copilot.py)")
    else:
        print("    FALHA na chamada a API:")
        print(f"    Motivo: {texto}")
        print("\n    Possiveis causas:")
        print("      - Sem conexao com a internet")
        print("      - Chave invalida (gere outra em openrouter.ai/keys)")
        print("      - Todos os modelos de reserva indisponiveis no momento")
        print("      - Limite diario do free tier atingido (tente mais tarde)")

    print("\n" + "=" * 56)


if __name__ == "__main__":
    main()
