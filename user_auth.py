"""
user_auth.py - Simplified and reliable authentication with proper persistence
"""
import os
import hashlib
import streamlit as st
from datetime import datetime, timedelta
from database_manager import authenticate_user, create_user

def create_auth_key(username):
    """Create a simple auth key for the user"""
    timestamp = datetime.now().strftime('%Y%m%d')
    return f"auth_{username}_{timestamp}"

def save_auth_state(username):
    """Save authentication state in a persistent way"""
    auth_key = create_auth_key(username)
    
    # Store in session state
    st.session_state.user_authenticated = True
    st.session_state.username = username
    st.session_state.auth_key = auth_key
    
    # Create a more reliable JavaScript-based persistence
    js_code = f"""
    <script>
    try {{
        // Store auth info in localStorage
        localStorage.setItem('chatbot_auth_user', '{username}');
        localStorage.setItem('chatbot_auth_key', '{auth_key}');
        localStorage.setItem('chatbot_auth_time', '{datetime.now().isoformat()}');
        
        // Save current conversation state if it exists
        const currentConvoId = "{st.session_state.get('current_conversation_id', '')}";
        const processedFile = "{st.session_state.get('processed_file_name', '')}";
        
        if (currentConvoId) {{
            localStorage.setItem('chatbot_current_convo', currentConvoId);
        }}
        if (processedFile) {{
            localStorage.setItem('chatbot_processed_file', processedFile);
        }}
        
        console.log('Auth data and state saved for user: {username}');
        
    }} catch (e) {{
        console.error('Error saving auth data:', e);
    }}
    </script>
    """
    
    st.markdown(js_code, unsafe_allow_html=True)

def check_auth_state():
    """Check if user is authenticated"""
    # First check current session state
    if st.session_state.get("user_authenticated", False) and st.session_state.get("username"):
        return True, st.session_state.username
    
    # Check if we have stored auth info and try to restore it
    restore_js = """
    <script>
    function restoreAuthState() {
        try {
            const storedUser = localStorage.getItem('chatbot_auth_user');
            const storedKey = localStorage.getItem('chatbot_auth_key');
            const storedTime = localStorage.getItem('chatbot_auth_time');
            
            if (storedUser && storedKey && storedTime) {
                console.log('Found stored auth data for user:', storedUser);
                
                // Check if auth is not too old (7 days)
                const authTime = new Date(storedTime);
                const now = new Date();
                const daysDiff = (now - authTime) / (1000 * 60 * 60 * 24);
                
                if (daysDiff < 7) {
                    console.log('Auth data is still valid, restoring session');
                    
                    // Set URL parameter to restore auth
                    const urlParams = new URLSearchParams(window.location.search);
                    if (!urlParams.has('restore_auth')) {
                        urlParams.set('restore_auth', storedUser);
                        urlParams.set('auth_key', storedKey);
                        
                        // Also restore conversation state if it exists
                        const currentConvo = localStorage.getItem('chatbot_current_convo');
                        const processedFile = localStorage.getItem('chatbot_processed_file');
                        
                        if (currentConvo) {
                            urlParams.set('restore_convo', currentConvo);
                        }
                        if (processedFile) {
                            urlParams.set('restore_file', processedFile);
                        }
                        
                        // Reload with auth parameters - NO REDIRECT, just update URL
                        const newUrl = window.location.pathname + '?' + urlParams.toString();
                        window.history.replaceState({}, document.title, newUrl);
                        
                        // Trigger Streamlit rerun instead of full page reload
                        window.location.reload();
                    }
                } else {
                    console.log('Auth data is too old, clearing');
                    localStorage.removeItem('chatbot_auth_user');
                    localStorage.removeItem('chatbot_auth_key');
                    localStorage.removeItem('chatbot_auth_time');
                    localStorage.removeItem('chatbot_current_convo');
                    localStorage.removeItem('chatbot_processed_file');
                }
            } else {
                console.log('No stored auth data found');
            }
        } catch (e) {
            console.error('Error restoring auth state:', e);
        }
    }
    
    // Only run once per page load
    if (!sessionStorage.getItem('auth_check_done')) {
        sessionStorage.setItem('auth_check_done', 'true');
        restoreAuthState();
    }
    </script>
    """
    
    st.markdown(restore_js, unsafe_allow_html=True)
    
    # Check URL parameters for auth restoration
    try:
        restore_user = st.query_params.get("restore_auth")
        restore_key = st.query_params.get("auth_key")
        restore_convo = st.query_params.get("restore_convo")
        restore_file = st.query_params.get("restore_file")
        
        if restore_user and restore_key:
            # Validate the auth key
            expected_key = create_auth_key(restore_user)
            if restore_key == expected_key:
                # Restore authentication
                st.session_state.user_authenticated = True
                st.session_state.username = restore_user
                st.session_state.auth_key = restore_key
                
                # Restore conversation state if provided
                if restore_convo:
                    st.session_state.current_conversation_id = restore_convo
                    st.session_state.loaded_convo_id = restore_convo
                    
                    # Load the conversation from database
                    try:
                        from database_manager import load_conversation
                        conversation = load_conversation(restore_user, restore_convo)
                        if conversation:
                            st.session_state.messages = conversation['messages']
                    except Exception as e:
                        print(f"Error loading conversation: {e}")
                
                if restore_file:
                    st.session_state.processed_file_name = restore_file
                
                # Clean up URL parameters
                clean_url_js = """
                <script>
                if (window.location.search.includes('restore_auth')) {
                    const url = new URL(window.location);
                    url.searchParams.delete('restore_auth');
                    url.searchParams.delete('auth_key');
                    url.searchParams.delete('restore_convo');
                    url.searchParams.delete('restore_file');
                    window.history.replaceState({}, document.title, url.pathname + url.search);
                }
                </script>
                """
                st.markdown(clean_url_js, unsafe_allow_html=True)
                
                return True, restore_user
                
    except Exception as e:
        print(f"Error checking auth restoration: {e}")
    
    return False, None

