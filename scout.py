import sys
import googlemaps
import requests
import warnings
import os
from bs4 import BeautifulSoup

try:
    import streamlit as st
    API_KEY = st.secrets["GOOGLE_API_KEY"]
except Exception:
    API_KEY = os.environ.get("GOOGLE_API_KEY", "COLE_SUA_CHAVE_AQUI_SO_NA_SUA_MAQUINA")

try:
    from db_connect import db
except ImportError:
    from google.cloud import firestore
    db = firestore.Client.from_service_account_json("credenciais-google.json")

warnings.filterwarnings('ignore', message='Unverified HTTPS request')
gmaps = googlemaps.Client(key=API_KEY)

def verificar_e_ler_site(url):
    if not url or url == 'Não possui':
        return "Não possui site", "Sem informações do site."
    
    try:
        # Disfarça o robô como se fosse um navegador comum para os sites não bloquearem
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resposta = requests.get(url, headers=headers, timeout=5, verify=False)
        
        status_seguranca = "Seguro (HTTPS Ativo)" if url.startswith("https") else "Inseguro (Sem HTTPS - Risco de Segurança)"
        
        # Faz o Web Scraping Profundo
        soup = BeautifulSoup(resposta.text, 'html.parser')
        
        # Remove os códigos por trás da tela (Javascript e CSS) para pegar só o texto legível
        for script in soup(["script", "style"]):
            script.extract()
            
        texto_puro = soup.get_text(separator=' ', strip=True)
        # Pega os primeiros 1000 caracteres (o suficiente para a IA entender o negócio do cliente)
        resumo_site = texto_puro[:1000] if len(texto_puro) > 10 else "Site sem textos descritivos."
        
        return status_seguranca, resumo_site

    except requests.exceptions.SSLError:
        return "Inseguro (Erro de Certificado SSL quebrado)", "Não foi possível extrair dados (Erro SSL)."
    except requests.exceptions.RequestException:
        return "Site fora do ar ou link quebrado", "Não foi possível extrair dados."

def filtrar_e_salvar_negocio(place_details, nicho_pesquisado):
    nome = place_details.get('name')
    rating = place_details.get('rating', 0)
    user_ratings_total = place_details.get('user_ratings_total', 0)
    place_id = place_details.get('place_id')
    website = place_details.get('website', 'Não possui')
    
    doc_ref = db.collection("leads").document(place_id)
    if doc_ref.get().exists:
        print(f"⏭️ {nome} já existe. Pula para o próximo.")
        return

    # Nova função em ação
    status_do_site, conteudo_site = verificar_e_ler_site(website)

    dados_lead = {
        "id_google": place_id,
        "nome": nome,
        "nicho": nicho_pesquisado,
        "telefone": place_details.get('formatted_phone_number', 'Não encontrado'),
        "endereco": place_details.get('formatted_address', ''),
        "nota_atual": rating,
        "total_avaliacoes": user_ratings_total,
        "website": website,
        "status_site": status_do_site,
        "conteudo_extraido_site": conteudo_site, # Salvando a leitura profunda!
        "status_agencia": "scouted"
    }
    doc_ref.set(dados_lead)
    print(f"✅ [Firestore] Lead salvo: {nome} | T.I: {status_do_site}")

def varrer_regiao(termo_busca, localizacao):
    print(f"🔎 Buscando '{termo_busca}' em '{localizacao}'...")
    resultado_busca = gmaps.places(query=f"{termo_busca}, {localizacao}")
    
    if 'results' in resultado_busca:
        for lugar in resultado_busca['results']:
            detalhes = gmaps.place(place_id=lugar['place_id'], fields=[
                'name', 'rating', 'user_ratings_total', 'formatted_phone_number', 
                'formatted_address', 'website', 'place_id'
            ])
            if 'result' in detalhes:
                filtrar_e_salvar_negocio(detalhes['result'], termo_busca)

if __name__ == "__main__":
    termo = sys.argv[1] if len(sys.argv) > 1 else "Clinica"
    regiao = sys.argv[2] if len(sys.argv) > 2 else "São Paulo"
    varrer_regiao(termo, regiao)
