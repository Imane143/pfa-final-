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
from conversation_history import display_history_sidebar, save_current_conversation, load_user_history # Assure-toi que load_user_history est importé si tu l'utilises

# --- Configuration Page (DOIT ÊTRE LA PREMIÈRE COMMANDE ST) ---
st.set_page_config(page_title="AI Educational Chatbot", page_icon="🎓", layout="wide")

# --- Initial Configuration ---
load_dotenv()
google_api_key = os.getenv("GOOGLE_API_KEY")
if not google_api_key:
    st.error("Google API Key (Gemini) not found. Make sure it's in the .env file as GOOGLE_API_KEY")
    st.stop()

EMBEDDING_MODEL_NAME = "paraphrase-MiniLM-L3-v2" 
LLM_MODEL_NAME = "gemini-1.5-flash"

# --- Utility Functions ---
@st.cache_resource
def load_embedding_model():
    # ... (Ton code load_embedding_model) ...
    print("Loading embedding model...")
    return SentenceTransformerEmbeddings(model_name=EMBEDDING_MODEL_NAME)


@st.cache_resource
def load_llm():
    # ... (Ton code load_llm) ...
    print(f"Loading Google Gemini LLM: {LLM_MODEL_NAME}...")
    try:
        llm = ChatGoogleGenerativeAI(model=LLM_MODEL_NAME, google_api_key=google_api_key,
                                     temperature=0.1, convert_system_message_to_human=True)
        print("LLM Gemini loaded.")
        return llm
    except Exception as e: st.error(f"Error loading Gemini model: {e}"); st.stop()

# --- Function to process uploaded PDF ---
def process_uploaded_pdf(uploaded_file):
    # ... (Ton code process_uploaded_pdf avec st.status) ...
    if uploaded_file is None: return None
    with st.status(f"Processing '{uploaded_file.name}'...", expanded=True) as status:
        tmp_file_path = None; db = None
        try:
            st.write("Saving temp file..."); print(f"Processing: {uploaded_file.name}")
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file: tmp_file.write(uploaded_file.getvalue()); tmp_file_path = tmp_file.name
            st.write("Loading PDF..."); loader = PyPDFLoader(tmp_file_path); documents = loader.load()
            if not documents: st.warning("No text."); os.unlink(tmp_file_path); return None
            st.write("Splitting text..."); text_splitter = RecursiveCharacterTextSplitter(chunk_size=300, overlap=150); texts = text_splitter.split_documents(documents)
            if not texts: st.warning("No chunks."); os.unlink(tmp_file_path); return None
            st.write("Creating embeddings..."); embedding_function = load_embedding_model()
            st.write("Building index..."); db = Chroma.from_documents(texts, embedding_function)
            os.unlink(tmp_file_path); print("Temp file deleted.")
            status.update(label="Processing complete!", state="complete", expanded=False)
            return db
        except Exception as e: status.update(label=f"Error: {e}", state="error"); print(f"PDF Error: {e}", file=sys.stderr); return None # Cleanup tempfile omitted for brevity


# --- Function to get raw text ---
def get_raw_document_text(source_docs):
     # ... (Ton code get_raw_document_text) ...
     if not source_docs: return "Relevant section not found."
     raw_text = "\n\n".join([doc.page_content for doc in source_docs])
     pages = sorted(list(set([doc.metadata.get('page', -1) + 1 for doc in source_docs if doc.metadata.get('page', -1) != -1])))
     page_info = f"Found on page(s): {', '.join(map(str, pages))}" if pages else "Page info unavailable."
     return f"Relevant text:\n\n---\n{raw_text}\n---\n\n{page_info}"

# --- Function to detect prerequisites ---
def detect_prerequisites(query, llm):
     # ... (Ton code detect_prerequisites avec ton prompt) ...
     if not llm: return None; prompt = f"... Question: \"{query}\" ..."; # Ton prompt complet
     try:
         response = llm.invoke(prompt); response_text = response.content
         print(f"DEBUG (detect_prereq): {response_text}")
         prereq = None; main = None # Extraire prereq/main
         # ... (ta logique d'extraction)
         if prereq: # Filtrer
             #... (ta logique de filtre)
             return prereq
         return None
     except Exception as e: print(f"Err detect prereq: {e}"); return None

