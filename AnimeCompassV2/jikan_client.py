
# Módulo: Cliente Jikan API (MyAnimeList)
# Descripción: Cliente para consultar la API pública de Jikan. Se utiliza para enriquecer
# las recomendaciones obteniendo imágenes oficiales, URLs y metadatos actualizados.

import requests
import streamlit as st
import time

class JikanClient:
    BASE_URL = "https://api.jikan.moe/v4/anime"

    @staticmethod
    @st.cache_data(ttl=86400, show_spinner=False)
    def get_anime_info(anime_name):
        """
        Busca un anime por nombre.
        MEJORA: Limpia guiones bajos y añade logs de depuración.
        """
        # 1. LIMPIEZA DEL NOMBRE
        clean_name = str(anime_name).replace("_", " ").strip()
        
        print(f"\n[JIKAN] Buscando imagen para: '{clean_name}' (Original: '{anime_name}')")

        try:
            # Pausa para evitar Rate Limit (429)
            time.sleep(0.35) 
            
            params = {"q": clean_name, "limit": 1}
            response = requests.get(JikanClient.BASE_URL, params=params, timeout=5)
            
            # Debug del estado HTTP
            if response.status_code != 200:
                print(f"WARNING [JIKAN] Error HTTP {response.status_code} para '{clean_name}'")

            if response.status_code == 200:
                data = response.json().get("data", [])
                if data:
                    anime = data[0]
                    found_title = anime["title"]
                    print(f"CORRECT [JIKAN] Encontrado: '{found_title}' (Match para '{clean_name}')")
                    
                    return {
                        "image_url": anime["images"]["jpg"]["large_image_url"], # Usamos 'large' para mejor calidad
                        "url": anime["url"],
                        "title": found_title
                    }
                else:
                    print(f"ERROR [JIKAN] La API respondió OK pero sin resultados para: '{clean_name}'")
            
            # Si fallamos, devolvemos placeholder
            return {
                "image_url": "https://dummyimage.com/225x320/000/fff&text=No+Image",
                "url": "#",
                "title": anime_name
            }
            
        except Exception as e:
            print(f"CRITICAL FAILURE [JIKAN] Excepción crítica: {e}")
            return {
                "image_url": "https://dummyimage.com/225x320/000/fff&text=Error",
                "url": "#",
                "title": anime_name
            }