def clear_auth_state():
    """Clear authentication state completely"""
    # Clear session state
    keys_to_clear = [
        'user_authenticated', 'username', 'auth_key',
        'messages', 'current_conversation_id', 'loaded_convo_id',
        'vector_store', 'rag_chain', 'processed_file_name',
        'current_question', 'prerequisite_topic', 'waiting_for_prereq_response',
        'prereq_history', 'check_prereqs', 'prereq_checkbox_state',
        'generated_notes', 'show_notes_modal'
    ]
    
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    
    # Reset essential values
    st.session_state.user_authenticated = False
    st.session_state.username = ""
    st.session_state.messages = [{"role": "assistant", "content": "Hello! How can I help you today?"}]
    
    # Clear browser storage and reload
    clear_js = """
    <script>
    try {
        // Clear all auth-related localStorage items
        localStorage.removeItem('chatbot_auth_user');
        localStorage.removeItem('chatbot_auth_key');
        localStorage.removeItem('chatbot_auth_time');
        localStorage.removeItem('chatbot_current_convo');
        localStorage.removeItem('chatbot_processed_file');
        
        // Clear session storage
        sessionStorage.clear();
        
        console.log('Auth data cleared, reloading page');
        
        // Force reload to clean state
        setTimeout(function() {
            window.location.href = window.location.pathname;
        }, 100);
        
    } catch (e) {
        console.error('Error clearing auth data:', e);
        // Force reload anyway
        window.location.href = window.location.pathname;
    }
    </script>
    """
    
    st.markdown(clear_js, unsafe_allow_html=True)

def display_login_ui():
    """Display the login interface with reliable persistence"""
    # Always check authentication state first
    is_auth, username = check_auth_state()
    
    if is_auth and username:
        st.session_state.user_authenticated = True
        st.session_state.username = username
    
    # Display appropriate UI
    if st.session_state.get("user_authenticated", False):
        st.sidebar.success(f"Logged in as {st.session_state.username}")
        
        if st.sidebar.button("Logout", key="logout_button", help="Click to log out"):
            with st.sidebar:
                with st.spinner("Logging out..."):
                    clear_auth_state()
                    st.rerun()
    else:
        # Login/Signup interface
        with st.sidebar.expander("🔐 Login / Sign up", expanded=True):
            tab1, tab2 = st.tabs(["Login", "Sign up"])
            
            with tab1:
                login_username = st.text_input("Username", key="login_username")
                login_password = st.text_input("Password", type="password", key="login_password")
                
                if st.button("Login", key="login_submit"):
                    if login_username and login_password:
                        success, message = authenticate_user(login_username, login_password)
                        if success:
                            save_auth_state(login_username)
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
                    else:
                        st.warning("Please fill in all fields.")
            
            with tab2:
                signup_username = st.text_input("Username", key="signup_username")
                signup_email = st.text_input("Email", key="signup_email")
                signup_password = st.text_input("Password", type="password", key="signup_password")
                signup_password_confirm = st.text_input("Confirm password", type="password", key="signup_password_confirm")
                
                if st.button("Sign up", key="signup_submit"):
                    if signup_username and signup_email and signup_password:
                        if signup_password != signup_password_confirm:
                            st.error("Passwords do not match.")
                        else:
                            success, message = create_user(signup_username, signup_password, signup_email)
                            if success:
                                save_auth_state(signup_username)
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)
                    else:
                        st.warning("Please fill in all fields.")

def is_user_authenticated():
    """Check if user is authenticated"""
    is_auth, _ = check_auth_state()
    return is_auth or st.session_state.get("user_authenticated", False)

def get_current_username():
    """Get the username of the logged-in user"""
    is_auth, username = check_auth_state()
    if is_auth and username:
        return username
    return st.session_state.get("username", "")