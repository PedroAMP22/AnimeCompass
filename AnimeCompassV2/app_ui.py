import streamlit as st
import requests
from llm_client import OllamaClient
# IMPORTAMOS EL NUEVO CLIENTE
from jikan_client import JikanClient 

API_URL = "http://localhost:8000/execute/search_knowledge_graph"

st.set_page_config(page_title="AnimeCompass V2", layout="wide")
st.title("🧭 AnimeCompass V2")

if "llm" not in st.session_state:
    st.session_state.llm = OllamaClient(model="llama3.2") 

if "messages" not in st.session_state:
    st.session_state.messages = []

# Historial
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        # Si el mensaje tiene galería de imágenes guardada, la mostramos
        if "gallery" in msg and msg["gallery"]:
            cols = st.columns(len(msg["gallery"]))
            for idx, item in enumerate(msg["gallery"]):
                with cols[idx]:
                    st.image(item["image"], use_container_width=True)
                    st.caption(f"[{item['name']}]({item['url']})")
        
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
        gallery_data = [] # Lista para guardar las imágenes
        
        # 1. Router
        if st.session_state.llm.should_use_tool(prompt):
            
            with st.status("Procesando solicitud y descargando imágenes...", expanded=True) as status:
                st.write("🧠 Detectando intención... (Anime)")
                anime_name = st.session_state.llm.extract_anime_name(prompt)
                
                if anime_name and anime_name != "NULL":
                    st.write(f"🔍 Buscando en grafo: **{anime_name}**")
                    
                    try:
                        res = requests.post(API_URL, json={"query": anime_name, "top_k": 5})
                        results = res.json().get("results", [])
                        
                        if results:
                            context = ""
                            
                            # FASE DE CARGA (Aquí solo descargamos datos, NO dibujamos)
                            for i, r in enumerate(results):
                                st.write(f"🖼️ Buscando carátula para: {r['name']}...")
                                
                                # Llamamos a Jikan
                                jikan_data = JikanClient.get_anime_info(r['name'])
                                
                                # Guardamos en la lista
                                gallery_data.append({
                                    "name": r['name'],
                                    "image": jikan_data['image_url'],
                                    "url": jikan_data['url'],
                                    "score": r['score'],
                                    "details": r['details']
                                })

                                # Texto para el LLM
                                context += f"""
                                === RANKING #{i+1} ===
                                - ANIME: {r['name']}
                                  * Score: {r['score']:.3f}
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
                            
                            table_data = results
                            
                            # CERRAMOS EL STATUS VISUALMENTE
                            status.update(label="¡Análisis completado!", state="complete", expanded=False)
                            
                        else:
                            status.update(label="No encontrado en DB", state="error")
                            sys_prompt = f"No encontré '{anime_name}' en la base de datos."
                    
                    except Exception as e:
                        status.update(label="Error de conexión", state="error")
                        sys_prompt = f"Error técnico: {e}"
                else:
                    status.update(label="No entendí el nombre", state="error")
                    sys_prompt = "Pide al usuario que especifique el anime."
                    
            if gallery_data:
                st.write("---")
                st.subheader(f"Recomendaciones para: {anime_name}")
                
                cols = st.columns(len(gallery_data))
                for idx, item in enumerate(gallery_data):
                    with cols[idx]:
                        st.markdown(f"[![Imagen]({item['image']})]({item['url']})")
                        st.caption(f"**{idx+1}. {item['name']}**")
                        st.progress(item['score'], text=f"{item['score']:.2f}")

        else:
            sys_prompt = "Responde como asistente normal."

        # 2. Generar respuesta de texto
        response_text = st.session_state.llm.prompt(sys_prompt, prompt)
        st.markdown(response_text)
        
        if table_data:
            with st.expander("📊 Desglose Matemático"):
                st.dataframe(table_data)

    # 3. Guardar en historial con la galería
    st.session_state.messages.append({
        "role": "assistant", 
        "content": response_text,
        "data": table_data,
        "gallery": gallery_data # <--- Guardamos las imágenes aquí
    })