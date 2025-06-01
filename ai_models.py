"""
ai_models.py - AI model loading and initialization
"""
import streamlit as st
from session_manager import debug_log

EMBEDDING_MODEL_NAME = "paraphrase-MiniLM-L3-v2" 
LLM_MODEL_NAME = "gemini-1.5-flash"

@st.cache_resource
def load_embedding_model():
    """Load the embedding model"""
    debug_log("Loading embedding model...")
    from langchain_community.embeddings import SentenceTransformerEmbeddings
    return SentenceTransformerEmbeddings(model_name=EMBEDDING_MODEL_NAME)

@st.cache_resource
def load_llm(google_api_key):
    """Load the Google Gemini LLM"""
    debug_log(f"Loading Google Gemini LLM: {LLM_MODEL_NAME}...")
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        llm = ChatGoogleGenerativeAI(
            model=LLM_MODEL_NAME, 
            google_api_key=google_api_key,
            temperature=0.1, 
            convert_system_message_to_human=True
        )
        debug_log("LLM Gemini loaded.")
        return llm
    except Exception as e: 
        st.error(f"Error loading Gemini model: {e}")
        debug_log(f"Error loading LLM: {e}")
        st.stop()

def initialize_ai_models(google_api_key):
    """Initialize AI models if not already loaded"""
    # Load LLM once per authenticated session
    if st.session_state.llm is None:
        st.session_state.llm = load_llm(google_api_key)
        
    # Load embedding model
    if st.session_state.embedding_model is None:
        st.session_state.embedding_model = load_embedding_model()