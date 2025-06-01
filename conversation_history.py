"""
conversation_history.py - Module to manage conversation histories using SQLite database
"""
import streamlit as st
from database_manager import save_conversation, load_user_conversations, load_conversation, delete_conversation

def display_history_sidebar(username):
    """Display the conversation history sidebar"""
    if not username:
        return None
    
    history = load_user_conversations(username)
    
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
        # Convert ISO format date to display format
        try:
            from datetime import datetime
            date_obj = datetime.fromisoformat(conv_data['last_updated'])
            date = date_obj.strftime("%d/%m/%Y")
        except:
            date = conv_data['last_updated'][:10]  # Fallback
        
        # Display a label for the associated document
        doc_label = f" 📄 {document}" if document else ""
        
        # Create columns for the buttons: load, rename, delete
        col1, col2, col3 = st.sidebar.columns([4, 1, 1])
        
        # Display the conversation button
        if col1.button(f"{title}{doc_label}\n{date}", key=f"hist_{conv_id}"):
            st.session_state.messages = conv_data['messages']
            st.session_state.current_conversation_id = conv_id
            st.session_state.loaded_convo_id = conv_id  # IMPORTANT: Set loaded convo ID
            
            # If the conversation is associated with a document different from the current one
            if document and document != st.session_state.get('processed_file_name', ''):
                st.info(f"This conversation is associated with the document '{document}' which is not currently loaded.")
            
            st.rerun()
        
        # Rename button
        if col2.button("✏️", key=f"rename_{conv_id}", help="Rename conversation"):
            from conversation_rename import trigger_rename
            trigger_rename(conv_id, title)
            st.rerun()
        
        # Delete button
        if col3.button("🗑️", key=f"del_{conv_id}", help="Delete conversation"):
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
    document_name = st.session_state.get('processed_file_name', '')
    
    new_id = save_conversation(
        username=username, 
        conversation_id=conversation_id, 
        title=title, 
        messages=st.session_state.messages,
        document_name=document_name
    )
    
    if not conversation_id:
        st.session_state.current_conversation_id = new_id
        st.session_state.loaded_convo_id = new_id  # IMPORTANT: Update loaded convo ID