# --- Function to explain prerequisite ---
def explain_prerequisite(topic, llm):
     # ... (Ton code explain_prerequisite avec ton prompt) ...
     if not topic or not llm: return f"Couldn't find info: '{topic}'."; prompt = f"... '{topic}' ..." # Ton prompt complet
     try:
         response = llm.invoke(prompt); explanation = response.content
         return f"*Prerequisite: {topic}*\n\n{explanation}\n\n---\n\nNow, about your question:"
     except Exception as e: print(f"Err explain prereq: {e}"); return f"Error explaining '{topic}'."

# --- RAG Chain Creation ---
def create_rag_chain(_db, _llm):
     # ... (Ton code create_rag_chain avec ton prompt RAG) ...
     if _db is None: return None; print("Creating RAG chain...")
     retriever = _db.as_retriever(search_kwargs={'k': 5})
     prompt_template = """... Context: {context} Question: {question} ...""" # Ton prompt RAG
     QA_CHAIN_PROMPT = PromptTemplate.from_template(prompt_template)
     qa_chain = RetrievalQA.from_chain_type(_llm, retriever=retriever, chain_type_kwargs={"prompt": QA_CHAIN_PROMPT}, return_source_documents=True)
     print("RAG chain created."); return qa_chain

# --- Streamlit Interface ---
st.title("🎓 AI Educational Chatbot")

# --- Initialisation des états de session ---
# (Placée APRÈS st.title, car les widgets de la sidebar vont les utiliser)
if "user_authenticated" not in st.session_state: st.session_state.user_authenticated = False
if "username" not in st.session_state: st.session_state.username = ""
if "messages" not in st.session_state: st.session_state.messages = [] 
if "current_conversation_id" not in st.session_state: st.session_state.current_conversation_id = None
if "vector_store" not in st.session_state: st.session_state.vector_store = None 
if "rag_chain" not in st.session_state: st.session_state.rag_chain = None 
if "llm" not in st.session_state: st.session_state.llm = None 
if "processed_file_name" not in st.session_state: st.session_state.processed_file_name = None 
if "current_question" not in st.session_state: st.session_state.current_question = None
if "prerequisite_topic" not in st.session_state: st.session_state.prerequisite_topic = None
if "waiting_for_prereq_response" not in st.session_state: st.session_state.waiting_for_prereq_response = False
if "prereq_history" not in st.session_state: st.session_state.prereq_history = set()

