"""
database_manager.py - SQLite database implementation for the Educational Chatbot
"""
import os
import sqlite3
import json
from datetime import datetime
import hashlib

# Path to the database file
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chatbot_data.db")

def initialize_database():
    """Initialize the SQLite database with required tables if they don't exist"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password_hash TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        created_at TEXT NOT NULL,
        last_login TEXT
    )
    ''')
    
    # Create conversations table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS conversations (
        conversation_id TEXT PRIMARY KEY,
        username TEXT NOT NULL,
        title TEXT NOT NULL,
        last_updated TEXT NOT NULL,
        messages TEXT NOT NULL,
        document_name TEXT,
        FOREIGN KEY (username) REFERENCES users (username)
    )
    ''')
    
    conn.commit()
    conn.close()
    
    print(f"Database initialized at {DB_PATH}")
    return True

def hash_password(password):
    """Hash the password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

# User management functions
def create_user(username, password, email):
    """Create a new user in the database"""
    initialize_database()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if username already exists
        cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            conn.close()
            return False, "This username already exists."
        
        # Check if email is already in use
        cursor.execute("SELECT email FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            conn.close()
            return False, "This email is already in use."
        
        # Create new user
        created_at = datetime.now().isoformat()
        password_hash = hash_password(password)
        
        cursor.execute(
            "INSERT INTO users (username, password_hash, email, created_at) VALUES (?, ?, ?, ?)",
            (username, password_hash, email, created_at)
        )
        
        conn.commit()
        conn.close()
        return True, "Account created successfully!"
        
    except Exception as e:
        conn.rollback()
        conn.close()
        print(f"Error creating user: {e}")
        return False, f"Error creating account: {str(e)}"

def authenticate_user(username, password):
    """Authenticate a user against the database"""
    initialize_database()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if user exists and password matches
        cursor.execute(
            "SELECT password_hash FROM users WHERE username = ?", 
            (username,)
        )
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return False, "Incorrect username or password."
        
        stored_hash = result[0]
        if stored_hash != hash_password(password):
            conn.close()
            return False, "Incorrect username or password."
        
        # Update last login time
        last_login = datetime.now().isoformat()
        cursor.execute(
            "UPDATE users SET last_login = ? WHERE username = ?",
            (last_login, username)
        )
        
        conn.commit()
        conn.close()
        return True, "Login successful!"
        
    except Exception as e:
        conn.close()
        print(f"Error authenticating user: {e}")
        return False, f"Error during login: {str(e)}"

# Conversation management functions
def save_conversation(username, conversation_id, title, messages, document_name=None):
    """Save a conversation to the database"""
    if not username:
        return None
    
    initialize_database()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
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
        
        last_updated = datetime.now().isoformat()
        messages_json = json.dumps(messages)
        
        # Check if conversation already exists
        cursor.execute(
            "SELECT conversation_id FROM conversations WHERE conversation_id = ?", 
            (conversation_id,)
        )
        
        if cursor.fetchone():
            # Update existing conversation
            cursor.execute(
                "UPDATE conversations SET title = ?, last_updated = ?, messages = ?, document_name = ? WHERE conversation_id = ?",
                (title, last_updated, messages_json, document_name, conversation_id)
            )
        else:
            # Insert new conversation
            cursor.execute(
                "INSERT INTO conversations (conversation_id, username, title, last_updated, messages, document_name) VALUES (?, ?, ?, ?, ?, ?)",
                (conversation_id, username, title, last_updated, messages_json, document_name)
            )
        
        conn.commit()
        conn.close()
        return conversation_id
        
    except Exception as e:
        conn.rollback()
        conn.close()
        print(f"Error saving conversation: {e}")
        return None

def load_user_conversations(username):
    """Load all conversations for a user"""
    if not username:
        return {}
    
    initialize_database()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # This enables column access by name
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "SELECT * FROM conversations WHERE username = ? ORDER BY last_updated DESC",
            (username,)
        )
        
        rows = cursor.fetchall()
        conversations = {}
        
        for row in rows:
            conversations[row['conversation_id']] = {
                'title': row['title'],
                'last_updated': row['last_updated'],
                'messages': json.loads(row['messages']),
                'document': row['document_name'] or ''
            }
        
        conn.close()
        return conversations
        
    except Exception as e:
        conn.close()
        print(f"Error loading conversations: {e}")
        return {}

