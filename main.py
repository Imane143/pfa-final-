# --- Code main.py - Intégration Login & Historique - STRUCTURE CORRIGÉE ---

import os
import streamlit as st
from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_core.messages import HumanMessage, AIMessage 
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import tempfile
import sys
# --- Imports pour Auth & Historique ---
from user_auth import display_login_ui, is_user_authenticated, get_current_username
from conversation_history import display_history_sidebar, save_current_conversation, load_user_history

# --- Chargement des variables d'environnement AVANT tout appel à Streamlit ---
load_dotenv()

# --- Fonction pour le sélecteur de thème (définie AVANT d'être utilisée) ---
def add_theme_selector():
    # Initialisation
    if "theme" not in st.session_state:
        st.session_state.theme = "light"
    if "color_scheme" not in st.session_state:
        st.session_state.color_scheme = 0
    
    # Définir les couleurs pour chaque thème
    color_schemes = {
        "blue": {"primary": "#1E88E5", "secondary": "#BBDEFB"},
        "green": {"primary": "#43A047", "secondary": "#C8E6C9"}, 
        "purple": {"primary": "#8E24AA", "secondary": "#E1BEE7"},
        "orange": {"primary": "#FB8C00", "secondary": "#FFE0B2"}
    }
    
    color_keys = list(color_schemes.keys())
    active_color_key = color_keys[st.session_state.color_scheme]
    active_color = color_schemes[active_color_key]["primary"]
    active_secondary = color_schemes[active_color_key]["secondary"]
    
    # Créer les colonnes avec les boutons en haut à droite
    cols = st.columns([6, 1, 1])
    
    # Bouton pour changer de thème avec clé unique
    with cols[1]:
        if st.button("🌓", key="theme_button"):
            st.session_state.theme = "dark" if st.session_state.theme == "light" else "light"
            st.rerun()
    
    # Bouton pour changer de couleur avec clé unique
    with cols[2]:
        if st.button("🎨", key="color_button"):
            st.session_state.color_scheme = (st.session_state.color_scheme + 1) % len(color_keys)
            st.rerun()
    
    # Définir les couleurs en fonction du thème
    is_dark = st.session_state.theme == "dark"
    
    # Couleurs pour le thème sombre/clair
    bg_color = "#121212" if is_dark else "#FFFFFF"
    text_color = "#FFFFFF" if is_dark else "#000000"
    sidebar_bg = "#1E1E1E" if is_dark else active_secondary
    card_bg = "#2D2D2D" if is_dark else "#FFFFFF"
    input_bg = "#2D2D2D" if is_dark else "#FFFFFF"
    border_color = "#555555" if is_dark else active_color
    
    # CSS complet pour modifier toute l'interface
    css = f"""
    <style>
        /* Styles globaux - Appliqués à tous les éléments */
        body, .stApp, section, main, header, footer, div, span, p, a, button, input, textarea, select, option {{
            color: {text_color} !important;
        }}
        
        /* Corps principal */
        body, .stApp, .main, section[data-testid="stAppViewContainer"], main, div.stApp > div {{
            background-color: {bg_color} !important;
        }}
        
        /* En-têtes et titres */
        h1, h2, h3, h4, h5, h6, .stMarkdown {{
            color: {text_color} !important;
        }}
        
        /* Barre latérale */
        section[data-testid="stSidebar"] {{
            background-color: {sidebar_bg} !important;
        }}
        
        /* Champs de saisie et boutons */
        button, input, textarea, select, .stTextInput > div, .stTextInput input,
        div.stTextArea textarea, div.stFileUploader,
        .stSelectbox > div, button[data-testid="baseButton-secondary"] {{
            background-color: {input_bg} !important;
            color: {text_color} !important;
            border-color: {border_color} !important;
        }}
        
        /* Champ de saisie de chat */
        div[data-testid="stChatInput"], .stChatInputContainer {{
            background-color: {input_bg} !important;
            color: {text_color} !important;
            border-color: {border_color} !important;
        }}
        
        /* Messages de chat */
        div[data-testid="stChatMessage"] {{
            background-color: {card_bg} !important;
            color: {text_color} !important;
        }}
        
        /* Bouton d'envoi et autres boutons d'action */
        button[kind="primary"], button[data-testid="chat-input-submit-button"],
        div[data-testid="stChatInput"] button {{
            background-color: {active_color} !important;
            color: {"#FFFFFF" if is_dark else "#FFFFFF"} !important;
        }}
        
        /* Zone de drop pour fichiers */
        div.stUploadDropzone, div.stFileUploader, div.uploadedFileInfo {{
            background-color: {input_bg} !important;
            color: {text_color} !important;
            border-color: {border_color} !important;
        }}
        
        /* Éléments blancs spécifiques dans le mode sombre */
        .main .block-container {{
            background-color: {bg_color} !important;
        }}
        
        /* Lien et accents de couleur */
        a, span[data-baseweb="tag"], div[role="radiogroup"] div[aria-checked="true"],
        label[data-baseweb="checkbox"] div[data-testid="stTickedContent"] {{
            color: {active_color} !important;
        }}
        
        /* Onglets et accordéons */
        button[role="tab"] {{
            color: {text_color} !important;
            background-color: {"transparent"} !important;
        }}
        
        /* Tous les autres éléments blancs qui pourraient apparaître */
        .stAlert, .stInfoBox, div[data-testid="stExpander"] {{
            background-color: {card_bg} !important;
            color: {text_color} !important;
            border-color: {border_color} !important;
        }}
        
        /* Zone de l'uploader de fichier */
        div[data-testid="stFileUploader"] {{
            background-color: {input_bg} !important;
            color: {text_color} !important;
        }}
        
        div[data-testid="stFileUploader"] > div {{
            background-color: {input_bg} !important;
        }}
        
        button[data-testid="baseButton-secondary"] {{
            border-color: {active_color} !important;
            color: {active_color} !important;
        }}
        
        /* Zone de login/signup */
        div[data-testid="stExpander"] {{
            background-color: {sidebar_bg} !important;
        }}
        
        /* Zone de chat complète */
        div[data-testid="stChatMessageContent"] {{
            background-color: {bg_color} !important;
        }}
        
        /* Icônes de visibilité du mot de passe */
        div.stPasswordInput {{
            position: relative;
        }}
        
        div.stPasswordInput span {{
            color: {text_color} !important;
        }}
        
        /* Couleur des boutons de navigation et menus */
        [data-testid="stFormSubmitButton"] button, 
        [data-testid="baseButton-secondary"],
        button.css-15cjy8h {{
            background-color: {active_color if not is_dark else "#2D2D2D"} !important;
            color: {("#FFFFFF" if not is_dark else text_color)} !important;
            border-color: {active_color} !important;
        }}
        
        /* Corrige spécifiquement la zone d'upload avec le message "Drag and drop" */
        div.stUploadDropzoneInstructions {{
            background-color: {input_bg} !important;
            color: {text_color} !important;
        }}
        
        div.stUploadDropzoneInstructions span {{
            color: {text_color} !important;
        }}
        
        /* Corrige la barre de progression */
        div.stProgress div.stProgressIndicator {{
            background-color: {active_color} !important;
        }}
    </style>
    """
    
    # Appliquer le CSS
    st.markdown(css, unsafe_allow_html=True)

