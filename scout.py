import sys
import googlemaps
import requests
import warnings
import os
import re
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
        return "Não possui site", "Sem informações do site.", None
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resposta = requests.get(url, headers=headers, timeout=5, verify=False)
        
        status_seguranca = "Seguro (HTTPS Ativo)" if url.startswith("https") else "Inseguro (Sem HTTPS - Risco de Segurança)"
        
        soup = BeautifulSoup(resposta.text, 'html.parser')
        
        # 🟢 INTEGRAÇÃO INTELIGENTE: RASTREADOR DE WHATSAPP NO SITE
        whatsapp_encontrado = None
        for link in soup.find_all('a', href=True):
            href = link['href'].lower()
            if 'wa.me' in href or 'api.whatsapp.com' in href or 'whatsapp.com/send' in href:
                # Extrai apenas os dígitos do número do link
                numeros = re.sub(r'\D', '', href)
                if len(numeros) >= 10:
                    whatsapp_encontrado = numeros
                    break
                    
        # Remove códigos estruturais de design
        for script in soup(["script", "style"]):
            script.extract()
            
        texto_puro = soup.get_text(separator=' ', strip=True)
        resumo_site = texto_puro[:1000] if len(texto_puro) > 10 else "Site sem textos descritivos."
        
        return status_seguranca, resumo_site, whatsapp_encontrado

    except requests.exceptions.SSLError:
        return "Inseguro (Erro de Certificado SSL quebrado)", "Não foi possível extrair dados (Erro SSL).", None
    except requests.exceptions.RequestException:
        return "Site fora do ar ou link quebrado", "Não foi possível extrair dados.", None

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

    # Nova função em ação (agora retorna 3 valores)
    status_do_site, conteudo_site, wpp_encontrado = verificar_e_ler_site(website)

    # 🟢 Define o telefone final: Se achar WhatsApp no site, substitui o fixo do Google Maps!
    telefone_final = place_details.get('formatted_phone_number', 'Não encontrado')
    if wpp_encontrado:
        # Se veio com o 55 da API, remove para formatar bonito na tela do painel
        if wpp_encontrado.startswith("55") and len(wpp_encontrado) > 4:
            wpp_encontrado = wpp_encontrado[2:]
        
        if len(wpp_encontrado) == 11: # Celular com 9 dígitos + DDD
            telefone_final = f"({wpp_encontrado[:2]}) {wpp_encontrado[2:7]}-{wpp_encontrado[7:]}"
        elif len(wpp_encontrado) == 10: # Celular antigo ou fixo com DDD
            telefone_final = f"({wpp_encontrado[:2]}) {wpp_encontrado[2:6]}-{wpp_encontrado[6:]}"
        else:
            telefone_final = f"+55 {wpp_encontrado}"

    dados_lead = {
        "id_google": place_id,
        "nome": nome,
        "nicho": nicho_pesquisado,
        "telefone": telefone_final,
        "endereco": place_details.get('formatted_address', ''),
        "nota_atual": rating,
        "total_avaliacoes": user_ratings_total,
        "website": website,
        "status_site": status_do_site,
        "conteudo_extraido_site": conteudo_site,
        "status_agencia": "scouted"
    }
    doc_ref.set(dados_lead)
    print(f"✅ [Firestore] Lead salvo: {nome} | T.I: {status_do_site} | Tel: {telefone_final}")

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