def load_conversation(username, conversation_id):
    """Load a specific conversation"""
    if not username or not conversation_id:
        return None
    
    initialize_database()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "SELECT * FROM conversations WHERE username = ? AND conversation_id = ?",
            (username, conversation_id)
        )
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None
        
        conversation = {
            'title': row['title'],
            'last_updated': row['last_updated'],
            'messages': json.loads(row['messages']),
            'document': row['document_name'] or ''
        }
        
        conn.close()
        return conversation
        
    except Exception as e:
        conn.close()
        print(f"Error loading conversation: {e}")
        return None

def delete_conversation(username, conversation_id):
    """Delete a conversation from the database"""
    if not username or not conversation_id:
        return False
    
    initialize_database()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "DELETE FROM conversations WHERE username = ? AND conversation_id = ?",
            (username, conversation_id)
        )
        
        if cursor.rowcount > 0:
            conn.commit()
            conn.close()
            return True
        else:
            conn.close()
            return False
            
    except Exception as e:
        conn.rollback()
        conn.close()
        print(f"Error deleting conversation: {e}")
        return False

# Migration function to import existing data
def migrate_from_json():
    """Migrate existing JSON data to SQLite database"""
    # Path to the user database file
    USER_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_database.json")
    # Path to conversation histories folder
    HISTORY_FOLDER = os.path.join(os.path.expanduser("~"), "Documents", "educational_chatbot_histories")
    
    # Initialize database
    initialize_database()
    
    # Migrate users if user_database.json exists
    if os.path.exists(USER_DB_PATH):
        try:
            with open(USER_DB_PATH, 'r') as file:
                users = json.load(file)
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            for username, user_data in users.items():
                # Check if user already exists in database
                cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
                if not cursor.fetchone():
                    cursor.execute(
                        "INSERT INTO users (username, password_hash, email, created_at, last_login) VALUES (?, ?, ?, ?, ?)",
                        (
                            username, 
                            user_data.get('password_hash', ''), 
                            user_data.get('email', ''), 
                            user_data.get('created_at', datetime.now().isoformat()),
                            user_data.get('last_login')
                        )
                    )
            
            conn.commit()
            conn.close()
            print("Users migrated successfully.")
        except Exception as e:
            print(f"Error migrating users: {e}")
    
    # Migrate conversation histories if folder exists
    if os.path.exists(HISTORY_FOLDER):
        try:
            # Get all history files
            history_files = [f for f in os.listdir(HISTORY_FOLDER) if f.endswith('_history.json')]
            
            for file_name in history_files:
                # Extract username from filename
                username = file_name.replace('_history.json', '')
                file_path = os.path.join(HISTORY_FOLDER, file_name)
                
                with open(file_path, 'r') as file:
                    try:
                        conversations = json.load(file)
                        
                        for conv_id, conv_data in conversations.items():
                            save_conversation(
                                username=username,
                                conversation_id=conv_id,
                                title=conv_data.get('title', 'Untitled'),
                                messages=conv_data.get('messages', []),
                                document_name=conv_data.get('document', '')
                            )
                    except json.JSONDecodeError:
                        print(f"Error decoding JSON from {file_path}")
            
            print("Conversation histories migrated successfully.")
        except Exception as e:
            print(f"Error migrating conversation histories: {e}")
    
    return True

# Run migration if this file is executed directly
if __name__ == "__main__":
    print("Starting database initialization and migration...")
    initialize_database()
    migrate_from_json()
    print("Database setup complete.")