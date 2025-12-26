import streamlit as st
import requests
from llm_client import OllamaClient

API_URL = "http://localhost:8000/execute/search_knowledge_graph"

st.set_page_config(page_title="AnimeCompass V2", layout="wide")
st.title("🧭 AnimeCompass V2 (Híbrido)")

if "llm" not in st.session_state:
    st.session_state.llm = OllamaClient(model="llama3.2") 

if "messages" not in st.session_state:
    st.session_state.messages = []

# Historial
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "data" in msg and msg["data"]:
            with st.expander("Ver desglose de puntuación"):
                st.table(msg["data"])

# Input
if prompt := st.chat_input("Ej: Algo parecido a Evangelion"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        response_text = ""
        table_data = []
        
        # 1. Router
        if st.session_state.llm.should_use_tool(prompt):
            
            # --- NUEVO PASO: EXTRACCIÓN DE ENTIDAD ---
            with st.status("Procesando solicitud...", expanded=True) as status:
                st.write("🧠 Detectando intención... (Anime)")
                
                # Extraemos el nombre limpio (Ej: "Bleach")
                anime_name = st.session_state.llm.extract_anime_name(prompt)
                
                if anime_name and anime_name != "NULL":
                    st.write(f"🔍 Buscando en grafo: **{anime_name}**")
                    
                    try:
                        # LLAMAMOS A LA API CON EL NOMBRE LIMPIO, NO CON LA FRASE ENTERA
                        res = requests.post(API_URL, json={"query": anime_name, "top_k": 5})
                        results = res.json().get("results", [])
                        
                        if results:
                            status.update(label="¡Datos encontrados!", state="complete", expanded=False)
                            
                            context = ""
                            for i, r in enumerate(results):
                                context += f"""
                                === RANKING #{i+1} ===
                                - ANIME: {r['name']}
                                  * Score: {r['score']:.3f}
                                  * TransR: {r['transr']:.3f}
                                  * Heurística: {r['heuristic']:.3f}
                                  * Detalles: {r['details']}
                                """
                            
                            sys_prompt = f"""
                            Actúa como un experto en anime amigable y conocedor. Acabas de consultar nuestra base de datos de similitud y tienes los resultados listos.
                            
                            TUS INSTRUCCIONES:
                            1. **El Orden es Clave:** Recomienda los animes en el orden exacto que te doy abajo (del #1 al #5). El #1 es la recomendación estrella.
                            2. **Tono Natural:** No hables como un robot ("Basado en los datos..."). Habla como un fan recomendando a otro fan. Usa frases como: "Tengo unas recomendaciones geniales", "Lo más parecido que he encontrado es...", "Si te gusta ese estilo, tienes que ver...".
                            3. **Argumenta:** Usa los detalles (géneros, año, etc.) para explicar por qué se parecen, pero no hace falta que digas los números exactos (ya salen en la tabla). Di cosas como "tiene una ambientación muy similar" o "coinciden mucho en los géneros de acción".
                            4. **Fidelidad:** Solo recomienda los animes de la lista.
                            
                            LISTA DE RECOMENDACIONES (ORDENADA):
                            {context}
                            
                            Responde al usuario de forma fluida, empezando por la mejor opción.
                            """
                            
                            table_data = [{
                                "Anime": r["name"],
                                "Total": f"{r['score']:.3f}",
                                "TransR (80%)": f"{r['transr']:.3f}",
                                "Heurística (20%)": f"{r['heuristic']:.3f}"
                            } for r in results]
                            
                        else:
                            status.update(label="No encontrado en DB", state="error")
                            sys_prompt = f"El usuario preguntó por '{anime_name}' pero no está en nuestra base de datos local. Dilo amablemente y ofrece hablar de otra cosa."
                    
                    except Exception as e:
                        status.update(label="Error de conexión", state="error")
                        sys_prompt = "Error técnico conectando al servidor."
                else:
                    status.update(label="No entendí el nombre del anime", state="error")
                    sys_prompt = "El usuario quiere recomendaciones pero no detecté un nombre de anime concreto. Pídele que especifique."

        else:
            sys_prompt = "Responde como un asistente normal."

        # 2. Generar respuesta
        response_text = st.session_state.llm.prompt(sys_prompt, prompt)
        st.markdown(response_text)
        
        if table_data:
            with st.expander("📊 Desglose Matemático"):
                st.table(table_data)

    st.session_state.messages.append({
        "role": "assistant", 
        "content": response_text,
        "data": table_data
    })