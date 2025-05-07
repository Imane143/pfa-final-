import os
import streamlit as st
from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import tempfile
import sys

# --- Initial Configuration ---
load_dotenv()
google_api_key = os.getenv("GOOGLE_API_KEY")
if not google_api_key:
    st.error("Google API Key (Gemini) not found. Make sure it's in the .env file as GOOGLE_API_KEY")
    st.stop()

# Using a smaller, faster embedding model
EMBEDDING_MODEL_NAME = "paraphrase-MiniLM-L3-v2"
LLM_MODEL_NAME = "gemini-1.5-flash"

# --- Utility Functions ---
@st.cache_resource
def load_embedding_model():
    with st.spinner("Loading embedding model (this might take a moment)..."):
        print("Loading embedding model...")
        return SentenceTransformerEmbeddings(model_name=EMBEDDING_MODEL_NAME)

@st.cache_resource
def load_llm():
    with st.spinner("Initializing Gemini model..."):
        print(f"Loading Google Gemini LLM: {LLM_MODEL_NAME}...")
        try:
            llm = ChatGoogleGenerativeAI(
                model=LLM_MODEL_NAME, 
                google_api_key=google_api_key,
                temperature=0.1,
                convert_system_message_to_human=True
            )
            print("LLM Gemini loaded.")
            return llm
        except Exception as e:
            st.error(f"Error loading Gemini model: {e}")
            st.stop()

# --- Function to process uploaded PDF ---
def process_uploaded_pdf(uploaded_file):
    if uploaded_file is None: return None
    
    progress_bar = st.progress(0)
    progress_text = st.empty()
    
    progress_text.text("Processing uploaded file...")
    progress_bar.progress(10)
    
    print(f"Processing uploaded file: {uploaded_file.name}")
    tmp_file_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_file_path = tmp_file.name
        
        progress_text.text("Loading PDF content...")
        progress_bar.progress(30)
        loader = PyPDFLoader(tmp_file_path)
        documents = loader.load()
        
        if not documents: 
            st.warning("Could not extract text from the PDF.")
            os.unlink(tmp_file_path)
            return None
        
        progress_text.text("Splitting text into chunks...")
        progress_bar.progress(50)
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=300,
            chunk_overlap=150,  # More overlap to ensure better context retrieval
            length_function=len
        )
        texts = text_splitter.split_documents(documents)
        
        if not texts: 
            st.warning("Zero chunks created after splitting.")
            os.unlink(tmp_file_path)
            return None
        
        progress_text.text("Creating vector embeddings...")
        progress_bar.progress(70)
        embedding_function = load_embedding_model()
        
        progress_text.text("Building search index...")
        progress_bar.progress(90)
        db = Chroma.from_documents(texts, embedding_function)
        
        # Store the entire document content for direct access
        if "document_content" not in st.session_state:
            st.session_state.document_content = "".join([doc.page_content for doc in documents])
        
        # Extract a table of contents from the document if possible
        progress_text.text("Extracting document structure...")
        
        os.unlink(tmp_file_path)
        progress_text.text("Processing complete!")
        progress_bar.progress(100)
        
        return db
    except Exception as e:
        st.error(f"Error processing PDF: {e}")
        if tmp_file_path and os.path.exists(tmp_file_path):
            try: os.unlink(tmp_file_path)
            except Exception as cleanup_e: print(f"Error cleaning up temp file: {cleanup_e}", file=sys.stderr)
        return None

# --- Function to get raw text from documents ---
def get_raw_document_text(source_docs):
    """Extract and return raw text from the document."""
    if not source_docs:
        return "I couldn't find the relevant section in the document."
    
    # Combine the relevant retrieved chunks
    raw_text = "\n\n".join([doc.page_content for doc in source_docs])
    
    # Include page information
    pages = sorted(set([doc.metadata.get('page', 'unknown') for doc in source_docs]))
    page_info = f"Found on page(s): {', '.join(map(str, pages))}"
    
    return f"Here's the exact text from the document:\n\n\n{raw_text}\n\n\n{page_info}"

