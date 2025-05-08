import os
import hashlib
import json
import streamlit as st
from datetime import datetime

# Path to the user database file
USER_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_database.json")

def initialize_user_database():
    """Initialize the user database if it doesn't exist"""
    if not os.path.exists(USER_DB_PATH):
        with open(USER_DB_PATH, 'w') as file:
            json.dump({}, file)
        return {}
    
    try:
        with open(USER_DB_PATH, 'r') as file:
            return json.load(file)
    except json.JSONDecodeError:
        # If file is corrupted, reset it
        with open(USER_DB_PATH, 'w') as file:
            json.dump({}, file)
        return {}

def save_user_database(users):
    """Save the user database"""
    with open(USER_DB_PATH, 'w') as file:
        json.dump(users, file)

def hash_password(password):
    """Hash the password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username, password, email):
    """Create a new user"""
    users = initialize_user_database()
    
    # Check if username already exists
    if username in users:
        return False, "This username already exists."
    
    # Check if email is already in use
    for user in users.values():
        if user.get('email') == email:
            return False, "This email is already in use."
    
    # Create new user
    users[username] = {
        'password_hash': hash_password(password),
        'email': email,
        'created_at': datetime.now().isoformat(),
        'last_login': None
    }
    
    save_user_database(users)
    return True, "Account created successfully!"

def authenticate_user(username, password):
    """Authenticate a user"""
    users = initialize_user_database()
    
    if username not in users:
        return False, "Incorrect username or password."
    
    if users[username]['password_hash'] != hash_password(password):
        return False, "Incorrect username or password."
    
    # Update last login time
    users[username]['last_login'] = datetime.now().isoformat()
    save_user_database(users)
    
    return True, "Login successful!"

def display_login_ui():
    """Display the login interface"""
    if 'user_authenticated' not in st.session_state:
        st.session_state.user_authenticated = False
    
    if 'username' not in st.session_state:
        st.session_state.username = ""
    
    if st.session_state.user_authenticated:
        st.sidebar.success(f"Logged in as {st.session_state.username}")
        if st.sidebar.button("Logout"):
            st.session_state.user_authenticated = False
            st.session_state.username = ""
            # Reset other user-related session states
            if 'messages' in st.session_state:
                st.session_state.messages = [{"role": "assistant", "content": "Hello! How can I help you today?"}]
            if 'current_conversation_id' in st.session_state:
                st.session_state.current_conversation_id = None
            if 'loaded_convo_id' in st.session_state:
                st.session_state.loaded_convo_id = None
            st.rerun()
    else:
        with st.sidebar.expander("🔐 Login / Sign up", expanded=not st.session_state.user_authenticated):
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
                                st.rerun()
                            else:
                                st.error(message)
                    else:
                        st.warning("Please fill in all fields.")

def is_user_authenticated():
    """Check if user is authenticated"""
    return st.session_state.get("user_authenticated", False)

def get_current_username():
    """Get the username of the logged-in user"""
    return st.session_state.get("username", "")