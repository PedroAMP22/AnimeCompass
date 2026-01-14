
# Módulo: Interfaz de Usuario (Frontend)
# Descripción: Aplicación principal construida con Streamlit. Gestiona la sesión del usuario,
# el chat interactivo, la visualización de recomendaciones y la comunicación con el servidor API.

import streamlit as st
import requests
from llm_client import OllamaClient
from jikan_client import JikanClient 

# --- CONFIGURACIÓN Y ESTADO ---
st.set_page_config(page_title="AnimeCompass V2", layout="wide", page_icon="🧭")


API_URL = "http://localhost:8000/"

# Inicialización de estado
init_states = {
    "llm": OllamaClient(model="llama3.2"),
    "messages": [],
    "excluded_animes": [],
    "total_likes": 0,
    "total_recs": 0,
    "ya_interactuado": set(),
    "rr_sum": 0.0,   
    "queries_con_like": 0,
    "sesiones_con_feedback": set(),
    "mrr": 0,
}
# --- TOP NAVIGATION BAR ---
col_title, col_btn = st.columns([3, 1])
with col_title:
    st.title("🧭 AnimeCompass V2")

for key, value in init_states.items():
    if key not in st.session_state:
        st.session_state[key] = value

# --- FUNCIONES DE FEEDBACK ---
def mark_as_disliked(anime_name):
    if anime_name not in st.session_state.ya_interactuado:
        # Guardar en base de datos local (memoria)
        st.session_state.excluded_animes.append(anime_name)
        st.session_state.ya_interactuado.add(anime_name)
        
        # Guardar en base de datos REAL (API)
        if "user_nick" in st.session_state:
            try:
                payload = {"nick": st.session_state.user_nick, "anime_name": anime_name}
                requests.post(f"{API_URL}/user/dislike", json=payload)
            except:
                pass
        
        st.toast(f"👎 Ocultando: {anime_name}")

def mark_as_liked(anime_name, rank, msg_idx):
    if anime_name not in st.session_state.ya_interactuado:
        # Lógica de métricas (MRR)
        if msg_idx not in st.session_state.sesiones_con_feedback:
            reciprocal_rank = 1.0 / rank
            st.session_state.rr_sum += reciprocal_rank
            st.session_state.queries_con_like += 1
            st.session_state.sesiones_con_feedback.add(msg_idx)

            if st.session_state.queries_con_like > 0:
                st.session_state.mrr = st.session_state.rr_sum / st.session_state.queries_con_like
            
        st.session_state.total_likes += 1
        st.session_state.ya_interactuado.add(anime_name)
        
        # Guardar en base de datos REAL (API)
        if "user_nick" in st.session_state:
            try:
                payload = {"nick": st.session_state.user_nick, "anime_name": anime_name, "mrr": st.session_state.mrr }
                requests.post(f"{API_URL}/user/like", json=payload)
            except:
                pass

        st.toast(f"❤️ ¡Añadido a favoritos! (Rank: {rank})")

# Comentarios
@st.dialog("Reviews de la Comunidad")
def show_review_modal():
    # Publicar comentario
    st.subheader("Publica tu review")
    new_comment = st.text_area("¿Que piensas de Anime Compass?", height=100) 
    if st.button("Enviar"):
        if "user_nick" in st.session_state:
            payload = {"nick": st.session_state.user_nick, "comment": new_comment} 
            try:
                requests.post(API_URL + "reviews/add", json=payload)
                st.toast("Review enviada")
            except:
                st.error("Server offline")

    st.divider()

    # Comentarios publicados
    st.subheader("Lo que opina nuestra comunidad")
    try:
        response = requests.get(API_URL + "reviews").json()
        reviews_list = response.get("reviews", [])

        for review in reversed(reviews_list):
            user = review["nick"]
            content = review["text"]
            
            with st.chat_message("user"):
                st.write(f"**{user}** dice:")
                st.write(content.strip())
    except:
        st.write("No hay nada. ¡Se el primero!")

    if st.button("Close"):
        st.rerun()


