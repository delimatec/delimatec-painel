import warnings
warnings.filterwarnings("ignore")

import streamlit as st
from google.cloud import firestore
import os
import base64
import requests 
import urllib.parse
from PIL import Image
import io
from fpdf import FPDF

# Importa as funções lógicas dos agentes
from scout import varrer_regiao
from diagnoser import rodar_diagnostico
from builder import rodar_builder
from pitcher import rodar_pitcher

def otimizar_imagem_base64(b64_string):
    try:
        img_bytes = base64.b64decode(b64_string)
        imagem = Image.open(io.BytesIO(img_bytes))
        if imagem.mode != 'RGB': imagem = imagem.convert('RGB')
        imagem.thumbnail((800, 800))
        buffer = io.BytesIO()
        imagem.save(buffer, format="JPEG", quality=75)
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    except Exception:
        return b64_string

def limpar_texto_pdf(texto):
    if not isinstance(texto, str):
        return ""
    substituicoes = {
        "—": "-", "–": "-", "“": '"', "”": '"', "‘": "'", "’": "'", "…": "...",
        "⭐": "*", "✨": "*", "🚀": ">", "🎁": ">"
    }
    for velho, novo in substituicoes.items():
        texto = texto.replace(velho, novo)
    return texto.encode('latin-1', 'replace').decode('latin-1')

def gerar_pdf_auditoria(lead, amostras):
    pdf = FPDF()
    pdf.add_page()
    
    # Cabeçalho DeLimaTec
    pdf.set_font("Arial", 'B', 16)
    nome_limpo = limpar_texto_pdf(lead.get('nome', ''))
    pdf.cell(0, 10, "Auditoria Estratégica de Tecnologia e Posicionamento", ln=True, align='C')
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(0, 8, "Desenvolvido por DeLimaTec - Suporte T.I. & Soluções Digitais", ln=True, align='C')
    pdf.set_font("Arial", 'I', 12)
    pdf.cell(0, 10, f"Empresa Avaliada: {nome_limpo}", ln=True, align='C')
    pdf.ln(10)
    
    # Diagnóstico
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "1. Diagnóstico de Infraestrutura Digital (Google Maps):", ln=True)
    pdf.set_font("Arial", '', 11)
    diag_limpo = limpar_texto_pdf(lead.get('diagnostico_ia', 'Análise não disponível.'))
    pdf.multi_cell(0, 8, diag_limpo)
    pdf.ln(5)
    
    # Presentes/Amostras
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "2. Material de Cortesia Gerado por Nossa IA:", ln=True)
    
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 8, "Sugestão de Postagem de Alta Conversão:", ln=True)
    pdf.set_font("Arial", '', 11)
    post_limpo = limpar_texto_pdf(amostras.get('post_proposto', ''))
    pdf.multi_cell(0, 8, post_limpo)
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 8, "Sugestão de Resposta Humanizada para Clientes:", ln=True)
    pdf.set_font("Arial", '', 11)
    resp_limpa = limpar_texto_pdf(amostras.get('resposta_1', ''))
    pdf.multi_cell(0, 8, resp_limpa)
    
    return bytes(pdf.output())

# Configuração Web
st.set_page_config(page_title="DeLimaTec - Painel", page_icon="💻", layout="wide")

try:
    from db_connect import db
except Exception as e:
    st.error(f"Erro ao conectar: {e}")
    st.stop()

st.title("💻 DeLimaTec - Máquina de Vendas Integrada")
st.write("Sistema de inteligência para prospecção de Suporte T.I. e Gestão de Maps.")

aba_buscar, aba_vendas, aba_metricas = st.tabs(["🔎 Mineração", "💰 Fila de Vendas", "📊 Métricas de Desempenho"])

