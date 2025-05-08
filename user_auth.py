"""
user_auth.py - Enhanced authentication module with better session persistence
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
# Generate a random secret key when deploying to production
SESSION_SECRET = os.getenv("SESSION_SECRET", "your_development_secret_key")

# Session constants
SESSION_COOKIE_NAME = "auth_token"
SESSION_EXPIRY_DAYS = 14  # Longer expiry for better user experience

def hash_password(password):
    """Hash the password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_session_token(username):
    """Create a robust session token for the user"""
    # Current timestamp + expiry days
    expiry = (datetime.now() + timedelta(days=SESSION_EXPIRY_DAYS)).timestamp()
    
    # Create a payload with more info for better security
    payload = {
        "username": username,
        "exp": expiry,
        "created": datetime.now().timestamp(),
        "random": os.urandom(8).hex()  # Add randomness to prevent token reuse
    }
    
    # Convert payload to string
    payload_str = json.dumps(payload)
    payload_b64 = base64.urlsafe_b64encode(payload_str.encode()).decode()
    
    # Sign the payload
    signature = hmac.new(
        SESSION_SECRET.encode(), 
        payload_b64.encode(), 
        hashlib.sha256
    ).hexdigest()
    
    # Combine payload and signature in a JWT-like format
    token = f"{payload_b64}.{signature}"
    
    return token, expiry

