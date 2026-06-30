import warnings
warnings.filterwarnings("ignore")

import streamlit as st
import os
import base64
import requests 
import urllib.parse
from PIL import Image
import io
import sys
from fpdf import FPDF

# Importa as funções lógicas dos agentes
from scout import varrer_regiao
from diagnoser import rodar_diagnostico
from builder import rodar_builder
from pitcher import rodar_pitcher, gerar_follow_up_com_claude

try:
    from db_connect import db
except ImportError:
    from google.cloud import firestore
    db = firestore.Client.from_service_account_json("credenciais-google.json")

# Inicializa a memória da página atual no sistema
if "pagina_vendas" not in st.session_state:
    st.session_state.pagina_vendas = 0
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

# =========================================================================
# CONFIGURAÇÃO DA PÁGINA E LOGIN
# =========================================================================
st.set_page_config(page_title="DeLimaTec OS", page_icon="💻", layout="wide")

def verificar_login():
    usu_correto = st.secrets.get("LOGIN_USUARIO", "admin")
    senha_correta = st.secrets.get("LOGIN_SENHA", "admin")
    if st.session_state.usu_input == usu_correto and st.session_state.senha_input == senha_correta:
        st.session_state.autenticado = True
        st.session_state.senha_input = ""
    else:
        st.error("❌ Usuário ou senha incorretos.")

if not st.session_state.autenticado:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔒 Acesso Restrito")
        st.markdown("Por favor, identifique-se para acessar o **DeLimaTec OS**.")
        with st.container(border=True):
            st.text_input("Usuário", key="usu_input")
            st.text_input("Senha", type="password", key="senha_input")
            st.button("Entrar no Sistema", on_click=verificar_login, type="primary", use_container_width=True)
    st.stop()

# =========================================================================
# FUNÇÕES DE APOIO E PDF
# =========================================================================
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
    if not isinstance(texto, str): return ""
    substituicoes = {"—": "-", "–": "-", "“": '"', "’": '"', "‘": "'", "’": "'", "…": "...", "⭐": "*", "✨": "*", "🚀": ">", "🎁": ">"}
    for velho, retro in substituicoes.items(): texto = texto.replace(velho, retro)
    return texto.encode('latin-1', 'replace').decode('latin-1')

def gerar_pdf_auditoria(lead, amostras):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    nome_limpo = limpar_texto_pdf(lead.get('nome', ''))
    pdf.cell(0, 10, "Auditoria Estratégica de Tecnologia e Posicionamento", ln=True, align='C')
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(0, 8, "Desenvolvido por DeLimaTec - Suporte T.I. & Soluções Digitais", ln=True, align='C')
    pdf.set_font("Arial", 'I', 12)
    pdf.cell(0, 10, f"Empresa Avaliada: {nome_limpo}", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "1. Diagnóstico de Infraestrutura Digital (T.I e Maps):", ln=True)
    pdf.set_font("Arial", '', 11)
    diag_limpo = limpar_texto_pdf(lead.get('diagnostico_ia', 'Análise não disponível.'))
    pdf.multi_cell(0, 8, diag_limpo)
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "2. Material de Cortesia Gerado por Nossa IA:", ln=True)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 8, "Sugestão de Postagem:", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.multi_cell(0, 8, limpar_texto_pdf(amostras.get('post_proposto', '')))
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 8, "Sugestão de Resposta:", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.multi_cell(0, 8, limpar_texto_pdf(amostras.get('resposta_1', '')))
    return bytes(pdf.output())