# --- Configuration Page (DOIT ÊTRE LA PREMIÈRE COMMANDE ST) ---
st.set_page_config(page_title="AI Educational Chatbot", page_icon="🎓", layout="wide")

# Ajouter le sélecteur de thème après la configuration de la page
add_theme_selector()

# --- Initial Configuration ---
google_api_key = os.getenv("GOOGLE_API_KEY")
if not google_api_key:
    st.error("Google API Key (Gemini) not found. Make sure it's in the .env file as GOOGLE_API_KEY")
    st.stop()

EMBEDDING_MODEL_NAME = "paraphrase-MiniLM-L3-v2" 
LLM_MODEL_NAME = "gemini-1.5-flash"

# --- Initialisation des états de session ---
if "user_authenticated" not in st.session_state: 
    st.session_state.user_authenticated = False
if "username" not in st.session_state: 
    st.session_state.username = ""
if "messages" not in st.session_state: 
    st.session_state.messages = [{"role": "assistant", "content": "Hello! How can I help you today?"}]
if "current_conversation_id" not in st.session_state: 
    st.session_state.current_conversation_id = None
if "loaded_convo_id" not in st.session_state:  # Ajout de cette variable importante
    st.session_state.loaded_convo_id = None
if "vector_store" not in st.session_state: 
    st.session_state.vector_store = None 
if "rag_chain" not in st.session_state: 
    st.session_state.rag_chain = None 
if "llm" not in st.session_state:  # Cette ligne est importante
    st.session_state.llm = None
if "processed_file_name" not in st.session_state: 
    st.session_state.processed_file_name = None 
