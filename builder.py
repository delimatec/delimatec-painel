import os
import json
from anthropic import Anthropic
from google.cloud import firestore

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "SUA_CHAVE_CLAUDE_AQUI")
anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY) if "SUA_CHAVE" not in ANTHROPIC_API_KEY else None
from db_connect import db

def gerar_conteudo_com_claude(dados_lead):
    if not anthropic_client:
        return {"resposta_1": "Obrigado", "resposta_2": "Dispomos", "post_proposto": "Venha conhecer!"}
    
    nicho_lead = dados_lead.get('nicho', 'Comércio Local')

    prompt = f"""
Você atua na DeLimaTec, uma parceira de Soluções em T.I. e Inteligência Digital para negócios locais.
Sua missão é criar conteúdos de alto nível para a empresa {dados_lead['nome']}, que atua no nicho de: {nicho_lead}.

INSTRUÇÕES DE NICHO:
- Adapte o tom de voz e os argumentos para o público de {nicho_lead}.
- Fale das dores e desejos reais de clientes de {nicho_lead}.

## Objetivos
- Atrair clientes gerando percepção de extrema organização e qualidade.
- Incentivar contato.
- Demonstrar profissionalismo que reflita uma empresa moderna (amparada por tecnologia).

## Regras obrigatórias
1. Não invente informações irreais.
2. Não ofereça produtos gratuitos ou descontos, salvo se explícito.
3. Não use jargões de forma excessiva.
4. Linguagem comercial premium e persuasiva.
5. Inclua CTAs naturais.
6. Máximo 2 emojis por texto.

## Respostas para avaliações
- Gratidão e profissionalismo, entre 40 e 90 palavras.

## Post para Google Meu Negócio / Instagram
- Chame atenção na primeira frase.
- Foque na resolução do problema do cliente.
- Entre 120 e 250 palavras otimizadas para SEO.

Retorne EXCLUSIVAMENTE um JSON válido:
{{
    "resposta_1": "...",
    "resposta_2": "...",
    "post_proposto": "..."
}}
"""
    try:
        message = anthropic_client.messages.create(
            model="claude-sonnet-4-6", max_tokens=800, temperature=0.5,
            messages=[{"role": "user", "content": prompt}]
        )
        texto = message.content[0].text.strip()
        
        # O bloco que havia sido cortado está inteiro aqui:
        if "```json" in texto: 
            texto = texto.split("```json")[1].split("```")[0].strip()
        elif "```" in texto: 
            texto = texto.split("```")[1].split("```")[0].strip()
            
        return json.loads(texto)
        
    except json.JSONDecodeError:
        return {
            "resposta_1": "Agradecemos muito pela sua avaliação! Nosso objetivo é sempre oferecer o melhor atendimento. Conte conosco!",
            "resposta_2": "Muito obrigado pelo feedback! É ótimo saber da sua experiência. Esperamos vê-lo novamente em breve.",
            "post_proposto": f"Você já conhece a qualidade da {dados_lead['nome']}? Venha nos fazer uma visita e descubra por que nossos clientes nos avaliam tão bem! Agende agora pelo WhatsApp."
        }
    except Exception as e:
        print(f"❌ Erro de conexão com a API para {dados_lead['nome']}: {e}")
        return None

def rodar_builder():
    docs = db.collection("leads").where("status_agencia", "==", "diagnosed").stream()
    for doc in docs:
        dados_lead = doc.to_dict()
        print(f"🎨 Criando criativos (DeLimaTec) para: {dados_lead['nome']}...")
        conteudo = gerar_conteudo_com_claude(dados_lead)
        if conteudo:
            doc.reference.update({
                "amostras_geradas": conteudo,
                "status_agencia": "content_built"
            })

if __name__ == "__main__":
    rodar_builder()