def gerar_pdf_proposta(lead):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    nome_limpo = limpar_texto_pdf(lead.get('nome', ''))
    pdf.cell(0, 10, "Proposta de Soluções em T.I. e Presença Digital", ln=True, align='C')
    pdf.set_font("Arial", 'I', 11)
    pdf.cell(0, 8, "DeLimaTec - Tecnologia de Resultados", ln=True, align='C')
    pdf.ln(10)

    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"Preparado exclusivamente para: {nome_limpo}", ln=True)
    pdf.ln(5)

    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 8, "Pacote 1: Presença Digital (Maps) - R$ 197,00 / mês", ln=True)
    pdf.set_font("Arial", '', 10)
    pdf.multi_cell(0, 6, "- Otimização do Google Meu Negócio\n- Resposta a todas as avaliações (IA)\n- 2 Postagens mensais no perfil")
    pdf.ln(5)

    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 8, "Pacote 2: Suporte T.I. Básico - R$ 297,00 / mês", ln=True)
    pdf.set_font("Arial", '', 10)
    pdf.multi_cell(0, 6, "- Suporte Remoto (até 3 computadores)\n- Manutenção preventiva básica\n- SLA de resposta de 6 horas")
    pdf.ln(5)

    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 8, "Pacote 3: Combo DeLimaTec - R$ 397,00 / mês (Melhor Opção)", ln=True)
    pdf.set_font("Arial", '', 10)
    pdf.multi_cell(0, 6, "- Todos os benefícios do Pacote 1 e 2 unidos\n- Prioridade no atendimento (SLA 3h)\n- Economia de R$ 97,00 todos os meses")
    pdf.ln(10)
    
    pdf.set_font("Arial", 'I', 10)
    pdf.multi_cell(0, 6, "Para alinhar os valores de investimento, responda a esta mensagem no WhatsApp e agendaremos uma rápida reunião de alinhamento técnico.")
    return bytes(pdf.output())

# =========================================================================
# PAINEL PRINCIPAL
# =========================================================================
st.title("💻 DeLimaTec OS - Máquina de Vendas e CRM")
if st.button("Sair (Logout)", type="secondary"):
    st.session_state.autenticado = False
    st.rerun()

aba_buscar, aba_vendas, aba_crm, aba_metricas = st.tabs(["🔎 Mineração", "💰 Fila de Vendas", "💼 Pipeline CRM", "📊 Métricas"])

# ==================== ABA 1: MINERAÇÃO & INBOUND ====================
with aba_buscar:
    # 🔔 NOVO BLOCO: DETECTOR AUTOMÁTICO DE LEADS DO SITE
    try:
        leads_site_pendentes = list(db.collection("leads").where("nicho", "==", "Captado via Site").where("status_agencia", "==", "scouted").stream())
        if leads_site_pendentes:
            st.warning(f"🔔 **Novos Cadastros no Site:** Existem **{len(leads_site_pendentes)}** empresas aguardando a Auditoria Gratuita solicitada no site!")
            if st.button("🤖 Processar Leads do Site Agora", type="secondary", use_container_width=True):
                st.markdown("### 💻 Processando Leads Inbound")
                terminal_site = st.empty()
                
                class RedirecionadorSite:
                    def __init__(self, container):
                        self.container = container
                        self.texto = ""
                    def write(self, msg):
                        self.texto += msg
                        self.container.code(self.texto, language="bash")
                    def flush(self): pass

                antigo_stdout = sys.stdout
                sys.stdout = RedirecionadorSite(terminal_site)
                try:
                    with st.spinner("Executando Inteligência Artificial..."):
                        rodar_diagnostico()
                        rodar_builder()
                        rodar_pitcher()
                        st.success("✅ Sucesso! Os clientes do site já estão com os PDFs prontos na 'Fila de Vendas'!")
                        st.rerun()
                except Exception as ex:
                    st.error(f"Erro: {ex}")
                finally:
                    sys.stdout = antigo_stdout
            st.markdown("---")
    except Exception:
        pass

    # Fluxo normal de mineração do Google Maps
    st.subheader("Minerar Novas Regiões (Google Maps)")
    col1, col2 = st.columns(2)
    with col1: nicho = st.text_input("Nicho?", placeholder="Ex: Padaria")
    with col2: localizacao = st.text_input("Local?", placeholder="Ex: Vila Izabel, Guarulhos SP")
    
    if st.button("🚀 Iniciar Automação", type="primary"):
        if nicho and localizacao:
            st.markdown("### 💻 Terminal de Execução")
            terminal_container = st.empty()
            
            class RedirecionadorTerminal:
                def __init__(self, container):
                    self.container = container
                    self.texto = ""
                def write(self, msg):
                    self.texto += msg
                    self.container.code(self.texto, language="bash")
                def flush(self): pass

            antigo_stdout = sys.stdout
            sys.stdout = RedirecionadorTerminal(terminal_container)
            
            try:
                with st.spinner("🤖 Inicializando varredura e IA..."):
                    varrer_regiao(nicho, localizacao)
                    rodar_diagnostico()
                    rodar_builder()
                    rodar_pitcher()
                    st.success("✨ Automação Concluída! Mude para a aba 'Fila de Vendas'.")
            except Exception as e:
                st.error(f"Erro no pipeline: {e}")
            finally:
                sys.stdout = antigo_stdout

