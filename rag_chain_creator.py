from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

def create_rag_chain(_db, _llm):
    if _db is None: return None
    print("Creating RAG chain...")
    retriever = _db.as_retriever(search_kwargs={'k': 5})
    prompt_template = """You are a helpful educational assistant. Your task is to answer questions about educational content based STRICTLY on the provided text snippets from the document.

Context information from the document is below:
{context}

ONLY using the context information above and NOT your general knowledge, answer the question:
{question}

Important guidelines:
1. ONLY use information found in the context snippets above
2. If the context doesn't contain the information needed, admit that you don't have enough information in the document
3. Do NOT use any knowledge outside of what's provided in the context snippets
4. Answer in a structured, educational way that helps the student understand the topic deeply
5. If the question asks for raw text or verbatim content, provide only the relevant sections from the context
6. If appropriate, include examples, analogies, or step-by-step explanations FROM THE DOCUMENT ONLY

Remember: You must ONLY use information from the provided context."""

    QA_CHAIN_PROMPT = PromptTemplate.from_template(prompt_template)
    qa_chain = RetrievalQA.from_chain_type(_llm, retriever=retriever, chain_type_kwargs={"prompt": QA_CHAIN_PROMPT}, return_source_documents=True)
    print("RAG chain created.")
    return qa_chain