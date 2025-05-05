# --- Code main.py - Version Finale: Upload Seul + Navigateur Caché ---
# --- PREDEFINED_COURSES contient TES mappings ---

import os
import streamlit as st
from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage, AIMessage
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import tempfile
import sys

# --- Structures pour les cours prédéfinis ---
# !!! VÉRIFIE QUE CE SONT BIEN TES MAPPINGS CORRIGÉS !!!
PREDEFINED_COURSES = {
    "Cours Java": { 
        "pdf_filename": "cours_java.pdf", # !!! VÉRIFIE NOM EXACT !!!
        "structure": [
            "What is Java", "Java Basic Syntax", "Java Identifiers", "Java Modifiers",
            "Java Variables", "Java Arrays", "Java Enums", "Java Keywords",
            "Data Types in Java", "Java Literals", "Java Access Modifiers",
            "Java Basic Operators", "Control Statements", "Loops", 
            "Java Methods", "Java Classes & Objects", "Exceptions Handling"
        ],
        "page_map": {
            (1, 1): "What is Java?", (1, 1): "Java Environment Setup:", (1, 1): "Java Basic Syntax:",
            (1, 2): "First Java Program:", (2, 2): "Java Identifiers:", (2, 2): "Java Modifiers:",
            (2, 3): "Java Variables:", (3, 3): "Java Arrays:", (3, 3): "Java Enums:",
            (3, 4): "Java Keywords:", (4, 4): "Comments in Java:", (4, 4): "Data Types in Java:",
            (4, 4): "Primitive Data Types:", (4, 5): "Reference Data Types:", (5, 5): "Java Literals:",
            (5, 5): "Java Access Modifiers:", (5, 5): "Java Basic Operators:", (5, 6): "The Arithmetic Operators:",
            (6, 6): "The Relational Operators:", (6, 7): "The Bitwise Operators:", (7, 7): "The Logical Operators:",
            (7, 8): "The Assignment Operators:", (8, 8): "Misc Operators:", (8, 8): "Conditional Operator",
            (8, 8): "instanceOf Operator:", (8, 8): "Precedence of Java Operators:", (8, 9): "The while Loop:",
            (9, 9): "The do...while Loop:", (9, 9): "The for Loop:", (9, 9): "Enhanced for loop in Java:",
            (9, 9): "The break Keyword:", (9, 10): "The continue Keyword:", (10, 10): "The if Statement:",
            (10, 10): "The if...else Statement:", (10, 10): "The if...else if...else Statement:",
            (10, 11): "Nested if...else Statement:", (11, 11): "The switch Statement:", 
            (11, 12): "Java Methods:", (12, 12): "Java Classes & Objects:", (12, 12): "Exceptions Handling:",
            (12, 13): "Multiple catch Blocks:", (13, 13): "The throws/throw Keywords:",
            (13, 13): "The finally Keyword:"
        }
    },
    "Cours SQL": { 
        "pdf_filename": "cours_sql.pdf",   
        "structure": [
            "Basic Concepts", "SQL Syntax", "SQL Commands", 
            "SQL Operators", "SQL Useful Functions"
            ],
        "page_map": {
            (1, 1): "What is SQL?", (1, 1): "Why SQL?", (1, 1): "What is RDBMS?", 
            (1, 1): "What is table ?", (1, 1): "What is field?", (1, 2): "What is record or row?", 
            (2, 2): "What is column?", (2, 2): "What is NULL value?", (2, 2): "SQL Constraints:", 
            (2, 2): "SQL Syntax:", (2, 2): "SQL SELECT Statement:", (2, 2): "SQL DISTINCT Clause:", 
            (2, 2): "SQL WHERE Clause:", (2, 2): "SQL AND/OR Clause:", (2, 2): "SQL IN Clause:",
            (3, 3): "SQL BETWEEN Clause:", (3, 3): "SQL Like Clause:", (3, 3): "SQL ORDER BY Clause:", 
            (3, 3): "SQL GROUP BY Clause:", (3, 3): "SQL COUNT Clause:", (3, 3): "SQL HAVING Clause:", 
            (3, 3): "SQL CREATE TABLE Statement:", (3, 3): "SQL DROP TABLE Statement:", 
            (3, 3): "SQL CREATE INDEX Statement :", (3, 4): "SQL DROP INDEX Statement :", 
            (4, 4): "SQL DESC Statement :", (4, 4): "SQL TRUNCATE TABLE Statement:", 
            (4, 4): "SQL ALTER TABLE Statement:", (4, 4): "SQL ALTER TABLE Statement Rename :", 
            (4, 4): "SQL INSERT INTO Statement:", (4, 4): "SQL UPDATE Statement:", 
            (4, 4): "SQL DELETE Statement:", (4, 4): "SQL CREATE DATABASE Statement:", 
            (4, 4): "SQL DROP DATABASE Statement:", (4, 4): "SQL USE Statement:", 
            (4, 4): "SQL COMMIT Statement:", (4, 4): "SQL ROLLBACK Statement:", 
            (4, 4): "SQL - Operators:", (4, 5): "SQL Arithmetic Operators:", 
            (5, 6): "SQL Comparison Operators:", (6, 6): "SQL Logical Operators:", 
            (6, 7): "SQL - Useful Functions:" 
            # !!! FINISH MAPPING ALL PAGES !!!
         }
    }
}
# --- FIN DU DICTIONNAIRE (VÉRIFIE ENCORE TES PAGES !) ---


