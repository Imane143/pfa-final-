"""
conversation_rename.py - Handle conversation renaming functionality
"""
import streamlit as st
from database_manager import save_conversation

def display_rename_modal():
    """Display rename modal if requested"""
    if st.session_state.get('show_rename_modal', False):
        # Get current conversation details
        conversation_id = st.session_state.get('rename_conversation_id')
        current_title = st.session_state.get('rename_current_title', '')
        
        # Create modal-like container
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.subheader("✏️ Rename Conversation")
            
            # Text input for new title
            new_title = st.text_input(
                "Enter new title:",
                value=current_title,
                key="rename_input",
                max_chars=100
            )
            
            # Buttons
            col_save, col_cancel = st.columns(2)
            
            with col_save:
                if st.button("💾 Save", key="save_rename", type="primary"):
                    if new_title.strip():
                        # Update the conversation title
                        success = rename_conversation(
                            st.session_state.username,
                            conversation_id,
                            new_title.strip()
                        )
                        
                        if success:
                            st.success("✅ Conversation renamed successfully!")
                            # Close modal
                            st.session_state.show_rename_modal = False
                            st.session_state.rename_conversation_id = None
                            st.session_state.rename_current_title = None
                            st.rerun()
                        else:
                            st.error("❌ Failed to rename conversation.")
                    else:
                        st.warning("⚠️ Please enter a valid title.")
            
            with col_cancel:
                if st.button("❌ Cancel", key="cancel_rename"):
                    # Close modal without saving
                    st.session_state.show_rename_modal = False
                    st.session_state.rename_conversation_id = None
                    st.session_state.rename_current_title = None
                    st.rerun()
        
        st.markdown("---")

def rename_conversation(username, conversation_id, new_title):
    """Rename a conversation in the database"""
    try:
        from database_manager import load_conversation
        
        # Load the conversation
        conversation = load_conversation(username, conversation_id)
        if not conversation:
            return False
        
        # Save with new title
        result = save_conversation(
            username=username,
            conversation_id=conversation_id,
            title=new_title,
            messages=conversation['messages'],
            document_name=conversation.get('document', '')
        )
        
        return result is not None
        
    except Exception as e:
        print(f"Error renaming conversation: {e}")
        return False

def trigger_rename(conversation_id, current_title):
    """Trigger the rename modal for a specific conversation"""
    st.session_state.show_rename_modal = True
    st.session_state.rename_conversation_id = conversation_id
    st.session_state.rename_current_title = current_title

def init_rename_session_state():
    """Initialize rename-related session state"""
    if 'show_rename_modal' not in st.session_state:
        st.session_state.show_rename_modal = False
    if 'rename_conversation_id' not in st.session_state:
        st.session_state.rename_conversation_id = None
    if 'rename_current_title' not in st.session_state:
        st.session_state.rename_current_title = None