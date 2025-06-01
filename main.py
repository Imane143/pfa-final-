"""
main.py - Educational Chatbot with Modular Architecture
Simplified and organized into logical modules
"""
import os
import streamlit as st
from dotenv import load_dotenv

# Database initialization (only once per session)
from database_manager import initialize_database, migrate_from_json

# Check if database exists, initialize if needed
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chatbot_data.db")
if not os.path.exists(DB_PATH):
    if 'database_initialized' not in st.session_state:
        st.info("First run detected: Setting up database...")
        initialize_database()
        migrate_from_json()
        st.session_state.database_initialized = True
        st.success("Database initialized successfully!")

# Load environment variables
load_dotenv()

# Import all modules
from session_manager import initialize_session_state, debug_log
from ai_models import initialize_ai_models
from user_auth import display_login_ui, is_user_authenticated, get_current_username
from conversation_history import display_history_sidebar, save_current_conversation
from conversation_rename import display_rename_modal
from theme_manager import add_theme_selector
from file_upload_handler import display_file_upload_section
from chat_handler import (
    display_chat_messages, 
    display_prerequisite_toggle, 
    handle_chat_input, 
    display_context_caption
)
from study_notes_generator import display_study_notes_generator, display_notes_modal

# Page configuration (must be first Streamlit command)
st.set_page_config(page_title="AI Educational Chatbot", page_icon="🎓", layout="wide")

# Add theme selector
add_theme_selector()

# Check for required API key
google_api_key = os.getenv("GOOGLE_API_KEY")
if not google_api_key:
    st.error("Google API Key (Gemini) not found. Make sure it's in the .env file as GOOGLE_API_KEY")
    st.stop()

# Initialize session state
initialize_session_state()

# Main app title
st.title("🎓 AI Educational Chatbot")

# Sidebar
with st.sidebar:
    st.header("User Account")
    display_login_ui()
    
    st.divider()
    
    # Show features only if authenticated
    if is_user_authenticated():
        st.header("Conversation History")
        display_history_sidebar(get_current_username())
        
        st.divider()
        st.header("Study Tools")
        display_study_notes_generator()
        
        st.divider()
        st.header("Settings")
        display_prerequisite_toggle()
    else:
        st.header("Conversation History")
        st.info("Log in to see conversation history.")

# Main interface (only show if authenticated)
if not is_user_authenticated():
    st.warning("Please log in or sign up using the sidebar to use the chatbot.")
else:
    # Welcome message
    st.success(f"Welcome {st.session_state.username}!") 

    # Initialize AI models once user is authenticated
    initialize_ai_models(google_api_key)

    # File upload section
    uploaded_file = display_file_upload_section()

    # Display context caption
    display_context_caption()

    # Chat interface
    display_chat_messages()

    # Always show chat input area, but handle the logic inside
    handle_chat_input()

    # Display study notes modal if requested
    display_notes_modal()

    # Display rename modal if requested
    display_rename_modal()

# Debug information (only in development)
if os.getenv("DEBUG") == "true":
    with st.sidebar.expander("Debug Info", expanded=False):
        st.write("Session State Keys:", list(st.session_state.keys()))
        st.write("Authenticated:", is_user_authenticated())
        st.write("Username:", get_current_username())
        st.write("RAG Chain:", bool(st.session_state.rag_chain))
        st.write("Vector Store:", bool(st.session_state.vector_store))
        st.write("Processed File:", st.session_state.processed_file_name)