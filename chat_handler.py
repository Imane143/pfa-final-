"""
chat_handler.py - Handle chat interface and conversation logic
"""
import streamlit as st
from session_manager import debug_log
from conversation_history import save_current_conversation
from prerequisite_handler import detect_prerequisites, explain_prerequisite
from pdf_processor import get_raw_document_text

def get_rag_answer(user_query, rag_chain_instance):
    """Get answer from RAG chain"""
    if not rag_chain_instance: 
        debug_log("Error: RAG Chain not initialized")
        return "Error: RAG Chain not initialized.", []
        
    is_raw = any(p in user_query.lower() for p in ["exact text", "verbatim", "raw text"])
    debug_log(f"Getting RAG answer for: {user_query[:50]}...")
    
    with st.spinner("Searching..."):
        try:
            response = rag_chain_instance.invoke({"query": user_query})
            answer = response.get("result", "Not found.")
            source_docs = response.get("source_documents", [])
            debug_log(f"RAG answer length: {len(answer)} chars, {len(source_docs)} sources")
            
            if is_raw: 
                debug_log("Raw document text requested")
                answer = get_raw_document_text(source_docs)
                
            return answer, source_docs
        except Exception as e: 
            debug_log(f"RAG Error: {e}")
            st.error("An error occurred.")
            return "Error processing your question.", []

def display_chat_messages():
    """Display the chat message history"""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

def display_prerequisite_toggle():
    """Display the prerequisite checking toggle"""
    prereq_toggle_key = "toggle_prereqs_" + str(hash(st.session_state.username))
    prereq_enabled = st.sidebar.checkbox(
        "Check for Prerequisites", 
        value=st.session_state.prereq_checkbox_state, 
        key=prereq_toggle_key
    )

    # Only update the state if it has changed
    if prereq_enabled != st.session_state.prereq_checkbox_state:
        debug_log(f"Prereq checkbox changed from {st.session_state.prereq_checkbox_state} to {prereq_enabled}")
        st.session_state.prereq_checkbox_state = prereq_enabled
        st.session_state.check_prereqs = prereq_enabled
        if prereq_enabled:
            st.success("Prerequisite checking enabled!")
        else:
            st.warning("Prerequisite checking disabled!")

def handle_chat_input():
    """Handle user chat input and responses"""
    # Always show the chat input, but provide different behavior based on state
    if prompt := st.chat_input("Your question here...", key="chat_input"):
        debug_log(f"New user input: {prompt[:50]}...")
        
        # Check if we have a RAG chain ready
        if not st.session_state.rag_chain:
            # Show error message if no RAG chain is available
            st.error("⚠️ Please upload a PDF document first or wait for processing to complete.")
            return
        
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): 
            st.markdown(prompt)

        active_rag_chain = st.session_state.rag_chain

        # Handle prerequisite responses vs new questions
        if st.session_state.waiting_for_prereq_response:
            _handle_prerequisite_response(prompt, active_rag_chain)
        else:
            _handle_new_question(prompt, active_rag_chain)
    
    # Show helpful message if no RAG chain but don't prevent input
    elif not st.session_state.rag_chain:
        if st.session_state.processed_file_name:
            st.info("📄 Document processed! You can now ask questions about the content.")
        elif not st.session_state.processed_file_name:
            st.info("📤 Please upload a PDF document to start chatting.")

