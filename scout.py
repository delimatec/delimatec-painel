import sys
import googlemaps
import requests
import warnings
import os

try:
    import streamlit as st
    API_KEY = st.secrets["GOOGLE_API_KEY"]
except Exception:
    # Se rodar local na sua máquina, ele tenta achar na variável de ambiente
    API_KEY = os.environ.get("GOOGLE_API_KEY", "COLE_SUA_CHAVE_AQUI_SO_NA_SUA_MAQUINA")

try:
    from db_connect import db
except ImportError:
    from google.cloud import firestore
    db = firestore.Client.from_service_account_json("credenciais-google.json")

# Ignora os avisos de segurança quando o site do cliente não tem SSL
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

gmaps = googlemaps.Client(key=API_KEY)

def verificar_site(url):
    if not url or url == 'Não possui':
        return "Não possui site"
    try:
        # Tenta acessar o site ignorando erros de certificado para ver se ele pelo menos carrega
        resposta = requests.get(url, timeout=5, verify=False)
        if url.startswith("https"):
            return "Seguro (HTTPS Ativo)"
        else:
            return "Inseguro (Sem HTTPS - Risco de Segurança)"
    except requests.exceptions.SSLError:
        return "Inseguro (Erro de Certificado SSL quebrado)"
    except requests.exceptions.RequestException:
        return "Site fora do ar ou link quebrado"

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

    # Nova função de T.I: Raio-X do Site
    status_do_site = verificar_site(website)

    dados_lead = {
        "id_google": place_id,
        "nome": nome,
        "nicho": nicho_pesquisado,
        "telefone": place_details.get('formatted_phone_number', 'Não encontrado'),
        "endereco": place_details.get('formatted_address', ''),
        "nota_atual": rating,
        "total_avaliacoes": user_ratings_total,
        "website": website,
        "status_site": status_do_site, # NOVO: Salva a saúde da T.I do cliente
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
    termo = sys.argv[1] if len(sys.argv) > 1 else "Clinica Odontologica"
    regiao = sys.argv[2] if len(sys.argv) > 2 else "Pinheiros, São Paulo"
    varrer_regiao(termo, regiao)