# --- Function to detect prerequisites for any topic ---
def detect_prerequisites(query, llm):
    """Detect fundamental prerequisite topics for understanding the query topic."""
    if not llm:
        return None
    
    # Extract the main topic and identify its prerequisites
    prereq_prompt = f"""
    Task: Identify the most important prerequisite topic needed to understand the following question:
    
    Question: "{query}"
    
    Instructions:
    1. First, identify the main topic or concept being asked about.
    2. Then, determine ONE specific fundamental prerequisite topic that is essential for understanding this main topic.
    3. The prerequisite should be a specific concept that is truly foundational to the topic (not just tangentially related).
    4. The prerequisite should be more basic than the main topic.
    
    Format your response exactly as follows:
    MAIN_TOPIC: [Main topic from the question]
    PREREQUISITE: [One specific prerequisite topic]
    """
    
    try:
        # Use direct LLM for this to get general knowledge prerequisites
        response = llm.invoke(prereq_prompt)
        response_text = response.content if hasattr(response, 'content') else str(response)
        
        # Extract the prerequisite topic
        prereq_topic = None
        main_topic = None
        
        for line in response_text.split("\n"):
            line = line.strip()
            if line.startswith("MAIN_TOPIC:"):
                main_topic = line[len("MAIN_TOPIC:"):].strip()
            elif line.startswith("PREREQUISITE:"):
                prereq_topic = line[len("PREREQUISITE:"):].strip()
        
        # Basic filtering to avoid unhelpful prerequisites
        if prereq_topic:
            # Skip if prereq is the same as the topic
            if prereq_topic.lower() == main_topic.lower():
                return None
                
            # Skip if prereq contains words like "basic", "understanding", etc.
            low_quality_words = ["basic", "understanding of", "knowledge of", "fundamentals of", 
                               "introduction to", "familiarity with", "background in"]
            if any(word in prereq_topic.lower() for word in low_quality_words):
                return None
                
            print(f"Detected prerequisite: {prereq_topic} for query about {main_topic}")
            return prereq_topic
        
        return None
    except Exception as e:
        print(f"Error detecting prerequisites: {e}")
        return None

# --- Function to explain a prerequisite topic using general knowledge ---
def explain_prerequisite(topic, llm):
    """Explain a prerequisite topic using the LLM's general knowledge."""
    if not topic or not llm:
        return f"I couldn't find information about '{topic}'."
    
    explain_prompt = f"""
    Please provide a clear and concise explanation of '{topic}' as a fundamental concept.
    
    Your explanation should:
    1. Define what '{topic}' is in simple terms
    2. Explain why it's important as a foundational concept
    3. Include 1-2 simple examples if appropriate
    4. Be around 4-6 sentences total
    
    Keep your explanation at an introductory level that would help someone understand more advanced topics.
    """
    
    try:
        # Use direct LLM call for general knowledge
        response = llm.invoke(explain_prompt)
        explanation = response.content if hasattr(response, 'content') else str(response)
        
        return f"*Prerequisite Topic: {topic}*\n\n{explanation}\n\n---\n\nNow let me answer your original question based on the document:"
    except Exception as e:
        print(f"Error explaining prerequisite: {e}")
        return f"I encountered an error while trying to explain '{topic}', but I'll still try to answer your original question:"

# --- RAG Chain Creation ---
def create_rag_chain(_db, _llm):
    if _db is None: return None
    print("Creating RAG chain...")
    
    retriever = _db.as_retriever(
        search_kwargs={
            'k': 5  # Number of documents to retrieve
        }
    )
    
    prompt_template = """You are an educational AI assistant tasked with answering questions about course materials. 
    Your job is to analyze the context provided and directly answer questions about the course content.
    
    If the user is explicitly asking for the exact/specific text or section from the document, DO NOT summarize or paraphrase. 
    Instead, provide the EXACT text from the context verbatim, preserving formatting, code samples, and terminology.
    
    For normal questions about the content, provide clear and helpful explanations based ONLY on the provided context.
    
    If asked for exact text or quotes from the document, ONLY provide text that appears verbatim in the context below. 
    DO NOT make up or hallucinate text that isn't present in the context. If the exact information isn't available,
    politely state that the specific text isn't found in the provided context.
    
    Context: {context}
    
    Question: {question}
    
    Helpful Answer:"""
    
    QA_CHAIN_PROMPT = PromptTemplate.from_template(prompt_template)
    qa_chain = RetrievalQA.from_chain_type(
        _llm, 
        retriever=retriever, 
        chain_type_kwargs={"prompt": QA_CHAIN_PROMPT}, 
        return_source_documents=True
    )
    print("RAG chain created.")
    return qa_chain