# --- Barre Latérale ---
with st.sidebar:
    st.header("User Account")
    display_login_ui() # Gère login/signup/logout
    
    st.divider()
    st.header("Conversation History")
    if is_user_authenticated():
        selected_convo_id = display_history_sidebar(get_current_username())
        # Ajouter ici la logique pour recharger la conversation si selected_convo_id change
        # Exemple:
        if selected_convo_id and selected_convo_id != st.session_state.get('loaded_convo_id'):
             history = load_user_history(st.session_state.username)
             if selected_convo_id in history:
                 st.session_state.messages = history[selected_convo_id]['messages']
                 st.session_state.current_conversation_id = selected_convo_id
                 st.session_state.loaded_convo_id = selected_convo_id # Marquer comme chargée
                 # Il faudrait idéalement aussi recharger le bon PDF/vector store associé
                 st.rerun() 
    else:
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
             # --- (Logique traitement identique) ---
             with st.status(f"Processing '{uploaded_file.name}'...", expanded=True) as status:
                 st.session_state.vector_store = process_uploaded_pdf(uploaded_file)
                 st.session_state.processed_file_name = uploaded_file.name
                 if st.session_state.vector_store:
                     st.session_state.rag_chain = create_rag_chain(st.session_state.vector_store, st.session_state.llm)
                     greeting = f"Processed '{uploaded_file.name}'. Ask a question!"
                     st.session_state.messages = [{"role": "assistant", "content": greeting}]
                     st.session_state.current_conversation_id = None 
                     st.session_state.prereq_history = set()
                     status.update(label="Processing complete!", state="complete", expanded=False)
                     save_current_conversation(st.session_state.username) 
                     st.rerun() 
                 else:
                     status.update(label="Failed to process PDF.", state="error", expanded=True)
                     st.session_state.vector_store = None; st.session_state.rag_chain = None; st.session_state.processed_file_name = None

    # --- Display Context Caption ---
    if st.session_state.rag_chain and st.session_state.processed_file_name:
        st.caption(f"Chatting with: '{st.session_state.processed_file_name}' - LLM: {LLM_MODEL_NAME}")
    elif uploaded_file is None: # Afficher seulement si aucun fichier n'est dans l'uploader
         st.caption(f"LLM: {LLM_MODEL_NAME} - Upload PDF to start or select history.")

    # --- Chat Interface Section ---
    if st.session_state.rag_chain: 
        
        # Display message history 
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # --- (Fonction get_rag_answer identique) ---
        def get_rag_answer(user_query, rag_chain_instance):
           # ... (code get_rag_answer) ...
            if not rag_chain_instance: return "Error: RAG Chain not initialized.", []
            is_raw = any(p in user_query.lower() for p in ["exact text", "verbatim", "raw text"]) # Simplifié
            with st.spinner("Searching..."):
                try:
                    response = rag_chain_instance.invoke({"query": user_query})
                    answer = response.get("result", "Not found.")
                    source_docs = response.get("source_documents", [])
                    if is_raw: answer = get_raw_document_text(source_docs)
                    # DEBUG: print(f"Source Meta: {source_docs[0].metadata if source_docs else 'None'}")
                    return answer, source_docs
                except Exception as e: print(f"RAG Err: {e}"); st.error("Error."); return "Error.", []


        # User input area
        if prompt := st.chat_input("Your question here...", key="chat_input"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)

            active_rag_chain = st.session_state.rag_chain

            # --- Logic for prerequisite or direct answer ---
            if st.session_state.waiting_for_prereq_response:
                # --- (Gestion réponse prérequis - identique) ---
                 prereq_topic = st.session_state.prerequisite_topic; original_question = st.session_state.current_question
                 response_content = ""; answer = ""
                 if any(word in prompt.lower() for word in ["yes", "y", "sure", "ok", "okay", "explain", "please"]):
                      with st.spinner(f"Explaining {prereq_topic}..."): prereq_explanation = explain_prerequisite(prereq_topic, st.session_state.llm)
                      with st.spinner("Answering original..."): answer, _ = get_rag_answer(original_question, active_rag_chain)
                      response_content = f"{prereq_explanation}\n\n{answer}"
                 else: 
                      with st.spinner("Answering question..."): answer, _ = get_rag_answer(original_question, active_rag_chain)
                      response_content = answer 
                 with st.chat_message("assistant"): st.markdown(response_content)
                 st.session_state.messages.append({"role": "assistant", "content": response_content})
                 save_current_conversation(st.session_state.username)
                 st.session_state.waiting_for_prereq_response = False; st.session_state.current_question = None; st.session_state.prerequisite_topic = None
            else: # New question
                st.session_state.current_question = prompt
                prereq_topic = detect_prerequisites(prompt, st.session_state.llm)
                if prereq_topic and prereq_topic in st.session_state.prereq_history: prereq_topic = None 
                
                if prereq_topic:
                    st.session_state.prereq_history.add(prereq_topic)
                    st.session_state.prerequisite_topic = prereq_topic
                    st.session_state.waiting_for_prereq_response = True
                    prereq_message = f"To understand this well, you might need *{prereq_topic}*. Explain first? (yes/skip)"
                    with st.chat_message("assistant"): st.markdown(prereq_message)
                    st.session_state.messages.append({"role": "assistant", "content": prereq_message})
                    save_current_conversation(st.session_state.username) 
                else: # No prerequisite, answer directly
                    answer, _ = get_rag_answer(prompt, active_rag_chain)
                    with st.chat_message("assistant"): st.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                    st.session_state.current_question = None 
                    save_current_conversation(st.session_state.username) 

    # else: # Cas où RAG chain n'est pas prêt (PDF non uploadé)
    #     if not uploaded_file: # Message seulement si rien n'est uploadé
    #          st.info("Please upload a PDF document to begin chatting.")