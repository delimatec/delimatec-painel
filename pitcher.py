import os
import json
from anthropic import Anthropic
from google.cloud import firestore

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "SUA_CHAVE_CLAUDE_AQUI")
anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY) if "SUA_CHAVE" not in ANTHROPIC_API_KEY else None
from db_connect import db

def criar_mensagem_vendas(dados_lead):
    amostras = dados_lead.get('amostras_geradas', {})
    
    prompt = f"""
    Escreva uma mensagem de abordagem comercial para o WhatsApp do dono da empresa {dados_lead['nome']}.
    Use as seguintes informações coletadas pelo nosso sistema:
    - Diagnóstico do problema online: {dados_lead['diagnostico_ia']}
    - Presente: Post ("{amostras.get('post_proposto')[:80]}...") e Respostas Otimizadas.

    Instruções estritas de tom e posicionamento (DeLimaTec):
    - Você representa a DeLimaTec, uma empresa completa de Soluções em T.I., Infraestrutura e Posicionamento Digital.
    - Comece amigável e direto: 'Olá, responsável pela {dados_lead['nome']}, tudo bem? Aqui é da equipe da DeLimaTec.'
    - Mostre autoridade: explique que a DeLimaTec ajuda empresas não só a ter computadores e redes seguras, mas também a dominar as buscas locais usando tecnologia.
    - Apresente o diagnóstico do Maps de forma polida, mostrando que é um detalhe tecnológico fácil de resolver.
    - Entregue a isca: 'Para mostrar a qualidade do nosso trabalho, nossa IA gerou um material de presente para o perfil de vocês usar hoje.'
    - Termine com a CTA convidando para falar sobre melhorias na T.I. e nas buscas locais: 'Podemos falar 5 minutos amanhã?'
    - Mantenha curto e cirúrgico. Sem jargões difíceis.
    """

    message = anthropic_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        temperature=0.6,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text

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