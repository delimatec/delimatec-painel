import os
import json
import googlemaps
from anthropic import Anthropic

try:
    import streamlit as st
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except Exception:
    GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "COLE_SUA_CHAVE_AQUI_SO_NA_SUA_MAQUINA")

try:
    from db_connect import db
except ImportError:
    from google.cloud import firestore
    db = firestore.Client.from_service_account_json("credenciais-google.json")

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "SUA_CHAVE_CLAUDE_AQUI")

gmaps = googlemaps.Client(key=GOOGLE_API_KEY)
anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY) if "SUA_CHAVE" not in ANTHROPIC_API_KEY else None

def obter_avaliacoes_ruins(place_id):
    if not place_id:
        return []
        
    try:
        detalhes = gmaps.place(place_id=place_id, fields=['reviews'], language='pt-BR')
        reviews = detalhes.get('result', {}).get('reviews', [])
        avaliacoes_criticas = []
        for r in reviews:
            if r.get('rating', 5) <= 3:
                avaliacoes_criticas.append({
                    "autor": r.get('author_name'), "nota": r.get('rating'),
                    "texto": r.get('text'), "tempo": r.get('relative_time_description')
                })
        return avaliacoes_criticas[:3]
    except:
        return []

def analisar_com_claude(dados_empresa, avaliacoes):
    if not anthropic_client: return "Perfil precisa de posicionamento local e suporte digital."
    
    contexto_reviews = "\n".join([f"- Nota {r['nota']}: {r['texto']}" for r in avaliacoes]) if avaliacoes else "Nenhuma avaliação extraída."
    necessidade = dados_empresa.get('necessidade_cliente', '')
    
    # Puxa o texto lido pelo robô scout
    conteudo_site = dados_empresa.get('conteudo_extraido_site', 'Não avaliado ou inexistente.')
    
    prompt = f"""
    Você é o consultor chefe da DeLimaTec (Especialistas em Suporte de TI e SEO Local). 
    Analise este comércio e crie um diagnóstico direto (gargalo de infraestrutura digital e marketing) em até 100 palavras. 
    Mostre que é um erro técnico solucionável e cite algum serviço que eles prestam (se encontrado no texto do site) para gerar conexão.
    
    Dados do cliente:
    - Empresa: {dados_empresa.get('nome')}
    - Nota no Maps: {dados_empresa.get('nota_atual')}
    - Status de Segurança do Site (T.I.): {dados_empresa.get('status_site', 'Desconhecido')}
    - Texto extraído do site da empresa: '{conteudo_site}'
    - Avaliações ruins do Maps: {contexto_reviews}
    - Necessidade específica (se houver): '{necessidade}'
    """

    try:
        message = anthropic_client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=450, temperature=0.3,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text
    except Exception as e:
        return f"Erro ao gerar diagnóstico: {e}"

def rodar_diagnostico():
    docs = db.collection("leads").where("status_agencia", "==", "scouted").stream()
    for doc in docs:
        dados_lead = doc.to_dict()
        print(f"🔍 Diagnosticando Infra e Maps (DeLimaTec): {dados_lead.get('nome', 'Empresa')}...")
        
        id_google = dados_lead.get('id_google')
        piores = obter_avaliacoes_ruins(id_google)
        
        diag = analisar_com_claude(dados_lead, piores)
        
        doc.reference.update({
            "piores_avaliacoes": piores,
            "diagnostico_ia": diag,
            "status_agencia": "diagnosed"
        })

if __name__ == "__main__":
    rodar_diagnostico()