# --- Initial Configuration ---
load_dotenv()
google_api_key = os.getenv("GOOGLE_API_KEY")
if not google_api_key:
    st.error("Google API Key (Gemini) not found. Make sure it's in the .env file as GOOGLE_API_KEY")
    st.stop()
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
LLM_MODEL_NAME = "gemini-1.5-flash"

# --- Utility Functions ---
@st.cache_resource
def load_embedding_model():
    print("Loading embedding model...")
    return SentenceTransformerEmbeddings(model_name=EMBEDDING_MODEL_NAME)

@st.cache_resource
def load_llm():
    print(f"Loading Google Gemini LLM: {LLM_MODEL_NAME}...")
    try:
        llm = ChatGoogleGenerativeAI(model=LLM_MODEL_NAME, google_api_key=google_api_key,
                                     temperature=0.2, convert_system_message_to_human=True)
        print("LLM Gemini loaded.")
        return llm
    except Exception as e:
        st.error(f"Error loading Gemini model '{LLM_MODEL_NAME}'. Error: {e}")
        st.stop()

# --- Function to process uploaded PDF ---
def process_uploaded_pdf(uploaded_file):
    if uploaded_file is None: return None
    print(f"Processing uploaded file: {uploaded_file.name}")
    tmp_file_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_file_path = tmp_file.name
        loader = PyPDFLoader(tmp_file_path)
        documents = loader.load()
        if not documents: st.warning("Could not extract text."); os.unlink(tmp_file_path); return None
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        texts = text_splitter.split_documents(documents)
        if not texts: st.warning("Zero chunks after splitting."); os.unlink(tmp_file_path); return None
        print(f"DEBUG (Process): Metadata of first chunk: {texts[0].metadata}")
        embedding_function = load_embedding_model()
        db = Chroma.from_documents(texts, embedding_function) # In-memory DB
        os.unlink(tmp_file_path)
        print("In-memory vector store created.")
        return db
    except Exception as e:
        st.error(f"Error processing PDF: {e}")
        if tmp_file_path and os.path.exists(tmp_file_path):
            try: os.unlink(tmp_file_path)
            except Exception as cleanup_e: print(f"Error cleaning up temp file: {cleanup_e}", file=sys.stderr)
        return None

# --- RAG Chain Creation ---
def create_rag_chain(_db, _llm):
    if _db is None: return None
    print("Creating RAG chain...")
    retriever = _db.as_retriever(search_kwargs={'k': 3})
    prompt_template = """Use the following pieces of context to answer the question.
    If you don't know the answer based solely on the provided context, just say that you don't know.
    Context: {context}
    Question: {question}
    Helpful Answer:"""
    QA_CHAIN_PROMPT = PromptTemplate.from_template(prompt_template)
    qa_chain = RetrievalQA.from_chain_type(
        _llm, retriever=retriever, chain_type_kwargs={"prompt": QA_CHAIN_PROMPT}, return_source_documents=True
    )
    print("RAG chain created.")
    return qa_chain

# --- Helper function find_section ---
def find_section_from_sources(source_docs, page_map):
     if not source_docs or not page_map: return None
     first_source_metadata = source_docs[0].metadata
     page_number = first_source_metadata.get('page')
     if page_number is None: return None
     print(f"DEBUG (Fn): Trying find_section for page index {page_number}")
     # Iterate through the provided page map to find the matching section
     for (start_page, end_page), section_name in page_map.items():
         # Ensure keys are integers
         try:
            start_idx = int(start_page)
            end_idx = int(end_page)
            current_page_idx = int(page_number)
            if start_idx <= current_page_idx <= end_idx:
                print(f"DEBUG (Fn): Found section '{section_name}'")
                return section_name
         except (ValueError, TypeError):
             print(f"Warning (Fn): Invalid page index found in page_map or metadata: Key={(start_page, end_page)} or page_number={page_number}")
             continue # Skip invalid entries

     print(f"Warning (Fn): Page index {page_number} not found in current page_map.")
     return None