# =========================================================================
# ABA 1: MINERAÇÃO
# =========================================================================
with aba_buscar:
    col1, col2 = st.columns(2)
    with col1: nicho = st.text_input("Qual o tipo de comércio?", placeholder="Ex: Oficina Mecânica")
    with col2: localizacao = st.text_input("Bairro e Cidade?", placeholder="Ex: Pinheiros, São Paulo")
        
    if st.button("🚀 Iniciar Automação", type="primary"):
        if nicho and localizacao:
            with st.spinner("🤖 A IA da DeLimaTec está trabalhando..."):
                try:
                    varrer_regiao(nicho, localizacao)
                    rodar_diagnostico()
                    rodar_builder()
                    rodar_pitcher()
                    st.success("✨ Concluído! Vá para a aba 'Fila de Vendas'.")
                except Exception as e:
                    st.error(f"Erro no pipeline: {e}")

# =========================================================================
# ABA 2: FILA DE VENDAS
# =========================================================================
with aba_vendas:
    try:
        leads_prontos = list(db.collection("leads").where("status_agencia", "==", "ready_to_send").stream())
        if not leads_prontos:
            st.info("📭 Nenhuma mensagem pendente.")
        else:
            total_pendentes = len(leads_prontos)
            st.write(f"Há **{total_pendentes}** oportunidades prontas na fila.")
            st.info("💡 **Fila de Atendimento:** Mostrando apenas os 5 primeiros para manter o painel rápido. Ao 'Marcar Enviado', o próximo da fila sobe automaticamente!")
            
            # Pega apenas os 5 primeiros da lista para otimizar espaço e velocidade
            leads_para_exibir = leads_prontos[:5]
            
            for doc in leads_para_exibir:
                lead = doc.to_dict()
                with st.container(border=True):
                    col_info, col_pitch = st.columns([1, 2])
                    
                    with col_info:
                        st.subheader(lead.get('nome', 'Sem Nome'))
                        st.write(f"⭐️ **Nota:** {lead.get('nota_atual', '')} | 💬 **Reviews:** {lead.get('total_avaliacoes', '')}")
                        
                        nome_formatado = urllib.parse.quote(lead.get('nome', ''))
                        endereco_formatado = urllib.parse.quote(lead.get('endereco', ''))
                        link_ig = f"https://www.google.com/search?q=site:instagram.com+{nome_formatado}+{endereco_formatado}"
                        st.link_button("🟣 Espiar Instagram", link_ig)
                        
                        telefone = lead.get('telefone', '')
                        st.write(f"📞 **Tel:** {telefone}")
                        
                        tel_limpo = "".join([c for c in telefone if c.isdigit()])
                        if tel_limpo:
                            if not tel_limpo.startswith("55") and len(tel_limpo) >= 10: tel_limpo = "55" + tel_limpo
                            st.link_button("🟢 Abrir no WhatsApp", f"https://wa.me/{tel_limpo}")
                        
                        if st.button("✅ Marcar Enviado", key=f"status_{doc.id}"):
                            doc.reference.update({"status_agencia": "sent"})
                            st.rerun()
                            
                    with col_pitch:
                        amostras = lead.get('amostras_geradas', {})
                        if amostras:
                            pdf_bytes = gerar_pdf_auditoria(lead, amostras)
                            st.download_button(
                                label="📄 Baixar Auditoria em PDF",
                                data=pdf_bytes,
                                file_name=f"Auditoria_{lead.get('nome', 'Lead')}.pdf",
                                mime="application/pdf",
                                type="primary",
                                key=f"pdf_{doc.id}"
                            )
                            
                        st.markdown("### 💬 Mensagem de Abordagem")
                        st.text_area("Edite ou copie o texto abaixo:", lead.get('pitch_vendas_whatsapp', ''), height=200, label_visibility="collapsed", key=f"pitch_{doc.id}")
                        
                        if amostras:
                            with st.expander("📝 Ver Post e Respostas"):
                                st.text_area("Post Proposto (DeLimaTec):", amostras.get('post_proposto', ''), height=150, key=f"post_{doc.id}")
                                st.text_area("Resposta Humanizada 1:", amostras.get('resposta_1', ''), height=100, key=f"resp1_{doc.id}")
                                st.text_area("Resposta Humanizada 2:", amostras.get('resposta_2', ''), height=100, key=f"resp2_{doc.id}")
                        
                        st.markdown("### 🖼️ Criativo Visual para o Post")
                        imagem_b64 = lead.get('imagem_generated_base64') if lead.get('imagem_generated_base64') else lead.get('imagem_gerada_base64')
                        
                        if imagem_b64:
                            imagem_bytes = base64.b64decode(imagem_b64)
                            st.image(imagem_bytes, caption="Criativo gerado e otimizado com sucesso!", use_container_width=True)
                            st.download_button(label="💾 Baixar Imagem", data=imagem_bytes, file_name=f"post_{doc.id}.jpg", mime="image/jpeg", key=f"dl_{doc.id}")
                        else:
                            st.info("Clique abaixo para gerar a imagem na hora.")
                            if st.button("✨ Gerar Imagem Grátis (Gemini)", key=f"img_{doc.id}"):
                                with st.spinner("Desenhando imagem (Pode levar 10s)..."):
                                    try:
                                        chave_gemini = os.environ.get("GEMINI_API_KEY")
                                        texto_post = amostras.get('post_proposto', lead.get('nome'))
                                        prompt_img = f"Fotografia profissional, hiper-realista. SEM nenhum texto. Tema: {lead.get('nome')}. Contexto: {texto_post}"
                                        
                                        sucesso_geracao = False
                                        img_base64_str = ""
                                        
                                        if chave_gemini:
                                            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image:generateContent?key={chave_gemini}"
                                            payload = {"contents": [{"parts": [{"text": prompt_img}]}], "generationConfig": {"responseModalities": ["IMAGE"]}}
                                            resposta_api = requests.post(url, json=payload)
                                            if resposta_api.status_code == 200:
                                                dados = resposta_api.json()
                                                try:
                                                    for parte in dados['candidates'][0]['content']['parts']:
                                                        if 'inlineData' in parte:
                                                            img_base64_str = parte['inlineData']['data']
                                                            sucesso_geracao = True
                                                            break
                                                except (KeyError, IndexError): pass
                                        
                                        if not sucesso_geracao:
                                            prompt_seguro = urllib.parse.quote(prompt_img)
                                            resp_backup = requests.get(f"https://image.pollinations.ai/prompt/{prompt_seguro}?nologo=true")
                                            if resp_backup.status_code == 200:
                                                img_base64_str = base64.b64encode(resp_backup.content).decode('utf-8')
                                                sucesso_geracao = True
                                            else: st.error("Servidores congestionados. Tente novamente.")
                                                
                                        if sucesso_geracao:
                                            img_base64_otimizada = otimizar_imagem_base64(img_base64_str)
                                            doc.reference.update({"imagem_gerada_base64": img_base64_otimizada})
                                            st.rerun() 
                                    except Exception as e:
                                        st.error(f"Erro ao gerar imagem: {e}")
    except Exception as e:
        st.error(f"Erro ao carregar os leads: {e}")

# =========================================================================
# ABA 3: DASHBOARD E MÉTRICAS
# =========================================================================
with aba_metricas:
    st.header("📈 Desempenho DeLimaTec")
    try:
        todos_leads = list(db.collection("leads").stream())
        total = len(todos_leads)
        enviados = len([l for l in todos_leads if l.to_dict().get('status_agencia') == 'sent'])
        pendentes = len([l for l in todos_leads if l.to_dict().get('status_agencia') == 'ready_to_send'])
        
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Leads Totais Minerados", total)
        col_m2.metric("Prospecções Enviadas", enviados)
        col_m3.metric("Aguardando Envio", pendentes)
        if total > 0: st.progress(enviados / total, text=f"Taxa de Abordagem: {int((enviados/total)*100)}%")
    except Exception as e:
        st.error(f"Erro ao carregar métricas: {e}")