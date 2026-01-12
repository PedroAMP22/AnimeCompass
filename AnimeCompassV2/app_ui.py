import streamlit as st
import requests
from llm_client import OllamaClient
from jikan_client import JikanClient 

# --- CONFIGURACIÓN Y ESTADO ---
st.set_page_config(page_title="AnimeCompass V2", layout="wide", page_icon="🧭")

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
    "sesiones_con_feedback": set()
}

for key, value in init_states.items():
    if key not in st.session_state:
        st.session_state[key] = value

# --- FUNCIONES DE FEEDBACK ---
def mark_as_disliked(anime_name):
    if anime_name not in st.session_state.ya_interactuado:
        st.session_state.excluded_animes.append(anime_name)
        st.session_state.ya_interactuado.add(anime_name)
        st.toast(f"👎 Ocultando: {anime_name}")

def mark_as_liked(anime_name, rank, msg_idx):
    """
    rank: posición en la lista (1, 2, 3...)
    msg_idx: identificador de la búsqueda para no duplicar MRR
    """
    if anime_name not in st.session_state.ya_interactuado:
        # Lógica de MRR: Solo cuenta el primer Like de cada bloque de recomendación
        if msg_idx not in st.session_state.sesiones_con_feedback:
            reciprocal_rank = 1.0 / rank
            st.session_state.rr_sum += reciprocal_rank
            st.session_state.queries_con_like += 1
            st.session_state.sesiones_con_feedback.add(msg_idx)
            
        st.session_state.total_likes += 1
        st.session_state.ya_interactuado.add(anime_name)
        st.toast(f"❤️ ¡Añadido a favoritos! (Rank: {rank})")

# --- SIDEBAR (MÉTRICAS) ---
with st.sidebar:
    st.header("📊 Panel de Control")
    top_k_selector = st.slider("Nº de Recomendaciones", 1, 10, 5)
    
    st.divider()
    st.subheader("📈 Calidad (IR Metrics)")
    
    # 1. User Precision
    precision = (st.session_state.total_likes / st.session_state.total_recs * 100) if st.session_state.total_recs > 0 else 0
    st.metric("🎯 User Precision", f"{precision:.1f}%", help="Porcentaje total de likes sobre recomendaciones mostradas.")
    
    # 2. MRR (Mean Reciprocal Rank)
    mrr = (st.session_state.rr_sum / st.session_state.queries_con_like) if st.session_state.queries_con_like > 0 else 0
    st.metric("🏆 MRR", f"{mrr:.3f}", help="Mide qué tan arriba aparecen los animes que te gustan. 1.0 es perfecto.")
    st.progress(min(mrr, 1.0))

    # 3. Confianza del Grafo
    last_msg = next((m for m in reversed(st.session_state.messages) if "data" in m and m["data"]), None)
    if last_msg:
        avg_score = sum(item.get('score', 0) for item in last_msg["data"]) / len(last_msg["data"])
        st.metric("🔗 Confianza Grafo", f"{avg_score:.3f}")

    st.divider()
    if st.button("🗑️ Reiniciar Sesión", width='stretch'):
        for key in init_states.keys():
            if key == "ya_interactuado": st.session_state[key] = set()
            elif key == "sesiones_con_feedback": st.session_state[key] = set()
            else: st.session_state[key] = init_states[key]
        st.rerun()

# --- INTERFAZ PRINCIPAL ---
st.title("🧭 AnimeCompass V2")
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
if prompt := st.chat_input("Ej: Recomiéndame algo oscuro como Death Note"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    with st.chat_message("assistant"):
        table_data = []
        gallery_data = []
        sys_prompt = "Responde amigablemente como un experto en anime."

        # 1. Router y Extracción
        if st.session_state.llm.should_use_tool(prompt):
            with st.status("Consultando Grafo de Conocimiento...", expanded=True) as status:
                anime_name = st.session_state.llm.extract_anime_name(prompt)
                
                if anime_name and anime_name != "NULL":
                    try:
                        API_URL = "http://localhost:8000/execute/search_knowledge_graph"
                        payload = {
                            "query": anime_name, 
                            "top_k": top_k_selector,
                            "exclude": st.session_state.excluded_animes
                        }
                        res = requests.post(API_URL, json=payload, timeout=60)
                        results = res.json().get("results", [])

                        if results:
                            st.session_state.total_recs += len(results)
                            table_data = results
                            context_text = ""
                            
                            for r in results:
                                status.write(f"🎞️ Obteniendo info de: {r['name']}")
                                jikan = JikanClient.get_anime_info(r['name'])
                                gallery_data.append({
                                    "name": r['name'],
                                    "image": jikan['image_url'],
                                    "url": jikan['url'],
                                    "score": r['score']
                                })
                                context_text += f"- {r['name']}: {r['details']}\n"

                            sys_prompt = f"""Actúa como experto. Recomienda estos animes en orden:
                            {context_text}
                            Usa un tono entusiasta y justifica por qué se parecen al original."""
                            status.update(label="¡Recomendaciones listas!", state="complete", expanded=False)
                        else:
                            status.update(label="No encontré resultados similares.", state="error")
                    except Exception as e:
                        status.update(label=f"Error de conexión: {e}", state="error")
                else:
                    status.update(label="No pude identificar un anime en tu mensaje.", state="error")

        # 2. Generación de Respuesta
        full_response = st.session_state.llm.chat(sys_prompt, st.session_state.messages[:-1], prompt)
        st.markdown(full_response)
        
        # 3. Guardado en historial
        st.session_state.messages.append({
            "role": "assistant",
            "content": full_response,
            "data": table_data,
            "gallery": gallery_data
        })
        
        st.rerun()