# --- LOGIN ----
if "user_nick" not in st.session_state:
    with st.form("login_form"):
        nick = st.text_input("Introduce tu nickname: ")
        if st.form_submit_button("Login / Register"):
            if nick:
                try:
                    response = requests.post(f"{API_URL}/user/add", json={"nick": nick, "comment": ""})
                    response.raise_for_status()
                    res_data = response.json()
                    
                    # --- CARGAR HISTORIAL DEL USUARIO ---
                    st.session_state.user_nick = nick
                    
                    # Si el usuario ya tenía dislikes, los cargamos para que el motor los use
                    user_info = res_data.get("data", {})
                    past_dislikes = user_info.get("disliked_animes", [])
                    st.session_state.excluded_animes = past_dislikes
                    
                    # También marcamos como interactuados para que no salgan botones de nuevo
                    past_likes = user_info.get("likes", [])
                    st.session_state.ya_interactuado = set(past_dislikes + past_likes)
                    st.session_state.total_likes = len(past_likes)

                    # Cargamos las métricas
                    st.session_state.mrr = user_info.get("mrr", 0)
                    st.session_state.total_recs = user_info.get("total_animes", 0)
                    # ------------------------------------

                    st.rerun()
                except Exception as e:
                    st.error(f"Error de conexión: {e}")
            else:
                st.error("Por favor, introduce tu nick.")
    st.stop()

with col_btn:
    if st.button("💬 Open Reviews", width="stretch"):
        show_review_modal()

# --- SIDEBAR (MÉTRICAS) ---
with st.sidebar:
    st.header(f"👤 Bienvenido, {st.session_state.user_nick}")
    if st.button("Logout / Change Nick", width="stretch"):
        # Eliminamos la identidad
        if "user_nick" in st.session_state:
            del st.session_state.user_nick
        
        # Reiniciamos todas las variables de estado a sus valores originales
        for key, value in init_states.items():
            if isinstance(value, list):
                st.session_state[key] = []
            elif isinstance(value, set):
                st.session_state[key] = set()
            else:
                st.session_state[key] = value
                
        # Forzamos el reinicio para volver a la pantalla de login
        st.rerun()

    st.divider()
    
    st.header("📊 Panel de Control")
    top_k_selector = st.slider("Nº de Recomendaciones", 1, 10, 5)
    
    st.divider()
    st.subheader("📈 Calidad (IR Metrics)")
    
    # 1. User Precision
    precision = (st.session_state.total_likes / st.session_state.total_recs * 100) if st.session_state.total_recs > 0 else 0
    st.metric("🎯 User Precision", f"{precision:.1f}%", help="Porcentaje total de likes sobre recomendaciones mostradas.")
    
    # 2. MRR (Mean Reciprocal Rank)
    st.session_state.mrr = (st.session_state.rr_sum / st.session_state.queries_con_like) if st.session_state.queries_con_like > 0 else st.session_state.mrr
    st.metric("🏆 MRR", f"{st.session_state.mrr:.3f}", help="Mide qué tan arriba aparecen los animes que te gustan. 1.0 es perfecto.")
    st.progress(min(st.session_state.mrr, 1.0))

    # 3. Confianza del Grafo
    last_msg = next((m for m in reversed(st.session_state.messages) if "data" in m and m["data"]), None)
    if last_msg:
        avg_score = sum(item.get('score', 0) for item in last_msg["data"]) / len(last_msg["data"])
        st.metric("🔗 Confianza Grafo", f"{avg_score:.3f}")

    st.divider()
    if st.button("🗑️ Reiniciar Usuario", width='stretch'):
        for key in init_states.keys():
            if key == "ya_interactuado": st.session_state[key] = set()
            elif key == "sesiones_con_feedback": st.session_state[key] = set()
            else: st.session_state[key] = init_states[key]
        
        payload = {"nick": st.session_state.user_nick,  "comment": ""}
        requests.post(f"{API_URL}/user/reset", json=payload)

        st.rerun()
        

