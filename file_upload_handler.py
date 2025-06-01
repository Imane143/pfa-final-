"""
file_upload_handler.py - Handle PDF file uploads and processing
"""
import os
import tempfile
import streamlit as st
from session_manager import debug_log, reset_conversation_state
from conversation_history import save_current_conversation
from rag_chain_creator import create_rag_chain

def process_file_upload(uploaded_file):
    """Process uploaded PDF file"""
    if uploaded_file is None:
        return False
        
    if uploaded_file.name == st.session_state.processed_file_name:
        return True  # Already processed
    
    # Show processing UI
    st.info(f"Processing '{uploaded_file.name}'...")
    progress_bar = st.progress(0)
    
    try:
        st.write("Saving temp file...")
        progress_bar.progress(20)
        debug_log(f"Processing: {uploaded_file.name}")
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_file_path = tmp_file.name
        
        st.write("Loading PDF...")
        progress_bar.progress(40)
        
        # Load PDF documents
        from langchain_community.document_loaders import PyPDFLoader
        loader = PyPDFLoader(tmp_file_path)
        documents = loader.load()
        
        if not documents:
            st.warning("No text found in the document.")
            os.unlink(tmp_file_path)
            progress_bar.empty()
            return False
        
        st.write("Splitting text...")
        progress_bar.progress(60)
        
        # Split documents into chunks
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=150)
        texts = text_splitter.split_documents(documents)
        
        if not texts:
            st.warning("No chunks created.")
            os.unlink(tmp_file_path)
            progress_bar.empty()
            return False
        
        st.write("Creating embeddings...")
        progress_bar.progress(80)
        
        st.write("Building index...")
        
        # Create vector store
        from langchain_community.vectorstores import Chroma
        st.session_state.vector_store = Chroma.from_documents(texts, st.session_state.embedding_model)
        progress_bar.progress(100)
        
        # Clean up temp file
        os.unlink(tmp_file_path)
        debug_log("Temp file deleted.")
        
        # Update session state
        st.session_state.processed_file_name = uploaded_file.name
        st.session_state.rag_chain = create_rag_chain(st.session_state.vector_store, st.session_state.llm)
        
        # Reset conversation for new document
        greeting = f"Processed '{uploaded_file.name}'. Ask a question!"
        st.session_state.messages = [{"role": "assistant", "content": greeting}]
        st.session_state.current_conversation_id = None 
        st.session_state.loaded_convo_id = None
        st.session_state.prereq_history = set()
        st.session_state.check_prereqs = True
        debug_log("Reset check_prereqs to True after file upload")
        st.session_state.prereq_checkbox_state = True
        debug_log("Reset prereq_checkbox_state to True after file upload")
        
        # Save conversation
        save_current_conversation(st.session_state.username)
        
        st.success("Processing complete!")
        return True
        
    except Exception as e:
        st.error(f"Error: {e}")
        debug_log(f"Error in PDF processing: {e}")
        
        # Reset states on error
        st.session_state.vector_store = None
        st.session_state.rag_chain = None
        st.session_state.processed_file_name = None
        
        # Clean up temp file if it exists
        if 'tmp_file_path' in locals() and os.path.exists(tmp_file_path):
            os.unlink(tmp_file_path)
        
        return False

def display_file_upload_section():
    """Display the file upload section"""
    uploaded_file = st.file_uploader("Upload your course PDF here:", type="pdf", key="fileuploader")
    
    if uploaded_file is not None:
        success = process_file_upload(uploaded_file)
        if success:
            st.rerun()
    
    return uploaded_file