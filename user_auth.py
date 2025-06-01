"""
user_auth.py - Enhanced authentication module with FIXED logout functionality
"""
import os
import hashlib
import hmac
import base64
import json
import streamlit as st
from datetime import datetime, timedelta
from database_manager import authenticate_user, create_user

# Secret key for session signing (should be in .env in production)
SESSION_SECRET = os.getenv("SESSION_SECRET", "your_development_secret_key")

# Session constants
SESSION_COOKIE_NAME = "auth_token"
SESSION_EXPIRY_DAYS = 14

def hash_password(password):
    """Hash the password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_session_token(username):
    """Create a robust session token for the user"""
    expiry = (datetime.now() + timedelta(days=SESSION_EXPIRY_DAYS)).timestamp()
    
    payload = {
        "username": username,
        "exp": expiry,
        "created": datetime.now().timestamp(),
        "random": os.urandom(8).hex()
    }
    
    payload_str = json.dumps(payload)
    payload_b64 = base64.urlsafe_b64encode(payload_str.encode()).decode()
    
    signature = hmac.new(
        SESSION_SECRET.encode(), 
        payload_b64.encode(), 
        hashlib.sha256
    ).hexdigest()
    
    token = f"{payload_b64}.{signature}"
    return token, expiry

def verify_session_token(token):
    """Verify a session token"""
    try:
        parts = token.split('.')
        if len(parts) != 2:
            return False, None
        
        payload_b64, signature = parts
        
        expected_sig = hmac.new(
            SESSION_SECRET.encode(),
            payload_b64.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if signature != expected_sig:
            return False, None
        
        payload_str = base64.urlsafe_b64decode(payload_b64.encode()).decode()
        payload = json.loads(payload_str)
        
        if datetime.now().timestamp() > payload.get('exp', 0):
            return False, None
        
        return True, payload.get('username')
    except Exception as e:
        print(f"Session verification error: {e}")
        return False, None

def set_auth_cookie(username):
    """Set authentication cookie for persistence"""
    token, expiry = create_session_token(username)
    
    # Store in session state
    st.session_state.auth_token = token
    st.session_state.stored_token = token
    
    expiry_str = datetime.fromtimestamp(expiry).strftime('%a, %d %b %Y %H:%M:%S GMT')
    
    js = f"""
    <script>
    try {{
        localStorage.setItem('{SESSION_COOKIE_NAME}', '{token}');
        document.cookie = "{SESSION_COOKIE_NAME}={token};path=/;expires={expiry_str};SameSite=Lax";
        console.log("Authentication data saved successfully");
    }} catch (e) {{
        console.error("Error saving auth data:", e);
    }}
    </script>
    """
    
    st.markdown(js, unsafe_allow_html=True)
    return token

def clear_auth_cookie():
    """Clear authentication cookie on logout - SIMPLIFIED VERSION"""
    # Clear session state first
    session_keys_to_clear = [
        'auth_token', 'stored_token', 'user_authenticated', 'username',
        'messages', 'current_conversation_id', 'loaded_convo_id',
        'vector_store', 'rag_chain', 'processed_file_name',
        'current_question', 'prerequisite_topic', 'waiting_for_prereq_response',
        'prereq_history', 'check_prereqs', 'prereq_checkbox_state'
    ]
    
    for key in session_keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    
    # Reset essential session state values
    st.session_state.user_authenticated = False
    st.session_state.username = ""
    st.session_state.messages = [{"role": "assistant", "content": "Hello! How can I help you today?"}]
    
    # Clear browser storage
    js = """
    <script>
    try {
        localStorage.removeItem('auth_token');
        document.cookie = "auth_token=;path=/;expires=Thu, 01 Jan 1970 00:00:00 GMT";
        sessionStorage.clear();
        console.log("Auth data cleared successfully");
        
        // Force reload to completely reset the app state
        setTimeout(function() {
            window.location.href = window.location.pathname;
        }, 100);
    } catch (e) {
        console.error("Error clearing auth data:", e);
        // Fallback: force reload anyway
        window.location.href = window.location.pathname;
    }
    </script>
    """
    
    st.markdown(js, unsafe_allow_html=True)

def check_token_in_url_or_storage():
    """Try to find auth token from multiple sources"""
    token = None
    
    # Try from query parameters first
    try:
        param_token = st.query_params.get("auth_token")
        if param_token:
            return param_token
    except Exception as e:
        print(f"Error getting token from query params: {e}")
    
    # Try from session state
    if "stored_token" in st.session_state and st.session_state.stored_token:
        return st.session_state.stored_token
    
    # Check storage with JavaScript
    check_storage_js = f"""
    <script>
    function findAndApplyAuthToken() {{
        const localToken = localStorage.getItem('{SESSION_COOKIE_NAME}');
        if (localToken && !window.location.search.includes('auth_token')) {{
            const separator = window.location.search ? '&' : '?';
            const newUrl = window.location.pathname + 
                          window.location.search + 
                          separator + 
                          'auth_token=' + localToken;
            window.history.replaceState(null, document.title, newUrl);
            
            // If URL update didn't work, force reload
            if (!window.location.search.includes('auth_token')) {{
                window.location.href = newUrl;
            }}
        }}
    }}
    
    if (document.readyState === 'complete') {{
        findAndApplyAuthToken();
    }} else {{
        window.addEventListener('load', findAndApplyAuthToken);
    }}
    </script>
    """
    
    if "stored_token" not in st.session_state:
        st.session_state.stored_token = None
    
    st.markdown(check_storage_js, unsafe_allow_html=True)
    return st.session_state.stored_token

def check_authentication():
    """Check if user is authenticated via multiple methods"""
    # First check session state (for current session)
    if st.session_state.get("user_authenticated", False) and st.session_state.get("username", ""):
        return True, st.session_state.username
    
    # Try to get token from session state first
    token = st.session_state.get("auth_token")
    
    # Also check stored_token from JS communication
    if not token and "stored_token" in st.session_state:
        token = st.session_state.stored_token
    
    # If not in session state, check URL and storage
    if not token:
        token = check_token_in_url_or_storage()
    
    # If we found a token, validate it
    if token:
        is_valid, username = verify_session_token(token)
        if is_valid and username:
            # Update session state
            st.session_state.user_authenticated = True
            st.session_state.username = username
            st.session_state.auth_token = token
            st.session_state.stored_token = token
            
            # Refresh the token to extend expiry
            set_auth_cookie(username)
            
            return True, username
    
    return False, None

def display_login_ui():
    """Display the login interface with FIXED logout functionality"""
    # Check authentication first
    is_auth, username = check_authentication()
    if is_auth and username:
        st.session_state.user_authenticated = True
        st.session_state.username = username
    
    # Display UI based on authentication status
    if st.session_state.get("user_authenticated", False):
        st.sidebar.success(f"Logged in as {st.session_state.username}")
        
        # FIXED LOGOUT BUTTON with better handling
        if st.sidebar.button("Logout", key="logout_button", help="Click to log out"):
            # Show a brief message
            with st.sidebar:
                with st.spinner("Logging out..."):
                    # Clear authentication data
                    clear_auth_cookie()
                    
                    # Force rerun after clearing data
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
                            st.session_state.user_authenticated = True
                            st.session_state.username = login_username
                            set_auth_cookie(login_username)
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
                                st.success(message)
                                st.session_state.user_authenticated = True
                                st.session_state.username = signup_username
                                set_auth_cookie(signup_username)
                                st.rerun()
                            else:
                                st.error(message)
                    else:
                        st.warning("Please fill in all fields.")

def is_user_authenticated():
    """Check if user is authenticated"""
    is_auth, _ = check_authentication()
    if is_auth:
        return True
    return st.session_state.get("user_authenticated", False)

def get_current_username():
    """Get the username of the logged-in user"""
    is_auth, username = check_authentication()
    if is_auth and username:
        return username
    return st.session_state.get("username", "")