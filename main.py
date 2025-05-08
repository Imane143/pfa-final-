# --- Code main.py - Intégration Login & Historique - STRUCTURE CORRIGÉE ---

from database_manager import initialize_database, migrate_from_json
import os
import streamlit as st
from dotenv import load_dotenv
import tempfile
import sys
# --- Database initialization ---
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chatbot_data.db")
if not os.path.exists(DB_PATH):
    st.info("First run detected: Setting up database...")
    initialize_database()
    migrate_from_json()
    st.success("Database initialized successfully!")
# --- Imports pour Auth & Historique ---
from user_auth import display_login_ui, is_user_authenticated, get_current_username
from conversation_history import display_history_sidebar, save_current_conversation
from database_manager import load_user_conversations as load_user_history
# --- Nouveaux imports modulaires ---
from theme_manager import add_theme_selector
from pdf_processor import process_uploaded_pdf, get_raw_document_text
from prerequisite_handler import detect_prerequisites, explain_prerequisite
from rag_chain_creator import create_rag_chain

# --- Chargement des variables d'environnement AVANT tout appel à Streamlit ---
load_dotenv()

# Add a debug log function to track what's happening
def debug_log(message):
    """Print a debug message to console only"""
    print(f"DEBUG: {message}")

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
if "embedding_model" not in st.session_state:
    st.session_state.embedding_model = None
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
if "check_prereqs" not in st.session_state:  # CRITICAL NEW FLAG
    st.session_state.check_prereqs = True
    debug_log("Initializing check_prereqs to True")
# Initialize checkbox state tracking variable
if "prereq_checkbox_state" not in st.session_state:
    st.session_state.prereq_checkbox_state = True
    debug_log("Initializing prereq_checkbox_state to True")

# --- Utility Functions ---
@st.cache_resource
def load_embedding_model():
    debug_log("Loading embedding model...")
    from langchain_community.embeddings import SentenceTransformerEmbeddings
    return SentenceTransformerEmbeddings(model_name=EMBEDDING_MODEL_NAME)