if "current_question" not in st.session_state: 
    st.session_state.current_question = None
if "prerequisite_topic" not in st.session_state: 
    st.session_state.prerequisite_topic = None
if "waiting_for_prereq_response" not in st.session_state: 
    st.session_state.waiting_for_prereq_response = False
if "prereq_history" not in st.session_state: 
    st.session_state.prereq_history = set()

# --- Utility Functions ---
@st.cache_resource
def load_embedding_model():
    print("Loading embedding model...")
    return SentenceTransformerEmbeddings(model_name=EMBEDDING_MODEL_NAME)


@st.cache_resource
def load_llm():
    print(f"Loading Google Gemini LLM: {LLM_MODEL_NAME}...")
    try:
        llm = ChatGoogleGenerativeAI(model=LLM_MODEL_NAME, google_api_key=google_api_key,
                                     temperature=0.1, convert_system_message_to_human=True)
        print("LLM Gemini loaded.")
        return llm
    except Exception as e: st.error(f"Error loading Gemini model: {e}"); st.stop()

# --- Function to process uploaded PDF ---
def process_uploaded_pdf(uploaded_file):
    if uploaded_file is None: return None
    tmp_file_path = None
    db = None
    
    try:
        print(f"Processing: {uploaded_file.name}")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file: 
            tmp_file.write(uploaded_file.getvalue())
            tmp_file_path = tmp_file.name
        
        loader = PyPDFLoader(tmp_file_path)
        documents = loader.load()
        
        if not documents: 
            print("No text found in document.")
            os.unlink(tmp_file_path)
            return None
        
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=150)
        texts = text_splitter.split_documents(documents)
        
        if not texts: 
            print("No chunks created.")
            os.unlink(tmp_file_path)
            return None
        
        embedding_function = load_embedding_model()
        db = Chroma.from_documents(texts, embedding_function)
        os.unlink(tmp_file_path)
        print("Temp file deleted.")
        
        return db
    except Exception as e: 
        print(f"PDF Error: {e}", file=sys.stderr)
        if tmp_file_path and os.path.exists(tmp_file_path):
            os.unlink(tmp_file_path)
        return None


# --- Function to get raw text ---
def get_raw_document_text(source_docs):
     if not source_docs: return "Relevant section not found."
     raw_text = "\n\n".join([doc.page_content for doc in source_docs])
     pages = sorted(list(set([doc.metadata.get('page', -1) + 1 for doc in source_docs if doc.metadata.get('page', -1) != -1])))
     page_info = f"Found on page(s): {', '.join(map(str, pages))}" if pages else "Page info unavailable."
     return f"Relevant text:\n\n---\n{raw_text}\n---\n\n{page_info}"

# --- Function to detect prerequisites ---
def detect_prerequisites(query, llm):
     if not llm: return None
     prompt = """Examine the following question related to educational content. Based on the question, determine if there's a prerequisite topic that the student likely needs to understand first before comprehending the answer. 

Question: "{query}"

First, analyze what topics are directly asked about in the question. Then, consider what foundational concepts would be necessary to understand these topics. If there is a clear prerequisite concept that is not explicitly mentioned in the question but is necessary to understand the answer, identify it.

Output format:
Prerequisite: [Single most important prerequisite topic or None if no clear prerequisite exists]

Examples:
- If asked about "solving quadratic equations" a prerequisite might be "linear equations"
- If asked about "Newton's Second Law" a prerequisite might be "force and mass concepts"
- If asked about simple concepts with no prerequisites, output "None"

Output ONLY the prerequisite topic name or "None". Keep it concise - max 5 words."""

     try:
         response = llm.invoke(prompt.format(query=query))
         response_text = response.content
         print(f"DEBUG (detect_prereq): {response_text}")
         
         # Parse response
         prereq = response_text.strip()
         if prereq.lower() == "none":
             return None
         
         # Filter out non-prerequisites
         low_value_prereqs = ["basic", "fundamental", "introduction", "concept", "definition"]
         if any(term in prereq.lower() for term in low_value_prereqs):
             return None
             
         return prereq
     except Exception as e: 
         print(f"Error detecting prerequisites: {e}")
         return None

