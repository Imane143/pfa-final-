# --- Code chatbot/bot.py - Version Finale (Construit la DB pour tous les PDFs) ---

import os
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.vectorstores import Chroma
import shutil 
import sys 

# Chemins
DATA_PATH = "data/"
DB_PATH = "vector_db/"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2" # Doit être le même que dans main.py

def build_persistent_db():
    pdf_loader = DirectoryLoader(DATA_PATH, glob='**/*.pdf', loader_cls=PyPDFLoader, recursive=True, show_progress=True, use_multithreading=True)
    txt_loader = DirectoryLoader(DATA_PATH, glob='**/*.txt', loader_cls=TextLoader, recursive=True, show_progress=True)

    all_loaders = [pdf_loader, txt_loader]
    loaded_documents = []
    print(f"Searching for documents in '{DATA_PATH}' and subdirectories...")
    for loader in all_loaders:
        try:
            print(f"Loading documents with {loader.__class__.__name__}...")
            loaded_documents.extend(loader.load())
        except Exception as e:
            print(f"Error loading files with {loader.__class__.__name__}: {e}", file=sys.stderr)
            
    if not loaded_documents:
        print(f"FATAL ERROR: No documents found in '{DATA_PATH}'. Cannot build database.")
        return False 

    print(f"Loaded {len(loaded_documents)} document(s) total.")
    
    # Découpage
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    texts = text_splitter.split_documents(loaded_documents)
    print(f"Split documents into {len(texts)} chunks.")
    if not texts:
        print("FATAL ERROR: Text splitting resulted in zero chunks.")
        return False

    # Affichage métadonnées
    if texts: print(f"Metadata of first chunk (example): {texts[0].metadata}") 

    # Embeddings
    print(f"Loading embedding model ({EMBEDDING_MODEL_NAME})...")
    try:
        embeddings = SentenceTransformerEmbeddings(model_name=EMBEDDING_MODEL_NAME)
        print("Embeddings model loaded successfully.")
    except Exception as e:
        print(f"FATAL ERROR loading embedding model: {e}", file=sys.stderr)
        return False

    # Suppression ancienne DB
    if os.path.exists(DB_PATH):
        print(f"Deleting old database folder at {DB_PATH}")
        try:
            shutil.rmtree(DB_PATH)
            print("Old database deleted.")
        except OSError as e:
            print(f"ERROR: Could not delete old database folder '{DB_PATH}'. Error: {e}", file=sys.stderr)
            print("Please ensure no other process (like Streamlit) is using it and try again.")
            return False 

    # Création Nouvelle DB
    print(f"Creating new persistent vector database at {DB_PATH}...")
    try:
        db = Chroma.from_documents(texts, embeddings, persist_directory=DB_PATH)
        print("Vector database created and persisted successfully.")
        return True # Succès
    except Exception as e:
        print(f"FATAL ERROR creating Chroma database: {e}", file=sys.stderr)
        return False

# Point d'entrée
if __name__ == "__main__":
    print("--- Starting Database Build Process ---")
    success = build_persistent_db()
    if success:
        print("--- Database Build Process Finished Successfully ---")
    else:
        print("--- Database Build Process Failed ---")