def _handle_prerequisite_response(prompt, active_rag_chain):
    """Handle user response to prerequisite question"""
    debug_log("Processing response to prerequisite question")
    
    prereq_topic = st.session_state.prerequisite_topic
    original_question = st.session_state.current_question
    
    debug_log(f"Prereq topic: {prereq_topic}")
    debug_log(f"Original question: {original_question[:50]}...")
    
    # Process their answer (yes/no to explanation)
    if any(word in prompt.lower() for word in ["yes", "y", "sure", "ok", "okay", "explain", "please"]):
        debug_log("User wants prerequisite explanation")
        
        # User wants the explanation
        with st.spinner(f"Explaining {prereq_topic}..."):
            prereq_explanation = explain_prerequisite(prereq_topic, st.session_state.llm)
        
        with st.spinner("Answering original question..."):
            answer, _ = get_rag_answer(original_question, active_rag_chain)
        
        # Combine explanation with answer
        response_content = f"{prereq_explanation}\n\n{answer}"
    else: 
        debug_log("User skipped prerequisite explanation")
        
        # User skipped the explanation
        with st.spinner("Answering question..."):
            answer, _ = get_rag_answer(original_question, active_rag_chain)
        response_content = answer
    
    # Display the answer
    with st.chat_message("assistant"): 
        st.markdown(response_content)
    
    # Add to message history
    st.session_state.messages.append({
        "role": "assistant", 
        "content": response_content
    })
    
    # Save conversation
    save_current_conversation(st.session_state.username)
    
    # Reset prerequisite state variables
    debug_log("Resetting prerequisite state variables")
    st.session_state.waiting_for_prereq_response = False
    st.session_state.current_question = None
    st.session_state.prerequisite_topic = None
    st.session_state.check_prereqs = st.session_state.prereq_checkbox_state
    debug_log(f"check_prereqs set to {st.session_state.check_prereqs}")

def _handle_new_question(prompt, active_rag_chain):
    """Handle a new question from the user"""
    debug_log("Processing new question")
    
    # Save the current question
    st.session_state.current_question = prompt
    debug_log(f"Current question set to: {prompt[:50]}...")
    
    # Log the current state of check_prereqs
    debug_log(f"check_prereqs is currently: {st.session_state.check_prereqs}")
    
    # Check for prerequisites ONLY if check_prereqs is True
    prereq_topic = None
    if st.session_state.check_prereqs:
        debug_log("Checking for prerequisites...")
        prereq_topic = detect_prerequisites(prompt, st.session_state.llm)
        debug_log(f"Prerequisite detection result: {prereq_topic}")
        
        # Skip if we've already explained this prerequisite
        if prereq_topic and prereq_topic in st.session_state.prereq_history:
            debug_log(f"Prerequisite '{prereq_topic}' already explained, skipping")
            prereq_topic = None
    else:
        debug_log("Prerequisite checking disabled, skipping detection")
    
    if prereq_topic:
        debug_log(f"Valid prerequisite found: {prereq_topic}")
        
        # Found a valid prerequisite to explain
        st.session_state.prereq_history.add(prereq_topic)
        debug_log(f"Added '{prereq_topic}' to prereq_history")
        
        # Set up for handling the response
        st.session_state.prerequisite_topic = prereq_topic
        st.session_state.waiting_for_prereq_response = True
        debug_log("Set waiting_for_prereq_response to True")
        
        # Ask if they want an explanation
        prereq_message = (
            f"Before answering your question about {prompt[:30]}{'...' if len(prompt) > 30 else ''}, "
            f"I think you should understand the concept of **{prereq_topic}** first. "
            f"Would you like me to explain this concept? (yes/skip)"
        )
        
        # Display question and save to history
        with st.chat_message("assistant"): 
            st.markdown(prereq_message)
        
        st.session_state.messages.append({
            "role": "assistant", 
            "content": prereq_message
        })
        
        save_current_conversation(st.session_state.username)
    else:
        debug_log("No prerequisite needed or detected")
        
        # No prerequisite needed - answer directly
        with st.spinner("Searching for answer..."):
            answer, _ = get_rag_answer(prompt, active_rag_chain)
        
        debug_log("Got direct answer, displaying")
        
        # Display and save the direct answer
        with st.chat_message("assistant"): 
            st.markdown(answer)
        
        st.session_state.messages.append({
            "role": "assistant", 
            "content": answer
        })
        
        save_current_conversation(st.session_state.username)
        
        # Reset question state but preserve check_prereqs flag
        st.session_state.current_question = None
        debug_log("Reset current_question to None")

def display_context_caption():
    """Display context information about the current session"""
    if st.session_state.rag_chain and st.session_state.processed_file_name:
        st.caption(f"Chatting with: '{st.session_state.processed_file_name}' - LLM: gemini-1.5-flash")
    elif not st.session_state.processed_file_name:
        st.caption(f"LLM: gemini-1.5-flash - Upload PDF to start or select history.")