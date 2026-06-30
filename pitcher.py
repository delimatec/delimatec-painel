import os
import json
from anthropic import Anthropic

try:
    from db_connect import db
except ImportError:
    from google.cloud import firestore
    db = firestore.Client.from_service_account_json("credenciais-google.json")

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "SUA_CHAVE_CLAUDE_AQUI")
anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY) if "SUA_CHAVE" not in ANTHROPIC_API_KEY else None

def criar_mensagem_vendas(dados_lead):
    amostras = dados_lead.get('amostras_geradas', {})
    
    prompt = f"""
    Escreva uma mensagem de abordagem comercial para o WhatsApp do dono da empresa {dados_lead['nome']}.
    Use as seguintes informações coletadas pelo nosso sistema:
    - Diagnóstico do problema online e de T.I: {dados_lead['diagnostico_ia']}
    - Presente: Post ("{amostras.get('post_proposto', '')[:80]}...") e Respostas Otimizadas.

    Instruções estritas de tom e posicionamento (DeLimaTec):
    - Você representa a DeLimaTec, uma empresa completa de Soluções em T.I., Infraestrutura e Posicionamento Digital.
    - Comece amigável e direto: 'Olá, responsável pela {dados_lead['nome']}, tudo bem? Aqui é da equipe da DeLimaTec.'
    - Mostre autoridade: explique que a DeLimaTec ajuda empresas não só a ter computadores e redes seguras, mas também a dominar as buscas locais usando tecnologia.
    - Apresente o diagnóstico do Maps/Site de forma polida.
    - Entregue a isca: 'Para mostrar a qualidade do nosso trabalho, nossa IA gerou um material de presente para o perfil de vocês usar hoje.'
    - Termine com a CTA: 'Podemos falar 5 minutos amanhã?'
    - Mantenha curto e cirúrgico.

    REGRAS DE FORMATAÇÃO PARA O WHATSAPP (MUITO IMPORTANTE):
    1. NUNCA use duplo asterisco (**) para negrito. Use SEMPRE apenas um asterisco (*texto*).
    2. NÃO use linhas horizontais como (---).
    3. Use no máximo 2 emojis na mensagem inteira para manter o tom profissional.
    """

    message = anthropic_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        temperature=0.6,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text

def gerar_follow_up_com_claude(dados_lead):
    if not anthropic_client: return "Olá! Passando para saber se conseguiu avaliar o diagnóstico que enviei. Podemos conversar? Abs, equipe DeLimaTec."
    
    prompt = f"""
    Você é consultor da DeLimaTec. Crie uma mensagem curta de WhatsApp (Follow-up) para a empresa {dados_lead['nome']}.
    Há 48 horas enviamos esta mensagem inicial: "{dados_lead.get('pitch_vendas_whatsapp')}"
    
    Objetivo: Perguntar educadamente se o responsável conseguiu ver o diagnóstico de T.I./Maps e o presente, e se tem 5 minutos para conversarmos.
    Regras: 
    - Seja muito curto, natural, amigável. Não seja insistente. Assine como equipe DeLimaTec.
    - Para negrito, use apenas um asterisco (*texto*). NUNCA use (**).
    - Máximo de 1 emoji.
    """
    try:
        message = anthropic_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=250,
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text
    except Exception as e:
        return "Olá! Passando para saber se conseguiu dar uma olhada na auditoria de tecnologia que mandei outro dia. Podemos falar rapidinho? Abs, equipe DeLimaTec."

def rodar_pitcher():
    docs = db.collection("leads").where("status_agencia", "==", "content_built").stream()
    for doc in docs:
        dados_lead = doc.to_dict()
        print(f"📣 Criando mensagem comercial DeLimaTec: {dados_lead['nome']}...")
        pitch = criar_mensagem_vendas(dados_lead)
        if pitch:
            doc.reference.update({
                "pitch_vendas_whatsapp": pitch,
                "status_agencia": "ready_to_send"
            })

if __name__ == "__main__":
    rodar_pitcher()