# ==================== ABA 2 ====================
with aba_vendas:
    try:
        leads_prontos = list(db.collection("leads").where("status_agencia", "==", "ready_to_send").stream())
        if not leads_prontos:
            st.info("📭 Fila de envios vazia.")
            st.session_state.pagina_vendas = 0
        else:
            total_leads = len(leads_prontos)
            itens_por_pagina = 5
            total_paginas = (total_leads + itens_por_pagina - 1) // itens_por_pagina
            
            if st.session_state.pagina_vendas >= total_paginas:
                st.session_state.pagina_vendas = max(0, total_paginas - 1)
                
            pagina_atual = st.session_state.pagina_vendas
            inicio = pagina_atual * itens_por_pagina
            fim = inicio + itens_por_pagina
            leads_para_exibir = leads_prontos[inicio:fim]
            
            st.write(f"Há **{total_leads}** oportunidades na fila. Exibindo página **{pagina_atual + 1}** de **{total_paginas}**.")
            
            for doc in leads_para_exibir:
                lead = doc.to_dict()
                with st.container(border=True):
                    col_info, col_pitch = st.columns([1, 2])
                    with col_info:
                        st.subheader(lead.get('nome', 'Sem Nome'))
                        st.write(f"🔐 **T.I Site:** {lead.get('status_site', 'Não checado')}")
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
                        
                        if st.button("✅ Marcar Enviado (Mover pro CRM)", key=f"status_{doc.id}"):
                            doc.reference.update({"status_agencia": "sent"})
                            st.rerun()
                            
                    with col_pitch:
                        amostras = lead.get('amostras_geradas', {})
                        if amostras:
                            c1, c2 = st.columns(2)
                            c1.download_button("📄 Baixar Auditoria", gerar_pdf_auditoria(lead, amostras), f"Auditoria_{lead.get('nome')}.pdf", "application/pdf", key=f"aud_{doc.id}")
                            c2.download_button("💼 Baixar Proposta Comercial", gerar_pdf_proposta(lead), f"Proposta_{lead.get('nome')}.pdf", "application/pdf", key=f"prop_{doc.id}")
                            
                        st.text_area("Pitch WhatsApp:", lead.get('pitch_vendas_whatsapp', ''), height=150, key=f"pitch_{doc.id}")
                        
                        if amostras:
                            with st.expander("📝 Ver Post e Respostas"):
                                st.text_area("Post Proposto (DeLimaTec):", amostras.get('post_proposto', ''), height=150, key=f"post_{doc.id}")
                                st.text_area("Resposta Humanizada 1:", amostras.get('resposta_1', ''), height=100, key=f"resp1_{doc.id}")
                                st.text_area("Resposta Humanizada 2:", amostras.get('resposta_2', ''), height=100, key=f"resp2_{doc.id}")
                                
                        imagem_b64 = lead.get('imagem_generated_base64') if lead.get('imagem_generated_base64') else lead.get('imagem_gerada_base64')
                        if imagem_b64:
                            st.markdown("### 🖼️ Criativo Visual para o Post")
                            imagem_bytes = base64.b64decode(imagem_b64)
                            st.image(imagem_bytes, caption="Criativo gerado com sucesso!", use_container_width=True)
                            st.download_button(label="💾 Baixar Imagem", data=imagem_bytes, file_name=f"post_{doc.id}.jpg", mime="image/jpeg", key=f"dl_{doc.id}")
                        else:
                            st.info("Clique abaixo para gerar a imagem na hora.")
                            if st.button("✨ Gerar Imagem Grátis (Gemini)", key=f"img_{doc.id}"):
                                with st.spinner("Desenhando imagem..."):
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
                                        if sucesso_geracao:
                                            img_base64_otimizada = otimizar_imagem_base64(img_base64_str)
                                            doc.reference.update({"imagem_gerada_base64": img_base64_otimizada})
                                            st.rerun()
                                    except Exception as e:
                                        st.error(f"Erro ao gerar imagem: {e}")

            st.markdown("---")
            col_anterior, col_centro, col_proxima = st.columns([1, 2, 1])
            with col_anterior:
                if pagina_atual > 0:
                    if st.button("⬅️ Página Anterior"):
                        st.session_state.pagina_vendas -= 1
                        st.rerun()
            with col_centro:
                st.markdown(f"<p style='text-align: center; font-weight: bold;'>Página {pagina_atual + 1} de {total_paginas}</p>", unsafe_allow_html=True)
            with col_proxima:
                if pagina_atual < total_paginas - 1:
                    if st.button("Próxima Página ➡️"):
                        st.session_state.pagina_vendas += 1
                        st.rerun()
                        
    except Exception as e:
        st.error(f"Erro ao carregar os leads: {e}")

