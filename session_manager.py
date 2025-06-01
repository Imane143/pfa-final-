"""
session_manager.py - Centralized session state management
"""
import streamlit as st

def debug_log(message):
    """Print a debug message to console only"""
    print(f"DEBUG: {message}")

def initialize_session_state():
    """Initialize all session state variables"""
    # Authentication states
    if "user_authenticated" not in st.session_state: 
        st.session_state.user_authenticated = False
    if "username" not in st.session_state: 
        st.session_state.username = ""
    
    # Chat and conversation states
    if "messages" not in st.session_state: 
        st.session_state.messages = [{"role": "assistant", "content": "Hello! How can I help you today?"}]
    if "current_conversation_id" not in st.session_state: 
        st.session_state.current_conversation_id = None
    if "loaded_convo_id" not in st.session_state:
        st.session_state.loaded_convo_id = None
    
    # RAG and AI states
    if "vector_store" not in st.session_state: 
        st.session_state.vector_store = None 
    if "rag_chain" not in st.session_state: 
        st.session_state.rag_chain = None 
    if "llm" not in st.session_state:
        st.session_state.llm = None
    if "embedding_model" not in st.session_state:
        st.session_state.embedding_model = None
    
    # File processing states
    if "processed_file_name" not in st.session_state: 
        st.session_state.processed_file_name = None 
    
    # Prerequisite handling states
    if "current_question" not in st.session_state: 
        st.session_state.current_question = None
    if "prerequisite_topic" not in st.session_state: 
        st.session_state.prerequisite_topic = None
    if "waiting_for_prereq_response" not in st.session_state: 
        st.session_state.waiting_for_prereq_response = False
    if "prereq_history" not in st.session_state: 
        st.session_state.prereq_history = set()
    if "check_prereqs" not in st.session_state:
        st.session_state.check_prereqs = True
        debug_log("Initializing check_prereqs to True")
    if "prereq_checkbox_state" not in st.session_state:
        st.session_state.prereq_checkbox_state = True
        debug_log("Initializing prereq_checkbox_state to True")
    
    # Study notes states
    if 'generated_notes' not in st.session_state:
        st.session_state.generated_notes = None
    if 'show_notes_modal' not in st.session_state:
        st.session_state.show_notes_modal = False
    
    # Rename conversation states
    if 'show_rename_modal' not in st.session_state:
        st.session_state.show_rename_modal = False
    if 'rename_conversation_id' not in st.session_state:
        st.session_state.rename_conversation_id = None
    if 'rename_current_title' not in st.session_state:
        st.session_state.rename_current_title = None

def reset_conversation_state():
    """Reset conversation-related session states"""
    st.session_state.messages = [{"role": "assistant", "content": "Hello! How can I help you today?"}]
    st.session_state.current_conversation_id = None 
    st.session_state.loaded_convo_id = None
    st.session_state.prereq_history = set()
    st.session_state.check_prereqs = True
    st.session_state.prereq_checkbox_state = True
    debug_log("Reset conversation state")

def reset_file_processing_state():
    """Reset file processing related states"""
    st.session_state.vector_store = None
    st.session_state.rag_chain = None
    st.session_state.processed_file_name = None
    debug_log("Reset file processing state")