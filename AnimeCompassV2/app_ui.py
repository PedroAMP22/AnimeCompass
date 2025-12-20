import streamlit as st
import requests
import json
from llm_client import OllamaClient

st.title("📺 Anime KG Chatbot")

if "llm" not in st.session_state:
    st.session_state.llm = OllamaClient(model="llama3.2")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ej: Recomiéndame algo parecido a Naruto"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # 1. Consultar tu motor TransR
        with st.spinner("Buscando en el Knowledge Graph..."):
            res = requests.post("http://localhost:8000/execute/search_knowledge_graph", 
                                json={"query": prompt, "top_k": 3})
            kg_data = res.json().get("results", [])

        # 2. Construir contexto para el LLM
        context = "Resultados encontrados en el Grafo de Conocimiento:\n"
        for item in kg_data:
            context += f"- {item['name']} (Similitud: {item['score']:.2f}). Info: {item['details']}\n"

        system_prompt = f"""
        Eres un recomendador de anime experto. Usa estos datos de nuestro Knowledge Graph 
        para responder. Los datos vienen de un modelo TransR de grafos.
        Contexto: {context}
        """

        response = st.session_state.llm.prompt(system_prompt, prompt)
        st.markdown(response)
        
        with st.expander("Ver razonamiento del Grafo"):
            st.json(kg_data)

    st.session_state.messages.append({"role": "assistant", "content": response})