# ==================== ABA 3: CRM KANBAN ====================
with aba_crm:
    try:
        st.header("💼 Gestão de Vendas (Kanban)")
        st.write("Acompanhe e movimente os leads enviados.")
        
        col_enviado, col_negociando, col_reuniao, col_fechado = st.columns(4)
        
        leads_crm = list(db.collection("leads").where("status_agencia", "in", ["sent", "negotiating", "meeting", "closed"]).stream())
        
        with col_enviado: st.markdown("### 📨 Enviado")
        with col_negociando: st.markdown("### 💬 Em Negociação")
        with col_reuniao: st.markdown("### 📅 Reunião")
        with col_fechado: st.markdown("### 💰 Fechado")
            
        for doc in leads_crm:
            lead = doc.to_dict()
            status = lead.get('status_agencia')
            
            target_col = col_enviado
            if status == "negotiating": target_col = col_negociando
            elif status == "meeting": target_col = col_reuniao
            elif status == "closed": target_col = col_fechado
            
            with target_col:
                with st.container(border=True):
                    st.write(f"**{lead.get('nome')}**")
                    tel = lead.get('telefone', '')
                    if tel: st.caption(f"📞 {tel}")
                    st.caption(f"🔐 Site: {lead.get('status_site', 'Não checado')}")
                    
                    if status in ["sent", "negotiating"]:
                        fup_texto = lead.get("follow_up_texto")
                        if fup_texto:
                            st.text_area("Texto de Follow-up:", fup_texto, height=100, key=f"txt_{doc.id}")
                        else:
                            if st.button("🔁 Gerar Follow-up (IA)", key=f"fup_btn_{doc.id}"):
                                with st.spinner("Pensando..."):
                                    texto = gerar_follow_up_com_claude(lead)
                                    doc.reference.update({"follow_up_texto": texto})
                                    st.rerun()

                    if status == "sent":
                        if st.button("➡️ Respondeu (Negociando)", key=f"mv_neg_{doc.id}"):
                            doc.reference.update({"status_agencia": "negotiating"})
                            st.rerun()
                    elif status == "negotiating":
                        if st.button("📅 Agendar Reunião", key=f"mv_reu_{doc.id}"):
                            doc.reference.update({"status_agencia": "meeting"})
                            st.rerun()
                    elif status == "meeting":
                        if st.button("💰 Fechar Contrato", type="primary", key=f"mv_fec_{doc.id}"):
                            doc.reference.update({"status_agencia": "closed"})
                            st.rerun()
    except Exception as e:
        st.error(f"Erro no CRM: {e}")

# ==================== ABA 4 ====================
with aba_metricas:
    try:
        st.header("📈 Desempenho DeLimaTec")
        todos_leads = list(db.collection("leads").stream())
        total = len(todos_leads)
        enviados = len([l for l in todos_leads if l.to_dict().get('status_agencia') in ['sent', 'negotiating', 'meeting', 'closed']])
        fechados = len([l for l in todos_leads if l.to_dict().get('status_agencia') == 'closed'])
        
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Empresas Mapeadas", total)
        col_m2.metric("Prospecções Ativas", enviados)
        col_m3.metric("Contratos Fechados", fechados)
    except Exception as e:
        st.error(f"Erro nas métricas: {e}")