# --- Streamlit Interface ---
st.set_page_config(page_title="AI Educational Chatbot", page_icon="🎓")
st.title("🎓 AI Educational Chatbot")

# Initialize session state
if "messages" not in st.session_state: 
    st.session_state.messages = [{"role": "assistant", "content": "Hello! Please upload a course PDF to begin."}]
if "vector_store" not in st.session_state: 
    st.session_state.vector_store = None
if "rag_chain" not in st.session_state: 
    st.session_state.rag_chain = None
if "llm" not in st.session_state:
    st.session_state.llm = None
if "processed_file_name" not in st.session_state: 
    st.session_state.processed_file_name = None
if "document_content" not in st.session_state:
    st.session_state.document_content = ""
if "current_question" not in st.session_state:
    st.session_state.current_question = None
if "prerequisite_topic" not in st.session_state:
    st.session_state.prerequisite_topic = None
if "waiting_for_prereq_response" not in st.session_state:
    st.session_state.waiting_for_prereq_response = False
if "prereq_history" not in st.session_state:
    st.session_state.prereq_history = set()  # Track shown prerequisites to avoid repetition

# --- File Upload Section ---
uploaded_file = st.file_uploader("Upload your course PDF here:", type="pdf", key="fileuploader")

# --- Logic to process upload ---
if uploaded_file is not None:
    if uploaded_file.name != st.session_state.processed_file_name:
        st.info(f"Processing '{uploaded_file.name}'...")
        
        # Load models
        st.session_state.llm = load_llm()
        
        st.session_state.vector_store = process_uploaded_pdf(uploaded_file)
        st.session_state.processed_file_name = uploaded_file.name
        
        if st.session_state.vector_store:
            st.session_state.rag_chain = create_rag_chain(st.session_state.vector_store, st.session_state.llm)
            greeting = f"I've processed '{uploaded_file.name}'. Ask me a question about the content!"
            st.session_state.messages = [{"role": "assistant", "content": greeting}]
            st.session_state.prereq_history = set()  # Reset prerequisite history
            st.success(f"'{uploaded_file.name}' processed successfully.")
            st.rerun()
        else:
            st.error("Failed to process uploaded PDF.")
            st.session_state.vector_store = None
            st.session_state.rag_chain = None
            st.session_state.processed_file_name = None

# Handle file removal
elif uploaded_file is None and st.session_state.processed_file_name: 
    st.session_state.messages = [{"role": "assistant", "content": "Upload a PDF to start."}]
    # Reset all state variables
    st.session_state.vector_store = None
    st.session_state.rag_chain = None
    st.session_state.llm = None
    st.session_state.processed_file_name = None
    st.session_state.document_content = ""
    st.session_state.current_question = None
    st.session_state.prerequisite_topic = None
    st.session_state.waiting_for_prereq_response = False
    st.session_state.prereq_history = set()
    st.rerun()

# --- Display Context Caption ---
if st.session_state.rag_chain and st.session_state.processed_file_name:
    st.caption(f"Chatting with: '{st.session_state.processed_file_name}' - LLM: {LLM_MODEL_NAME}")
elif not uploaded_file:
    st.caption(f"LLM Model: {LLM_MODEL_NAME} - Upload a PDF to start")