def verify_session_token(token):
    """Verify a session token"""
    try:
        # Split token into parts
        parts = token.split('.')
        if len(parts) != 2:
            return False, None
        
        payload_b64, signature = parts
        
        # Verify signature
        expected_sig = hmac.new(
            SESSION_SECRET.encode(),
            payload_b64.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if signature != expected_sig:
            return False, None
        
        # Decode payload
        payload_str = base64.urlsafe_b64decode(payload_b64.encode()).decode()
        payload = json.loads(payload_str)
        
        # Check expiration
        if datetime.now().timestamp() > payload.get('exp', 0):
            return False, None
        
        return True, payload.get('username')
    except Exception as e:
        print(f"Session verification error: {e}")
        return False, None

def set_auth_cookie(username):
    """Set authentication cookie for persistence using multiple approaches"""
    token, expiry = create_session_token(username)
    
    # Store in session state
    st.session_state.auth_token = token
    
    # Format expiry for cookie
    expiry_str = datetime.fromtimestamp(expiry).strftime('%a, %d %b %Y %H:%M:%S GMT')
    
    # Use multiple methods for more reliable persistence
    js = f"""
    <script>
    // Store in both localStorage and cookies for redundancy
    try {{
        // Primary method: localStorage (most reliable for Streamlit)
        localStorage.setItem('{SESSION_COOKIE_NAME}', '{token}');
        
        // Backup method: cookies
        document.cookie = "{SESSION_COOKIE_NAME}={token};path=/;expires={expiry_str};SameSite=Lax";
        
        // Add token to URL once (as fragment) for immediate use
        // This helps with page refreshes without changing the URL each time
        if (!window.location.hash.includes('auth_token')) {{
            // Store temporarily in hash (not sent to server)
            const currentHash = window.location.hash || '';
            const newHash = currentHash + (currentHash ? '&' : '#') + 'auth_token={token}';
            window.history.replaceState(null, document.title, newHash);
            console.log("Auth token added to URL hash");
        }}
        
        // Set a flag to check auth on page load
        sessionStorage.setItem('check_auth_on_load', 'true');
        
        console.log("Authentication data saved successfully");
    }} catch (e) {{
        console.error("Error saving auth data:", e);
    }}
    
    // Helper function that will be available on page load
    function checkAuthOnLoad() {{
        // This runs on every page load to check for stored auth data
        const storedToken = localStorage.getItem('{SESSION_COOKIE_NAME}');
        if (storedToken && !window.location.search.includes('auth_token')) {{
            // Add as URL parameter to allow server to detect it
            // Only do this if not already present in URL
            const separator = window.location.search ? '&' : '?';
            window.location.href = window.location.pathname + 
                                   window.location.search + 
                                   separator + 
                                   'auth_token=' + storedToken;
        }}
    }}
    
    // Add a small delay to run only after page is fully loaded
    if (sessionStorage.getItem('check_auth_on_load') === 'true') {{
        setTimeout(checkAuthOnLoad, 100);
    }}
    </script>
    """
    
    st.markdown(js, unsafe_allow_html=True)
    return token

def clear_auth_cookie():
    """Clear authentication cookie on logout"""
    if 'auth_token' in st.session_state:
        del st.session_state.auth_token
    
    js = """
    <script>
    // Clear all stored authentication data
    try {
        // Remove from localStorage
        localStorage.removeItem('auth_token');
        
        // Remove from cookies
        document.cookie = "auth_token=;path=/;expires=Thu, 01 Jan 1970 00:00:00 GMT";
        
        // Remove from URL if present
        if (window.location.search.includes('auth_token')) {
            const newUrl = window.location.href.replace(/[?&]auth_token=[^&#]*/g, '');
            window.history.replaceState(null, document.title, newUrl);
        }
        
        // Remove from URL hash if present
        if (window.location.hash.includes('auth_token')) {
            const newHash = window.location.hash.replace(/[#&]auth_token=[^&]*/g, '');
            window.history.replaceState(null, document.title, window.location.pathname + window.location.search + newHash);
        }
        
        // Remove check flag
        sessionStorage.removeItem('check_auth_on_load');
        
        console.log("Auth data cleared successfully");
    } catch (e) {
        console.error("Error clearing auth data:", e);
    }
    </script>
    """
    
    st.markdown(js, unsafe_allow_html=True)

def check_token_in_url_or_storage():
    """
    Try to find auth token from multiple sources: 
    URL params, hash fragment, localStorage
    """
    token = None
    
    # Try from query parameters
    try:
        token = st.query_params.get("auth_token", [None])[0]
        if token:
            print("Found token in URL query params")
            return token
    except Exception as e:
        print(f"Error getting token from query params: {e}")
    
    # Add JavaScript to check localStorage and cookies
    # This will set a token in the URL if found in localStorage
    check_storage_js = """
    <script>
    function checkAuthStorage() {
        try {
            // Check localStorage first (most reliable in Streamlit)
            const storedToken = localStorage.getItem('auth_token');
            if (storedToken && !window.location.search.includes('auth_token')) {
                // Add token to URL to let server detect it
                console.log("Found token in localStorage, adding to URL");
                const separator = window.location.search ? '&' : '?';
                window.location.href = window.location.pathname + 
                                       window.location.search + 
                                       separator + 
                                       'auth_token=' + storedToken;
                return true;
            }
            
            // Check URL hash as fallback
            if (window.location.hash.includes('auth_token')) {
                // Extract token from hash
                const hashParams = new URLSearchParams(window.location.hash.substring(1));
                const hashToken = hashParams.get('auth_token');
                if (hashToken && !window.location.search.includes('auth_token')) {
                    console.log("Found token in URL hash, adding to URL params");
                    const separator = window.location.search ? '&' : '?';
                    window.location.href = window.location.pathname + 
                                           window.location.search + 
                                           separator + 
                                           'auth_token=' + hashToken;
                    return true;
                }
            }
            
            // Last resort - try to get from cookies
            const cookies = document.cookie.split(';');
            for (const cookie of cookies) {
                const [name, value] = cookie.trim().split('=');
                if (name === 'auth_token' && value && !window.location.search.includes('auth_token')) {
                    console.log("Found token in cookies, adding to URL");
                    const separator = window.location.search ? '&' : '?';
                    window.location.href = window.location.pathname + 
                                           window.location.search + 
                                           separator + 
                                           'auth_token=' + value;
                    return true;
                }
            }
        } catch (e) {
            console.error("Error in checkAuthStorage:", e);
        }
        return false;
    }
    
    // Run the check if no auth_token in URL already
    if (!window.location.search.includes('auth_token')) {
        setTimeout(checkAuthStorage, 50);
    }
    </script>
    """
    
    st.markdown(check_storage_js, unsafe_allow_html=True)
    
    # Token isn't available yet but might be after page refresh
    return token

def check_authentication():
    """Check if user is authenticated via multiple methods"""
    # First check session state (for current session)
    if st.session_state.get("user_authenticated", False) and st.session_state.get("username", ""):
        # Already authenticated in this session
        return True, st.session_state.username
    
    # Try to get token from session state first (current session)
    token = st.session_state.get("auth_token")
    
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
            
            # Refresh the token to extend expiry
            set_auth_cookie(username)
            
            return True, username
    
    return False, None

def display_login_ui():
    """Display the login interface with enhanced persistence"""
    # Check authentication first
    is_auth, username = check_authentication()
    if is_auth and username:
        st.session_state.user_authenticated = True
        st.session_state.username = username
    
    # Add a script to ensure localStorage persistence works on first load
    st.markdown("""
    <script>
    // Helper function to check if this is a brand new session
    function checkFirstTimeLoad() {
        if (sessionStorage.getItem('app_loaded') !== 'true') {
            sessionStorage.setItem('app_loaded', 'true');
            
            // This is the first load in this tab session
            // Check if we have auth data in localStorage
            const storedToken = localStorage.getItem('auth_token');
            if (storedToken && !window.location.search.includes('auth_token')) {
                console.log("First time load: Auth token found in storage");
                const separator = window.location.search ? '&' : '?';
                window.location.href = window.location.pathname + 
                                       window.location.search + 
                                       separator + 
                                       'auth_token=' + storedToken;
            }
        }
    }
    
    // Run this check on initial page load
    checkFirstTimeLoad();
    </script>
    """, unsafe_allow_html=True)
    
    # Continue with normal login UI
    if st.session_state.get("user_authenticated", False):
        st.sidebar.success(f"Logged in as {st.session_state.username}")
        if st.sidebar.button("Logout"):
            # Clear the authentication data
            clear_auth_cookie()
            
            st.session_state.user_authenticated = False
            st.session_state.username = ""
            # Reset other user-related session states
            if 'messages' in st.session_state:
                st.session_state.messages = [{"role": "assistant", "content": "Hello! How can I help you today?"}]
            if 'current_conversation_id' in st.session_state:
                st.session_state.current_conversation_id = None
            if 'loaded_convo_id' in st.session_state:
                st.session_state.loaded_convo_id = None
            
            # Force a full page reload after logout for clean state
            st.markdown("""
            <script>
                window.location.href = window.location.pathname;
            </script>
            """, unsafe_allow_html=True)
            
            st.rerun()
    else:
        with st.sidebar.expander("🔐 Login / Sign up", expanded=not st.session_state.get("user_authenticated", False)):
            tab1, tab2 = st.tabs(["Login", "Sign up"])
            
            with tab1:
                login_username = st.text_input("Username", key="login_username")
                login_password = st.text_input("Password", type="password", key="login_password")
                
                if st.button("Login"):
                    if login_username and login_password:
                        success, message = authenticate_user(login_username, login_password)
                        if success:
                            st.session_state.user_authenticated = True
                            st.session_state.username = login_username
                            # Set auth cookie for persistence
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
                
                if st.button("Sign up"):
                    if signup_username and signup_email and signup_password:
                        if signup_password != signup_password_confirm:
                            st.error("Passwords do not match.")
                        else:
                            success, message = create_user(signup_username, signup_password, signup_email)
                            if success:
                                st.success(message)
                                st.session_state.user_authenticated = True
                                st.session_state.username = signup_username
                                # Set auth cookie for persistence
                                set_auth_cookie(signup_username)
                                st.rerun()
                            else:
                                st.error(message)
                    else:
                        st.warning("Please fill in all fields.")

def is_user_authenticated():
    """Check if user is authenticated"""
    # Check cookies first
    is_auth, _ = check_authentication()
    if is_auth:
        return True
    # Fallback to session state
    return st.session_state.get("user_authenticated", False)

def get_current_username():
    """Get the username of the logged-in user"""
    # Check cookies first
    is_auth, username = check_authentication()
    if is_auth and username:
        return username
    # Fallback to session state
    return st.session_state.get("username", "")