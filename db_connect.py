import os
import streamlit as st
from google.cloud import firestore
from google.oauth2 import service_account

def obter_banco():
    try:
        # 1. Tenta ler o cofre seguro da nuvem (Streamlit Secrets)
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            credenciais = service_account.Credentials.from_service_account_info(creds_dict)
            return firestore.Client(credentials=credenciais)
    except Exception:
        pass

    # 2. Se não estiver na nuvem, usa o arquivo local da sua máquina
    if os.path.exists("credenciais-google.json"):
        return firestore.Client.from_service_account_json("credenciais-google.json")
    
    raise Exception("Nenhuma credencial do Google encontrada!")

# Cria a conexão pronta para ser usada por todos os arquivos
db = obter_banco()