# --- Chat Interface Section ---
if st.session_state.rag_chain:
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Function to get RAG answers
    def get_rag_answer(user_query, rag_chain_instance):
        """Get answer from the RAG system."""
        if not rag_chain_instance: 
            return "Error: Search system not initialized.", []
        
        # Check if user is asking for exact text
        is_raw_text_request = any(phrase in user_query.lower() for phrase in 
                               ["exact text", "exact part", "specific part", "exact content",
                                "verbatim", "word for word", "direct quote", "literal text", 
                                "exactly say", "raw text", "exact section", "give me the text", 
                                "show me the text", "show the exact", "what does it say"])
        
        with st.spinner("Searching document for answer..."):
            try:
                # Get response from RAG
                response = rag_chain_instance.invoke({"query": user_query})
                source_docs = response.get("source_documents", [])
                
                # Handle raw text requests differently
                if is_raw_text_request:
                    answer = get_raw_document_text(source_docs)
                else:
                    answer = response.get("result", "Sorry, I couldn't find an answer to that in the document.")
                
                return answer, source_docs
            except Exception as e:
                print(f"Error during RAG search: {e}", file=sys.stderr)
                st.error(f"An error occurred while generating the response.")
                return "Sorry, an error prevented me from responding.", []

    # User input area
    if prompt := st.chat_input("Your question here...", key="chat_input"):
        # Display user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): 
            st.markdown(prompt)
        
        # Check if waiting for user response about prerequisites
        if st.session_state.waiting_for_prereq_response:
            prereq_topic = st.session_state.prerequisite_topic
            original_question = st.session_state.current_question
            
            # Process user response to prerequisite offer
            if any(word in prompt.lower() for word in ["yes", "y", "sure", "ok", "okay", "explain", "please"]):
                # User wants prerequisite explanation
                with st.spinner(f"Preparing explanation for {prereq_topic}..."):
                    # Get general knowledge explanation for the prerequisite
                    prereq_explanation = explain_prerequisite(prereq_topic, st.session_state.llm)
                
                with st.spinner("Answering your original question..."):
                    # Get document-based answer for the original question
                    answer, _ = get_rag_answer(original_question, st.session_state.rag_chain)
                
                # Combine the responses
                full_response = f"{prereq_explanation}\n\n{answer}"
                
                with st.chat_message("assistant"):
                    st.markdown(full_response)
                
                st.session_state.messages.append({"role": "assistant", "content": full_response})
            else:
                # User wants to skip prerequisite
                with st.spinner("Answering your question..."):
                    answer, _ = get_rag_answer(original_question, st.session_state.rag_chain)
                
                with st.chat_message("assistant"):
                    st.markdown(answer)
                
                st.session_state.messages.append({"role": "assistant", "content": answer})
            
            # Reset prerequisite state
            st.session_state.waiting_for_prereq_response = False
            st.session_state.current_question = None
            st.session_state.prerequisite_topic = None
            
        else:
            # New question flow
            st.session_state.current_question = prompt
            
            # Check for prerequisites using general knowledge
            prereq_topic = detect_prerequisites(prompt, st.session_state.llm)
            
            # Check if we've already shown this prerequisite to avoid repetition
            if prereq_topic and prereq_topic in st.session_state.prereq_history:
                prereq_topic = None
            
            if prereq_topic:
                # Add to history to avoid showing again
                st.session_state.prereq_history.add(prereq_topic)
                
                # Set state for prerequisite handling
                st.session_state.prerequisite_topic = prereq_topic
                st.session_state.waiting_for_prereq_response = True
                
                # Ask user if they want the prerequisite explained
                prereq_message = f"To understand this topic well, you would need to understand *{prereq_topic}*. Would you like me to explain this prerequisite topic first? (Reply 'yes' if you want me to explain it, or 'skip' to proceed directly to your answer)"
                
                with st.chat_message("assistant"):
                    st.markdown(prereq_message)
                
                st.session_state.messages.append({"role": "assistant", "content": prereq_message})
                
            else:
                # No prerequisites needed, answer directly
                with st.spinner("Searching for answer..."):
                    answer, _ = get_rag_answer(prompt, st.session_state.rag_chain)
                
                with st.chat_message("assistant"):
                    st.markdown(answer)
                
                st.session_state.messages.append({"role": "assistant", "content": answer})
                st.session_state.current_question = None

else:
    if not uploaded_file:
        st.info("Please upload a PDF document to begin.")