# --- INTERFAZ PRINCIPAL ---
st.info("Recomendaciones de anime utilizando Inteligencia Artificial y Grafos de Conocimiento.")

# Renderizado de Historial
for msg_idx, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        
        # Mostrar Galería si existe
        if "gallery" in msg and msg["gallery"]:
            cols = st.columns(len(msg["gallery"]))
            for idx, item in enumerate(msg["gallery"]):
                with cols[idx]:
                    st.image(item["image"], width='stretch')
                    st.caption(f"**{item['name']}**")
                    
                    # Estado del botón
                    interactuado = item['name'] in st.session_state.ya_interactuado
                    b1, b2 = st.columns(2)
                    
                    # Botón Like
                    b1.button("❤️", key=f"lk_{msg_idx}_{idx}", 
                              on_click=mark_as_liked, 
                              args=(item['name'], idx + 1, msg_idx),
                              disabled=interactuado)
                    
                    # Botón Dislike
                    b2.button("👎", key=f"dk_{msg_idx}_{idx}", 
                              on_click=mark_as_disliked, 
                              args=(item['name'],),
                              disabled=interactuado)
        
        # Mostrar desglose técnico
        if "data" in msg and msg["data"]:
            with st.expander("Detalles técnicos del Grafo"):
                st.table(msg["data"])

# --- LÓGICA DE ENTRADA ---
if prompt := st.chat_input("Ej: Algo parecido a Evangelion"):
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        response_text = ""
        table_data = []
        gallery_data = [] 

        # 1. Router 
        if st.session_state.llm.should_use_tool(prompt):

            with st.status("Procesando solicitud y descargando imágenes...", expanded=True) as status:
                st.write("🧠 Detectando intención... (Anime)")
                anime_name = st.session_state.llm.extract_anime_name(prompt)
                results = []
                if anime_name and anime_name != "NULL":
                    st.write(f"🔍 Calculando similitud para: **{anime_name}**")
                    try:
                        payload = {
                            "nick": st.session_state.user_nick,
                            "query": anime_name, 
                            "top_k": top_k_selector,
                            "exclude": st.session_state.excluded_animes
                        }
                        res = requests.post(API_URL + "execute/search_knowledge_graph", json=payload)
                        results = res.json().get("results", [])
                    except Exception as e:
                        status.update(label=f"Error de conexión: {e}", state="error")
                else:
                    status.update(label="No pude identificar un anime en tu mensaje.", state="error")

                # 2. Configuramos la salida según los resultados
                if results:
                    st.session_state.total_recs += len(results)
                    table_data = results
                    context = ""
                    
                    for i, r in enumerate(results):
                        status.write(f"🎞️ Obteniendo carátula para: {r['name']}")
                        jikan = JikanClient.get_anime_info(r['name'])
                        gallery_data.append({
                            "name": r['name'],
                            "image": jikan['image_url'],
                            "url": jikan['url'],
                            "score": r['score'],
                            "details": r['details']
                        })
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

                    status.update(label="¡Análisis completado!", state="complete", expanded=False)
                else:
                    status.update(label="No encontré resultados similares.", state="error")

                if gallery_data:
                    st.write("---")
                    st.subheader(f"Recomendaciones para: {anime_name}")
                    
                    cols = st.columns(len(gallery_data))
                    for idx, item in enumerate(gallery_data):
                        with cols[idx]:
                            st.image(item['image'], width="stretch")
                            st.caption(f"**{idx+1}. [{item['name']}]({item['url']})**")
                            st.progress(item['score'], text=f"Sim: {item['score']:.2f}")
                
        else:
            sys_prompt = "Responde como asistente normal."

        # Generación de Respuesta
        response_text = st.session_state.llm.chat(
            sys_prompt, 
            st.session_state.messages[:-1], 
            prompt
        )  
        
        # 3. Guardado en historial
        st.session_state.messages.append({
            "role": "assistant",
            "content": response_text,
            "data": table_data,
            "gallery": gallery_data
        })

        st.rerun()