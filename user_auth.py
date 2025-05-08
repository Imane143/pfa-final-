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
    
    # Store in session state in multiple ways for redundancy
    st.session_state.auth_token = token
    st.session_state.stored_token = token
    
    # Format expiry for cookie
    expiry_str = datetime.fromtimestamp(expiry).strftime('%a, %d %b %Y %H:%M:%S GMT')
    
    # Use multiple methods for more reliable persistence
    js = f"""
    <script>
    // Store in both localStorage and cookies for redundancy
    try {{
        // Primary method: localStorage (most reliable for Streamlit)
        localStorage.setItem('{SESSION_COOKIE_NAME}', '{token}');
        console.log("Token stored in localStorage");
        
        // Backup method: cookies
        document.cookie = "{SESSION_COOKIE_NAME}={token};path=/;expires={expiry_str};SameSite=Lax";
        console.log("Token stored in cookies");
        
        // Communication with Streamlit
        try {{
            window.parent.postMessage({{
                type: "streamlit:setComponentValue",
                value: "{token}",
                dataType: "str",
                key: "stored_token"
            }}, "*");
            console.log("Token sent to Streamlit via postMessage");
        }} catch (e) {{
            console.error("Error sending token to Streamlit:", e);
        }}
        
        // Add token to URL once (as parameter) for immediate use
        if (!window.location.search.includes('auth_token')) {{
            const separator = window.location.search ? '&' : '?';
            const newUrl = window.location.pathname + 
                          window.location.search + 
                          separator + 
                          'auth_token={token}';
            
            // Use history API to avoid full page reload
            window.history.replaceState(null, document.title, newUrl);
            console.log("Token added to URL via history API");
        }}
        
        console.log("Authentication data saved successfully");
    }} catch (e) {{
        console.error("Error saving auth data:", e);
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
    
    # Try from query parameters first
    try:
        param_token = st.query_params.get("auth_token")
        if param_token:
            print("Found token in URL query params")
            return param_token
    except Exception as e:
        print(f"Error getting token from query params: {e}")
    
    # Try from session state (if it was stored there by previous JavaScript)
    if "stored_token" in st.session_state and st.session_state.stored_token:
        print("Found token in stored_token session state")
        return st.session_state.stored_token
    
    # Add JavaScript to check localStorage and cookies
    # This will set both a token in the URL if found in localStorage
    # AND store it in session_state.stored_token via Streamlit's
    # component communication
    check_storage_js = """
    <script>
    // Function to find auth token in various storage locations
    function findAuthToken() {
        // Check localStorage first (most reliable in Streamlit)
        const localToken = localStorage.getItem('auth_token');
        if (localToken) {
            console.log("Found token in localStorage");
            return localToken;
        }
        
        // Check URL hash as fallback
        if (window.location.hash.includes('auth_token')) {
            const hashParams = new URLSearchParams(window.location.hash.substring(1));
            const hashToken = hashParams.get('auth_token');
            if (hashToken) {
                console.log("Found token in URL hash");
                return hashToken;
            }
        }
        
        // Last resort - try to get from cookies
        const cookies = document.cookie.split(';');
        for (const cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'auth_token' && value) {
                console.log("Found token in cookies");
                return value;
            }
        }
        
        return null;
    }
    
    // Function to apply the token to the page
    function applyAuthToken() {
        const token = findAuthToken();
        if (!token) return false;
        
        // Store token in localStorage as the primary storage method
        localStorage.setItem('auth_token', token);
        
        // Add token to URL if not already there
        if (!window.location.search.includes('auth_token')) {
            console.log("Adding auth token to URL");
            const separator = window.location.search ? '&' : '?';
            const newUrl = window.location.pathname + 
                          window.location.search + 
                          separator + 
                          'auth_token=' + token;
            
            // Use history API to avoid full page reload
            window.history.replaceState(null, document.title, newUrl);
            
            // If that didn't work (e.g. in some Streamlit scenarios), reload with the token in URL
            if (!window.location.search.includes('auth_token')) {
                window.location.href = newUrl;
                return true;
            }
        }
        
        // Also communicate with Streamlit via session state
        // This is a backup method that works even when URL parameters don't
        try {
            const streamlitDoc = window.parent.document;
            const tokenInput = streamlitDoc.createElement('input');
            tokenInput.setAttribute('type', 'hidden');
            tokenInput.setAttribute('id', 'stored_token');
            tokenInput.setAttribute('data-stcore', token);
            tokenInput.setAttribute('name', 'stored_token');
            tokenInput.setAttribute('value', token);
            streamlitDoc.body.appendChild(tokenInput);
            
            // Trigger a custom event that Streamlit can detect
            const event = new Event('stored_token_updated');
            streamlitDoc.dispatchEvent(event);
            
            console.log("Token communicated to Streamlit");
        } catch (e) {
            console.error("Error communicating with Streamlit:", e);
        }
        
        return true;
    }
    
    // Run immediately
    if (document.readyState === 'complete') {
        applyAuthToken();
    } else {
        // Or wait for page to load if needed
        window.addEventListener('load', applyAuthToken);
    }
    
    // Also run on first Streamlit render
    const observer = new MutationObserver((mutations) => {
        for (const mutation of mutations) {
            if (mutation.addedNodes.length) {
                applyAuthToken();
                observer.disconnect();
                break;
            }
        }
    });
    
    observer.observe(document.body, { childList: true, subtree: true });
    
    // Set a flag to ensure we only redirect once
    if (!window.authCheckRun) {
        window.authCheckRun = true;
        setTimeout(applyAuthToken, 300);
    }
    </script>
    
    <!-- Add listener for Streamlit session state -->
    <script>
    // Create a component to communicate with Streamlit
    function sendTokenToStreamlit() {
        const token = localStorage.getItem('auth_token');
        if (token) {
            window.parent.postMessage({
                type: "streamlit:setComponentValue",
                value: token,
                dataType: "str",
                key: "stored_token"
            }, "*");
        }
    }
    
    // Try multiple times with increasing delays
    setTimeout(sendTokenToStreamlit, 100);
    setTimeout(sendTokenToStreamlit, 500);
    setTimeout(sendTokenToStreamlit, 1000);
    </script>
    """
    
    # Initialize a session state variable for the stored token
    if "stored_token" not in st.session_state:
        st.session_state.stored_token = None
    
    # Display the JS code to check storage
    st.markdown(check_storage_js, unsafe_allow_html=True)
    
    # Create a hidden component to receive the token from JavaScript
    # This is a workaround to get data from JavaScript to Python in Streamlit
    if st.session_state.stored_token:
        token = st.session_state.stored_token
    
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
            
            # Also store in stored_token for redundancy
            st.session_state.stored_token = token
            
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