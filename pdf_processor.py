import os
import tempfile
import sys
import streamlit as st
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma

def process_uploaded_pdf(uploaded_file):
    if uploaded_file is None: return None
    tmp_file_path = None
    db = None
    
    try:
        print(f"Processing: {uploaded_file.name}")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file: 
            tmp_file.write(uploaded_file.getvalue())
            tmp_file_path = tmp_file.name
        
        loader = PyPDFLoader(tmp_file_path)
        documents = loader.load()
        
        if not documents: 
            print("No text found in document.")
            os.unlink(tmp_file_path)
            return None
        
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=150)
        texts = text_splitter.split_documents(documents)
        
        if not texts: 
            print("No chunks created.")
            os.unlink(tmp_file_path)
            return None
        
        embedding_function = st.session_state.embedding_model
        db = Chroma.from_documents(texts, embedding_function)
        os.unlink(tmp_file_path)
        print("Temp file deleted.")
        
        return db
    except Exception as e: 
        print(f"PDF Error: {e}", file=sys.stderr)
        if tmp_file_path and os.path.exists(tmp_file_path):
            os.unlink(tmp_file_path)
        return None

def get_raw_document_text(source_docs):
     if not source_docs: return "Relevant section not found."
     raw_text = "\n\n".join([doc.page_content for doc in source_docs])
     pages = sorted(list(set([doc.metadata.get('page', -1) + 1 for doc in source_docs if doc.metadata.get('page', -1) != -1])))
     page_info = f"Found on page(s): {', '.join(map(str, pages))}" if pages else "Page info unavailable."
     return f"Relevant text:\n\n---\n{raw_text}\n---\n\n{page_info}"