# --- Function to explain prerequisite ---
def explain_prerequisite(topic, llm):
     if not topic or not llm: return f"Couldn't find info: '{topic}'."
     
     prompt = f"""Provide a clear, concise explanation of '{topic}' suitable for a student who needs this information as background knowledge. The explanation should:
1. Define what '{topic}' is in simple terms
2. Explain why it's important or useful
3. Include 1-2 simple examples if applicable
4. Be educational and suitable for a student

Keep the explanation under 200 words, focusing on clarity and helpfulness."""

     try:
         response = llm.invoke(prompt)
         explanation = response.content
         return f"*Prerequisite: {topic}*\n\n{explanation}\n\n---\n\nNow, about your question:"
     except Exception as e: 
         print(f"Error explaining prerequisite: {e}")
         return f"Error explaining '{topic}'."

# --- RAG Chain Creation ---
def create_rag_chain(_db, _llm):
     if _db is None: return None
     print("Creating RAG chain...")
     retriever = _db.as_retriever(search_kwargs={'k': 5})
     prompt_template = """You are a helpful educational assistant. Your task is to answer questions about educational content based on provided text snippets.

Context information is below:
{context}

Given the context information and not prior knowledge, answer the question:
{question}

Answer in a structured, educational way that helps the student understand the topic deeply. If the context doesn't contain the information needed, admit that you don't have enough information rather than making up an answer.
If the question asks for raw text or verbatim content, provide only the relevant sections from the context.
If the question is about a complex concept, break it down into simpler components.
If appropriate, include examples, analogies, or step-by-step explanations."""

     QA_CHAIN_PROMPT = PromptTemplate.from_template(prompt_template)
     qa_chain = RetrievalQA.from_chain_type(_llm, retriever=retriever, chain_type_kwargs={"prompt": QA_CHAIN_PROMPT}, return_source_documents=True)
     print("RAG chain created.")
     return qa_chain

# --- Streamlit Interface ---
st.title("🎓 AI Educational Chatbot")

# --- Barre Latérale ---
with st.sidebar:
    st.header("User Account")
    display_login_ui() # Gère login/signup/logout
    
    st.divider()
    
    # Afficher l'historique uniquement si l'utilisateur est authentifié
    if is_user_authenticated():
        st.header("Conversation History")
        # Appeler display_history_sidebar sans logique superflue
        display_history_sidebar(get_current_username())
    else:
        st.header("Conversation History")
        st.info("Log in to see conversation history.")

# --- Interface Principale (Conditionnée par l'authentification) ---
if not is_user_authenticated():
    st.warning("Please log in or sign up using the sidebar to use the chatbot.")
    # Pas besoin de st.stop() ici, le reste ne s'affichera pas de toute façon
