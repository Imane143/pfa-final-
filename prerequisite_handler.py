import streamlit as st

def detect_prerequisites(query, llm):
    if not llm: return None
    print(f"DEBUG: Detecting prerequisites for: {query}")
    prompt = """Examine the following question related to educational content. Based on the question, determine if there's a prerequisite topic that the student likely needs to understand first before comprehending the answer. 

Question: "{query}"

First, analyze what topics are directly asked about in the question. Then, determine the most fundamental concept that is DIRECTLY RELATED to this question and is necessary to understand before the original question can be properly understood.

Important rules:
1. The prerequisite MUST be closely and directly related to the original question
2. The prerequisite should be specific, not general (e.g. "quadratic equations" not "mathematics")
3. Do not suggest basic concepts unless the question is actually about a complex topic building on them
4. If the question is already about a fundamental concept, return the exact string "None"
5. DO NOT include any words like "Prerequisite:" in your response, just give the topic name or "None"

Examples of good outputs:
- linear equations
- force and mass concepts
- cellular respiration
- None

Output ONLY the prerequisite topic name or "None". Keep it concise - max 5 words."""

    try:
        response = llm.invoke(prompt.format(query=query))
        response_text = response.content.strip()
        print(f"DEBUG (detect_prereq response): {response_text}")
        
        # Clean up response to handle cases where model outputs "Prerequisite: None"
        response_text = response_text.replace("Prerequisite:", "").strip()
        
        # Return None if the response is "None" or empty
        if response_text.lower() == "none" or not response_text:
            print("DEBUG: No prerequisite needed")
            return None
        
        # Filter out non-prerequisites
        low_value_prereqs = ["basic", "fundamental", "introduction", "concept", "definition"]
        if any(term in response_text.lower() for term in low_value_prereqs) and len(response_text.split()) <= 2:
            print(f"DEBUG: Low value prerequisite filtered out: {response_text}")
            return None
            
        print(f"DEBUG: Prerequisite detected: {response_text}")
        return response_text
    except Exception as e: 
        print(f"Error detecting prerequisites: {e}")
        return None

def explain_prerequisite(topic, llm):
    if not topic or not llm: return f"Couldn't find info: '{topic}'."
    print(f"DEBUG: Explaining prerequisite: {topic}")
    
    prompt = f"""Provide a clear, concise explanation of '{topic}' suitable for a student who needs this information as background knowledge. 

Important: Use ONLY your general knowledge for this explanation. Do NOT refer to any document or PDF content.

The explanation should:
1. Define what '{topic}' is in simple terms
2. Explain why it's important or useful for understanding related concepts
3. Include 1-2 simple examples if applicable
4. Be educational and suitable for a student

Keep the explanation under 200 words, focusing on clarity and helpfulness. 
Remember to ONLY use your general knowledge, not information from any document."""

    try:
        response = llm.invoke(prompt)
        explanation = response.content
        return f"*Prerequisite: {topic}*\n\n{explanation}\n\n---\n\nNow, about your original question:"
    except Exception as e: 
        print(f"Error explaining prerequisite: {e}")
        return f"Error explaining '{topic}'."