@st.cache_resource
def load_llm():
    debug_log(f"Loading Google Gemini LLM: {LLM_MODEL_NAME}...")
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        llm = ChatGoogleGenerativeAI(model=LLM_MODEL_NAME, google_api_key=google_api_key,
                                     temperature=0.1, convert_system_message_to_human=True)
        debug_log("LLM Gemini loaded.")
        return llm
    except Exception as e: 
        st.error(f"Error loading Gemini model: {e}")
        debug_log(f"Error loading LLM: {e}")
        st.stop()

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
        
    # Load embedding model
    if st.session_state.embedding_model is None:
        st.session_state.embedding_model = load_embedding_model()

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
                debug_log(f"Processing: {uploaded_file.name}")
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_file_path = tmp_file.name
                
                st.write("Loading PDF...")
                progress_bar.progress(40)
                from langchain_community.document_loaders import PyPDFLoader
                loader = PyPDFLoader(tmp_file_path)
                documents = loader.load()
                
                if not documents:
                    st.warning("No text found in the document.")
                    os.unlink(tmp_file_path)
                    progress_bar.empty()
                else:
                    st.write("Splitting text...")
                    progress_bar.progress(60)
                    from langchain.text_splitter import RecursiveCharacterTextSplitter
                    text_splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=150)
                    texts = text_splitter.split_documents(documents)
                    
                    if not texts:
                        st.warning("No chunks created.")
                        os.unlink(tmp_file_path)
                        progress_bar.empty()
                    else:
                        st.write("Creating embeddings...")
                        progress_bar.progress(80)
                        
                        st.write("Building index...")
                        from langchain_community.vectorstores import Chroma
                        st.session_state.vector_store = Chroma.from_documents(texts, st.session_state.embedding_model)
                        progress_bar.progress(100)
                        
                        os.unlink(tmp_file_path)
                        debug_log("Temp file deleted.")
                        
                        st.session_state.processed_file_name = uploaded_file.name
                        st.session_state.rag_chain = create_rag_chain(st.session_state.vector_store, st.session_state.llm)
                        
                        greeting = f"Processed '{uploaded_file.name}'. Ask a question!"
                        st.session_state.messages = [{"role": "assistant", "content": greeting}]
                        st.session_state.current_conversation_id = None 
                        st.session_state.loaded_convo_id = None
                        st.session_state.prereq_history = set()
                        st.session_state.check_prereqs = True  # Reset prerequisite check flag
                        debug_log("Reset check_prereqs to True after file upload")
                        st.session_state.prereq_checkbox_state = True  # Reset checkbox state too
                        debug_log("Reset prereq_checkbox_state to True after file upload")
                        
                        save_current_conversation(st.session_state.username)
                        
                        st.success("Processing complete!")
                        st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
                debug_log(f"Error in PDF processing: {e}")
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
        if not rag_chain_instance: 
            debug_log("Error: RAG Chain not initialized")
            return "Error: RAG Chain not initialized.", []
            
        is_raw = any(p in user_query.lower() for p in ["exact text", "verbatim", "raw text"])
        debug_log(f"Getting RAG answer for: {user_query[:50]}...")
        
        with st.spinner("Searching..."):
            try:
                response = rag_chain_instance.invoke({"query": user_query})
                answer = response.get("result", "Not found.")
                source_docs = response.get("source_documents", [])
                debug_log(f"RAG answer length: {len(answer)} chars, {len(source_docs)} sources")
                
                if is_raw: 
                    debug_log("Raw document text requested")
                    answer = get_raw_document_text(source_docs)
                    
                return answer, source_docs
            except Exception as e: 
                debug_log(f"RAG Error: {e}")
                st.error("An error occurred.")
                return "Error processing your question.", []

    # --- Better way to handle Toggle Prerequisites for testing ---
    prereq_toggle_key = "toggle_prereqs_" + str(hash(st.session_state.username))
    prereq_enabled = st.sidebar.checkbox("Check for Prerequisites", 
                                        value=st.session_state.prereq_checkbox_state, 
                                        key=prereq_toggle_key)

    # Only update the state if it has changed
    if prereq_enabled != st.session_state.prereq_checkbox_state:
        debug_log(f"Prereq checkbox changed from {st.session_state.prereq_checkbox_state} to {prereq_enabled}")
        st.session_state.prereq_checkbox_state = prereq_enabled
        st.session_state.check_prereqs = prereq_enabled
        if prereq_enabled:
            st.success("Prerequisite checking enabled!")
        else:
            st.warning("Prerequisite checking disabled!")

    # Zone de saisie utilisateur - seulement si on a un RAG chain
    if st.session_state.rag_chain:
        if prompt := st.chat_input("Your question here...", key="chat_input"):
            debug_log(f"New user question: {prompt[:50]}...")
            
            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)

            active_rag_chain = st.session_state.rag_chain

            # --- COMPLETELY REWRITTEN prerequisite handling logic ---
            if st.session_state.waiting_for_prereq_response:
                debug_log("Processing response to prerequisite question")
                # User is responding to our prerequisite question
                prereq_topic = st.session_state.prerequisite_topic
                original_question = st.session_state.current_question
                
                debug_log(f"Prereq topic: {prereq_topic}")
                debug_log(f"Original question: {original_question[:50]}...")
                
                # Process their answer (yes/no to explanation)
                if any(word in prompt.lower() for word in ["yes", "y", "sure", "ok", "okay", "explain", "please"]):
                    debug_log("User wants prerequisite explanation")
                    # User wants the explanation
                    with st.spinner(f"Explaining {prereq_topic}..."):
                        prereq_explanation = explain_prerequisite(prereq_topic, st.session_state.llm)
                    
                    with st.spinner("Answering original question..."):
                        answer, _ = get_rag_answer(original_question, active_rag_chain)
                    
                    # Combine explanation with answer
                    response_content = f"{prereq_explanation}\n\n{answer}"
                else: 
                    debug_log("User skipped prerequisite explanation")
                    # User skipped the explanation
                    with st.spinner("Answering question..."):
                        answer, _ = get_rag_answer(original_question, active_rag_chain)
                    response_content = answer
                
                # Display the answer
                with st.chat_message("assistant"): 
                    st.markdown(response_content)
                
                # Add to message history
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": response_content
                })
                
                # Save conversation
                save_current_conversation(st.session_state.username)
                
                # RESET all prerequisite state variables
                debug_log("Resetting prerequisite state variables")
                st.session_state.waiting_for_prereq_response = False
                st.session_state.current_question = None
                st.session_state.prerequisite_topic = None
                # CRITICAL: Keep check_prereqs True for next questions
                st.session_state.check_prereqs = st.session_state.prereq_checkbox_state
                debug_log(f"check_prereqs set to {st.session_state.check_prereqs}")
                
            else:
                # This is a new question 
                debug_log("Processing new question")
                
                # Save the current question
                st.session_state.current_question = prompt
                debug_log(f"Current question set to: {prompt[:50]}...")
                
                # Log the current state of check_prereqs
                debug_log(f"check_prereqs is currently: {st.session_state.check_prereqs}")
                
                # Check for prerequisites ONLY if check_prereqs is True
                prereq_topic = None
                if st.session_state.check_prereqs:
                    debug_log("Checking for prerequisites...")
                    prereq_topic = detect_prerequisites(prompt, st.session_state.llm)
                    debug_log(f"Prerequisite detection result: {prereq_topic}")
                    
                    # Skip if we've already explained this prerequisite
                    if prereq_topic and prereq_topic in st.session_state.prereq_history:
                        debug_log(f"Prerequisite '{prereq_topic}' already explained, skipping")
                        prereq_topic = None
                else:
                    debug_log("Prerequisite checking disabled, skipping detection")
                
                if prereq_topic:
                    debug_log(f"Valid prerequisite found: {prereq_topic}")
                    # Found a valid prerequisite to explain
                    # Add to history so we don't ask again
                    st.session_state.prereq_history.add(prereq_topic)
                    debug_log(f"Added '{prereq_topic}' to prereq_history")
                    
                    # Set up for handling the response
                    st.session_state.prerequisite_topic = prereq_topic
                    st.session_state.waiting_for_prereq_response = True
                    debug_log("Set waiting_for_prereq_response to True")
                    
                    # Ask if they want an explanation
                    prereq_message = (
                        f"Before answering your question about {prompt[:30]}{'...' if len(prompt) > 30 else ''}, "
                        f"I think you should understand the concept of **{prereq_topic}** first. "
                        f"Would you like me to explain this concept? (yes/skip)"
                    )
                    
                    # Display question and save to history
                    with st.chat_message("assistant"): 
                        st.markdown(prereq_message)
                    
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": prereq_message
                    })
                    
                    save_current_conversation(st.session_state.username)
                else:
                    debug_log("No prerequisite needed or detected")
                    # No prerequisite needed - answer directly
                    with st.spinner("Searching for answer..."):
                        answer, _ = get_rag_answer(prompt, active_rag_chain)
                    
                    debug_log("Got direct answer, displaying")
                    # Display and save the direct answer
                    with st.chat_message("assistant"): 
                        st.markdown(answer)
                    
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": answer
                    })
                    
                    save_current_conversation(st.session_state.username)
                    
                    # Reset question state but PRESERVE check_prereqs flag
                    st.session_state.current_question = None
                    debug_log("Reset current_question to None")
    else:
        # Message d'information si aucun PDF n'est chargé
        if not st.session_state.processed_file_name and is_user_authenticated():
            st.info("Please upload a PDF document or select a conversation from history to begin chatting.")