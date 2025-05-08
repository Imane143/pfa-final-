import os
import json
import streamlit as st
from datetime import datetime

# Path to conversation histories folder - CORRECTION
HISTORY_FOLDER = os.path.join(os.path.expanduser("~"), "Documents", "educational_chatbot_histories")

def initialize_history_folder():
    """Create the histories folder if it doesn't exist"""
    if not os.path.exists(HISTORY_FOLDER):
        os.makedirs(HISTORY_FOLDER)

def get_user_history_path(username):
    """Get the path to the user's history file"""
    initialize_history_folder()
    return os.path.join(HISTORY_FOLDER, f"{username}_history.json")

def load_user_history(username):
    """Load a user's conversation history"""
    file_path = get_user_history_path(username)
    
    if not os.path.exists(file_path):
        return {}
    
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except json.JSONDecodeError:
        # If file is corrupted, reset it
        return {}

def save_conversation(username, conversation_id, title, messages):
    """Save a conversation to the user's history"""
    if not username:
        return None
        
    history = load_user_history(username)
    
    # If it's a new conversation, create a new ID
    if not conversation_id:
        conversation_id = datetime.now().strftime("%Y%m%d%H%M%S")
    
    # Generate a title if none is provided
    if not title and messages:
        # Use the beginning of the first user question as the title
        for msg in messages:
            if msg['role'] == 'user':
                title = msg['content'][:30] + '...' if len(msg['content']) > 30 else msg['content']
                break
        if not title:
            title = f"Conversation {conversation_id}"
    
    # Update the history
    history[conversation_id] = {
        'title': title,
        'last_updated': datetime.now().isoformat(),
        'messages': messages,
        'document': st.session_state.get('processed_file_name', '')
    }
    
    # Save to file
    with open(get_user_history_path(username), 'w') as file:
        json.dump(history, file)
    
    return conversation_id

def delete_conversation(username, conversation_id):
    """Delete a conversation from the history"""
    history = load_user_history(username)
    
    if conversation_id in history:
        del history[conversation_id]
        
        with open(get_user_history_path(username), 'w') as file:
            json.dump(history, file)
        
        return True
    
    return False

def display_history_sidebar(username):
    """Display the conversation history sidebar"""
    if not username:
        return None
    
    history = load_user_history(username)
    
    if not history:
        st.sidebar.info("No saved conversations.")
        return None

    # Initialize session state for current chat
    if 'current_conversation_id' not in st.session_state:
        st.session_state.current_conversation_id = None
    
    # Display the conversation list
    st.sidebar.subheader("Conversation History")
    
    # New conversation button
    if st.sidebar.button("➕ New Conversation"):
        st.session_state.messages = [{"role": "assistant", "content": "Hello! How can I help you today?"}]
        st.session_state.current_conversation_id = None
        st.session_state.loaded_convo_id = None  # IMPORTANT: Reset loaded convo ID
        st.rerun()
    
    # List of conversations
    for conv_id, conv_data in sorted(history.items(), key=lambda x: x[1]['last_updated'], reverse=True):
        title = conv_data['title']
        document = conv_data.get('document', '')
        date = datetime.fromisoformat(conv_data['last_updated']).strftime("%d/%m/%Y")
        
        # Display a label for the associated document
        doc_label = f" 📄 {document}" if document else ""
        
        # Create columns for the button and delete button
        col1, col2 = st.sidebar.columns([5, 1])
        
        # Display the conversation button
        if col1.button(f"{title}{doc_label}\n{date}", key=f"hist_{conv_id}"):
            st.session_state.messages = conv_data['messages']
            st.session_state.current_conversation_id = conv_id
            st.session_state.loaded_convo_id = conv_id  # IMPORTANT: Set loaded convo ID
            
            # If the conversation is associated with a document different from the current one
            if document and document != st.session_state.get('processed_file_name', ''):
                st.info(f"This conversation is associated with the document '{document}' which is not currently loaded.")
            
            st.rerun()
        
        # Delete button
        if col2.button("🗑️", key=f"del_{conv_id}"):
            if delete_conversation(username, conv_id):
                if st.session_state.current_conversation_id == conv_id:
                    st.session_state.current_conversation_id = None
                    st.session_state.loaded_convo_id = None  # IMPORTANT: Reset loaded convo ID
                    st.session_state.messages = [{"role": "assistant", "content": "Hello! How can I help you today?"}]
                st.rerun()
    
    return st.session_state.current_conversation_id

def save_current_conversation(username):
    """Save the current conversation"""
    if not username or not st.session_state.get('messages'):
        return
    
    conversation_id = st.session_state.get('current_conversation_id')
    title = None  # Let the save_conversation function generate a title
    
    new_id = save_conversation(username, conversation_id, title, st.session_state.messages)
    
    if not conversation_id:
        st.session_state.current_conversation_id = new_id
        st.session_state.loaded_convo_id = new_id  # IMPORTANT: Update loaded convo ID