# --- Streamlit Interface ---
st.set_page_config(page_title="AI Educational Chatbot", page_icon="🎓")
st.title("🎓 AI Educational Chatbot")

# Initialize session state
if "messages" not in st.session_state: st.session_state.messages = [{"role": "assistant", "content": "Hello! Please upload a course PDF to begin."}]
if "vector_store" not in st.session_state: st.session_state.vector_store = None
if "rag_chain" not in st.session_state: st.session_state.rag_chain = None
if "processed_file_name" not in st.session_state: st.session_state.processed_file_name = None
if "current_question" not in st.session_state: st.session_state.current_question = None
if "prerequisite_check" not in st.session_state: st.session_state.prerequisite_check = None
if "prerequisite_response" not in st.session_state: st.session_state.prerequisite_response = None
if "navigator_active" not in st.session_state: st.session_state.navigator_active = False
if "current_course_structure" not in st.session_state: st.session_state.current_course_structure = None
if "current_page_map" not in st.session_state: st.session_state.current_page_map = None


# --- File Upload Section ---
uploaded_file = st.file_uploader("Upload your course PDF here:", type="pdf", key="fileuploader")

# Load LLM and Embedding Model (cached)
embedding_function = load_embedding_model()
llm = load_llm()

# --- Logic to process upload and set mode ---
if uploaded_file is not None:
    if uploaded_file.name != st.session_state.processed_file_name:
        st.info(f"Processing '{uploaded_file.name}'...")
        with st.spinner(f"Processing '{uploaded_file.name}'..."):
            st.session_state.vector_store = process_uploaded_pdf(uploaded_file)
            st.session_state.processed_file_name = uploaded_file.name
            if st.session_state.vector_store:
                st.session_state.rag_chain = create_rag_chain(st.session_state.vector_store, llm)
                st.session_state.uploaded_file_name = uploaded_file.name

                # Check if uploaded file matches predefined
                st.session_state.navigator_active = False
                st.session_state.current_course_structure = None
                st.session_state.current_page_map = None
                matched_course = None
                for course_name, course_data in PREDEFINED_COURSES.items():
                    # Ensure pdf_filename exists before comparing
                    if course_data.get("pdf_filename") == uploaded_file.name:
                        print(f"Uploaded file matches predefined course: {course_name}")
                        st.session_state.navigator_active = True
                        st.session_state.current_course_structure = course_data.get("structure")
                        st.session_state.current_page_map = course_data.get("page_map")
                        matched_course = course_name
                        # Basic validation of loaded structure/map
                        if not st.session_state.current_course_structure or not st.session_state.current_page_map:
                             print(f"Error: Structure or Page Map is missing for matched course '{course_name}' in PREDEFINED_COURSES.")
                             st.error(f"Configuration error for '{course_name}'. Navigator disabled.")
                             st.session_state.navigator_active = False
                        break

                greeting = f"Using '{uploaded_file.name}'. Ask me a question!" # Neutral message
                st.session_state.messages = [{"role": "assistant", "content": greeting}]
                st.session_state.current_question = None; st.session_state.prerequisite_check = None; st.session_state.prerequisite_response = None
                st.success(f"'{uploaded_file.name}' processed.")
                st.rerun()
            else:
                st.error("Failed to process uploaded PDF.")
                # Reset states
                st.session_state.vector_store = None; st.session_state.rag_chain = None; st.session_state.uploaded_file_name = None; st.session_state.processed_file_name = None; st.session_state.navigator_active = False; st.session_state.current_course_structure = None; st.session_state.current_page_map = None


elif uploaded_file is None and st.session_state.processed_file_name: # Handle file removal
     print("Uploaded file removed.")
     st.session_state.messages = [{"role": "assistant", "content": "Upload a PDF to start."}]
     # Reset all states
     st.session_state.vector_store = None; st.session_state.rag_chain = None; st.session_state.uploaded_file_name = None; st.session_state.processed_file_name = None; st.session_state.current_question = None; st.session_state.prerequisite_check = None; st.session_state.prerequisite_response = None; st.session_state.navigator_active = False; st.session_state.current_course_structure = None; st.session_state.current_page_map = None
     st.rerun()

# --- Display Context Caption ---
if st.session_state.rag_chain and st.session_state.uploaded_file_name:
     st.caption(f"Chatting with: '{st.session_state.uploaded_file_name}' - LLM: {LLM_MODEL_NAME}")