else:
    # --- Affiche l'interface du chatbot SEULEMENT si connecté ---
    st.success(f"Welcome {st.session_state.username}!") 

    # Charger le LLM une seule fois par session authentifiée
    if st.session_state.llm is None:
        st.session_state.llm = load_llm()

    # --- File Upload Section ---
    uploaded_file = st.file_uploader("Upload your course PDF here:", type="pdf", key="fileuploader")

    # --- Logic to process upload ---
    if uploaded_file is not None:
        if uploaded_file.name != st.session_state.processed_file_name:
            # Remplacer st.status par st.info et une barre de progression
            st.info(f"Processing '{uploaded_file.name}'...")
            progress_bar = st.progress(0)
            
            # Traiter le PDF
            try:
                st.write("Saving temp file...")
                progress_bar.progress(20)
                print(f"Processing: {uploaded_file.name}")
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_file_path = tmp_file.name
                
                st.write("Loading PDF...")
                progress_bar.progress(40)
                loader = PyPDFLoader(tmp_file_path)
                documents = loader.load()
                
                if not documents:
                    st.warning("No text found in the document.")
                    os.unlink(tmp_file_path)
                    progress_bar.empty()
                else:
                    st.write("Splitting text...")
                    progress_bar.progress(60)
                    text_splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=150)
                    texts = text_splitter.split_documents(documents)
                    
                    if not texts:
                        st.warning("No chunks created.")
                        os.unlink(tmp_file_path)
                        progress_bar.empty()
                    else:
                        st.write("Creating embeddings...")
                        progress_bar.progress(80)
                        embedding_function = load_embedding_model()
                        
                        st.write("Building index...")
                        st.session_state.vector_store = Chroma.from_documents(texts, embedding_function)
                        progress_bar.progress(100)
                        
                        os.unlink(tmp_file_path)
                        print("Temp file deleted.")
                        
                        st.session_state.processed_file_name = uploaded_file.name
                        st.session_state.rag_chain = create_rag_chain(st.session_state.vector_store, st.session_state.llm)
                        
                        greeting = f"Processed '{uploaded_file.name}'. Ask a question!"
                        st.session_state.messages = [{"role": "assistant", "content": greeting}]
                        st.session_state.current_conversation_id = None 
                        st.session_state.loaded_convo_id = None
                        st.session_state.prereq_history = set()
                        
                        save_current_conversation(st.session_state.username)
                        
                        st.success("Processing complete!")
                        st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
                st.session_state.vector_store = None
                st.session_state.rag_chain = None
                st.session_state.processed_file_name = None
                if 'tmp_file_path' in locals():
                    os.unlink(tmp_file_path)

    # --- Display Context Caption ---
    if st.session_state.rag_chain and st.session_state.processed_file_name:
        st.caption(f"Chatting with: '{st.session_state.processed_file_name}' - LLM: {LLM_MODEL_NAME}")
    elif uploaded_file is None: # Afficher seulement si aucun fichier n'est dans l'uploader
         st.caption(f"LLM: {LLM_MODEL_NAME} - Upload PDF to start or select history.")

    # --- Chat Interface Section ---
    # Afficher l'historique de messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # --- Function pour obtenir une réponse RAG ---
    def get_rag_answer(user_query, rag_chain_instance):
        if not rag_chain_instance: return "Error: RAG Chain not initialized.", []
        is_raw = any(p in user_query.lower() for p in ["exact text", "verbatim", "raw text"])
        with st.spinner("Searching..."):
            try:
                response = rag_chain_instance.invoke({"query": user_query})
                answer = response.get("result", "Not found.")
                source_docs = response.get("source_documents", [])
                if is_raw: answer = get_raw_document_text(source_docs)
                return answer, source_docs
            except Exception as e: 
                print(f"RAG Error: {e}")
                st.error("An error occurred.")
                return "Error processing your question.", []

    # Zone de saisie utilisateur - seulement si on a un RAG chain
    if st.session_state.rag_chain:
        if prompt := st.chat_input("Your question here...", key="chat_input"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)

            active_rag_chain = st.session_state.rag_chain

            # --- Logic for prerequisite or direct answer ---
            if st.session_state.waiting_for_prereq_response:
                # Gestion de la réponse à la question "expliquer le prérequis ?"
                prereq_topic = st.session_state.prerequisite_topic
                original_question = st.session_state.current_question
                response_content = ""
                
                if any(word in prompt.lower() for word in ["yes", "y", "sure", "ok", "okay", "explain", "please"]):
                    with st.spinner(f"Explaining {prereq_topic}..."):
                        prereq_explanation = explain_prerequisite(prereq_topic, st.session_state.llm)
                    with st.spinner("Answering original question..."):
                        answer, _ = get_rag_answer(original_question, active_rag_chain)
                    response_content = f"{prereq_explanation}\n\n{answer}"
                else: 
                    with st.spinner("Answering question..."):
                        answer, _ = get_rag_answer(original_question, active_rag_chain)
                    response_content = answer 
                    
                with st.chat_message("assistant"): st.markdown(response_content)
                st.session_state.messages.append({"role": "assistant", "content": response_content})
                save_current_conversation(st.session_state.username)
                st.session_state.waiting_for_prereq_response = False
                st.session_state.current_question = None
                st.session_state.prerequisite_topic = None
            else: # Nouvelle question
                st.session_state.current_question = prompt
                prereq_topic = detect_prerequisites(prompt, st.session_state.llm)
                # Éviter de répéter un prérequis déjà expliqué
                if prereq_topic and prereq_topic in st.session_state.prereq_history:
                    prereq_topic = None 
                
                if prereq_topic:
                    st.session_state.prereq_history.add(prereq_topic)
                    st.session_state.prerequisite_topic = prereq_topic
                    st.session_state.waiting_for_prereq_response = True
                    prereq_message = f"To understand this well, you might need *{prereq_topic}*. Explain first? (yes/skip)"
                    with st.chat_message("assistant"): st.markdown(prereq_message)
                    st.session_state.messages.append({"role": "assistant", "content": prereq_message})
                    save_current_conversation(st.session_state.username) 
                else: # Pas de prérequis, répondre directement
                    answer, _ = get_rag_answer(prompt, active_rag_chain)
                    with st.chat_message("assistant"): st.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                    st.session_state.current_question = None 
                    save_current_conversation(st.session_state.username) 
    else:
        # Message d'information si aucun PDF n'est chargé
        if not st.session_state.processed_file_name and is_user_authenticated():
            st.info("Please upload a PDF document or select a conversation from history to begin chatting.")