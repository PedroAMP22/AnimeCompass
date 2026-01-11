import streamlit as st
import requests
from llm_client import OllamaClient
from jikan_client import JikanClient 


st.set_page_config(page_title="AnimeCompass V2", layout="wide")

if "llm" not in st.session_state:
    st.session_state.llm = OllamaClient(model="llama3.2") 

if "messages" not in st.session_state:
    st.session_state.messages = []

if "excluded_animes" not in st.session_state:
    st.session_state.excluded_animes = []

if "total_likes" not in st.session_state:
    st.session_state.total_likes = 0  

if "total_recs" not in st.session_state:
    st.session_state.total_recs = 0   

def mark_as_seen(anime_name):
    if "excluded_animes" not in st.session_state:
        st.session_state.excluded_animes = []
    
    if anime_name not in st.session_state.excluded_animes:
        st.session_state.excluded_animes.append(anime_name)
        st.toast(f"👁️ Ocultado: {anime_name} (No saldrá más)")

def mark_as_liked():
    st.session_state.total_likes += 1

API_URL = "http://localhost:8000/execute/search_knowledge_graph"


with st.sidebar:
    st.header("📊 Panel de Evaluación")

    top_k_selector = st.slider("Nº de Recomendaciones", min_value=1, max_value=10, value=5)
    
    # Cálculo de Precisión
    if st.session_state.total_recs > 0:
        precision = (st.session_state.total_likes / st.session_state.total_recs) * 100
    else:
        precision = 0.0
        
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Likes ❤️", st.session_state.total_likes)
    with col2:
        st.metric("Vistos 👁️", st.session_state.total_recs)
    
    st.divider()
    st.metric("🎯 Precision Actual", f"{precision:.1f}%")
    if precision > 0:
        st.progress(min(precision / 100, 1.0))
    
    st.caption("Precision = Likes / Total Mostrados")
    
    if st.button("🗑️ Resetear Métricas"):
        st.session_state.total_likes = 0
        st.session_state.total_recs = 0
        st.session_state.excluded_animes = []
        st.rerun()

st.title("🧭 AnimeCompass V2")

# Historial
for msg_idx, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        # Si el mensaje tiene galería de imágenes guardada, la mostramos
        if "gallery" in msg and msg["gallery"]:
            cols = st.columns(len(msg["gallery"]))
            for idx, item in enumerate(msg["gallery"]):
                with cols[idx]:
                    st.image(item["image"], width="stretch")
                    st.caption(f"[{item['name']}]({item['url']})")
                    b1, b2 = st.columns(2)
                    with b1:
                        st.button("❤️", 
                                  key=f"h_like_{msg_idx}_{idx}", 
                                  help="Me gusta",
                                  on_click=mark_as_liked)
                    with b2:
                        st.button("👁️", 
                                  key=f"h_seen_{msg_idx}_{idx}", 
                                  help="Ya lo he visto",
                                  on_click=mark_as_seen,
                                  args=(item['name'],))
        
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
                        payload = {
                            "query": anime_name, 
                            "top_k": top_k_selector,
                            "exclude": st.session_state.excluded_animes # <--- Enviamos lo que ya hemos visto
                        }
                        res = requests.post(API_URL, json=payload)

                        results = res.json().get("results", [])
                        
                        if results:
                            st.session_state.total_recs += len(results)

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
                            status.update(label="No encontrado / Sin más resultados", state="error")
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
                        # Imagen y Título
                        st.image(item['image'], width="stretch")
                        st.caption(f"**{idx+1}. [{item['name']}]({item['url']})**")
                        st.progress(item['score'], text=f"Sim: {item['score']:.2f}")
                        
                        # Botones de Feedback
                        b1, b2 = st.columns(2)
                        with b1:
                            # Like (Feedback positivo)
                            if st.button("❤️", 
                                        key=f"like_{item['name']}_{len(st.session_state.messages)}", 
                                        help="Me gusta",
                                        on_click=mark_as_liked):
                                st.toast(f"¡Te gusta {item['name']}!")
                        
                        with b2:
                            # Seen (Feedback negativo / Ya visto)
                            # Usa on_click para actualizar estado inmediatamente
                            st.button("👁️", 
                                      key=f"seen_{item['name']}_{len(st.session_state.messages)}", 
                                      help="Ya lo he visto (No recomendar más)",
                                      on_click=mark_as_seen,
                                      args=(item['name'],))

        else:
            sys_prompt = "Responde como asistente normal."

        response_text = st.session_state.llm.chat(
            sys_prompt, 
            st.session_state.messages[:-1], 
            prompt
        )
        
        # --- GUARDADO FINAL ---
        # Aquí guardamos texto, galería Y LA TABLA (table_data)
        st.session_state.messages.append({
            "role": "assistant", 
            "content": response_text,
            "data": table_data, # <--- Se guarda aquí
            "gallery": gallery_data 
        })
        
        # --- RECARGA ---
        # Al recargar, el bucle del paso 4 pintará la tabla automáticamente
        st.rerun()