elif not uploaded_file:
     st.caption(f"LLM Model: {LLM_MODEL_NAME} - Upload a PDF to start")


# --- Chat Interface Section ---
if st.session_state.rag_chain:
    # --- (Affichage historique comme avant) ---
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # --- (Fonction get_rag_answer comme avant) ---
    def get_rag_answer(user_query, rag_chain_instance):
        # ... (code identique avec spinner, invoke, gestion erreur, debug print) ...
        if not rag_chain_instance: return "Error: RAG Chain not initialized.", []
        with st.spinner("Searching..."):
            try:
                response = rag_chain_instance.invoke({"query": user_query})
                answer = response.get("result", "Sorry, I couldn't find an answer.")
                source_docs = response.get("source_documents", [])
                if source_docs: st.write(f"DEBUG: Source 0 Meta: {source_docs[0].metadata}") # DEBUG
                else: st.write("DEBUG: No source docs.") # DEBUG
                return answer, source_docs
            except Exception as e:
                print(f"Error during RAG invoke: {e}", file=sys.stderr)
                st.error(f"An error occurred while generating the response.")
                return "Sorry, an error prevents me from responding.", []


    # User input area
    if prompt := st.chat_input("Your question here...", key="chat_input"):
        # --- (Affichage question user comme avant) ---
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)

        active_rag_chain = st.session_state.rag_chain

        # --- Logique pour prérequis OU réponse directe ---
        if st.session_state.prerequisite_check:
            # --- (Gestion réponse prérequis - identique à avant) ---
            # ... (code gestion réponse / skip) ...
             st.session_state.prerequisite_response = prompt
             prereq_section = st.session_state.prerequisite_check
             original_question = st.session_state.current_question
             response_content = ""
             if st.session_state.prerequisite_response.lower().strip() == 'skip':
                 response_content = f"Okay, skipping the check for '{prereq_section}'. Regarding '{original_question}':\n\n"
                 answer, _ = get_rag_answer(original_question, active_rag_chain)
                 response_content += answer
             else:
                 response_content = f"Okay, thanks for confirming about '{prereq_section}'. Now, regarding '{original_question}':\n\n"
                 answer, _ = get_rag_answer(original_question, active_rag_chain)
                 response_content += answer
             with st.chat_message("assistant"): st.markdown(response_content)
             st.session_state.messages.append({"role": "assistant", "content": response_content})
             st.session_state.current_question = None; st.session_state.prerequisite_check = None; st.session_state.prerequisite_response = None

        else:
            # Nouvelle question
            st.session_state.current_question = prompt
            answer, source_docs = get_rag_answer(prompt, active_rag_chain)

            preceding_section = None
            # *** CONDITIONAL NAVIGATOR LOGIC ***
            if st.session_state.get('navigator_active', False): # Check the flag
                current_page_map = st.session_state.get('current_page_map')
                current_course_structure = st.session_state.get('current_course_structure')

                if current_page_map and current_course_structure:
                    current_section = find_section_from_sources(source_docs, current_page_map)
                    st.write(f"DEBUG: Current Section: {current_section}") # DEBUG
                    if current_section and current_section in current_course_structure:
                        try:
                            current_index = current_course_structure.index(current_section)
                            if current_index > 0:
                                preceding_section = current_course_structure[current_index - 1]
                                st.write(f"DEBUG: Preceding Section: {preceding_section}") # DEBUG
                        except ValueError: pass
                else:
                     print("Warning: Navigator active but structure/map missing from session state.")
                     st.write("DEBUG: Navigator SHOULD be active but structure/map data missing!") # DEBUG


            if preceding_section: # Ask prerequisite question
                # ... (code identique pour poser la question) ...
                 st.session_state.prerequisite_check = preceding_section
                 active_file = st.session_state.uploaded_file_name or "the document"
                 assistant_message = f"Okay, the topic '{prompt}' seems related to section '{current_section}' in '{active_file}'. The previous section is '{preceding_section}'.\n\nTo ensure we're aligned, could you briefly summarize your understanding of '{preceding_section}'? (Or type 'skip')."
                 with st.chat_message("assistant"): st.markdown(assistant_message)
                 st.session_state.messages.append({"role": "assistant", "content": assistant_message})
            else: # No prerequisite check needed or navigator inactive
                # ... (code identique pour donner la réponse directe) ...
                 st.write(f"DEBUG: No preceding section or navigator inactive. Direct answer.") # DEBUG
                 with st.chat_message("assistant"): st.markdown(answer)
                 st.session_state.messages.append({"role": "assistant", "content": answer})
                 st.session_state.current_question = None

else:
    if not uploaded_file:
         st.info("Please upload a PDF document to begin.")