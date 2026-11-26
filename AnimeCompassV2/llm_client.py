
# Módulo: Cliente LLM (Ollama Wrapper)
# Descripción: Gestiona la comunicación el modelo Llama 3.2. Incluye lógica
# para extracción estricta de entidades en lasq queries y generación de respuestas conversacionales.

import requests

class OllamaClient:
    def __init__(self, model="llama3.2", base_url="http://localhost:11434"):
        self.base_url = f"{base_url}/api/generate"
        self.model = model

    def _call(self, prompt, temp=0.7):
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temp}
        }
        try:
            res = requests.post(self.base_url, json=payload)
            if res.status_code == 200:
                return res.json().get("response", "")
            else:
                print(f"⚠️ Error OLLAMA Status: {res.status_code}")
                return ""
        except Exception as e:
            print(f"❌ Error CONEXIÓN OLLAMA: {e}")
            return ""

    def should_use_tool(self, query):
        """
        Router más permisivo para Llama 3.2
        """
        print(f"\nRouter pensando sobre: '{query}'...")
        
        # Prompt simple, evita confusiones
        prompt = f"""
        Tu única tarea es clasificar si el usuario menciona 'anime', series japonesas o pide recomendaciones.
        Texto: "{query}"
        Responde SOLO con la palabra "SI" o "NO".
        """
        
        ans = self._call(prompt, temp=0.0).strip().upper()
        print(f"El modelo dice: '{ans}'")
        
        activar = "SI" in ans or "YES" in ans or "SÍ" in ans or "ANIME" in ans
        
        if activar:
            print("Decisión: CONSULTAR BASE DE DATOS")
        else:
            print("Decisión: CHARLA NORMAL")
            
        return activar
    
    def extract_anime_name(self, query):
        """Extrae solo el nombre del anime de la frase"""
        print(f"Extrayendo entidad de: '{query}'...")
        
        # Promt engineering
        prompt = f"""
        Actúa como un extractor de subcadenas. Tu trabajo es extraer los elementos necesarios de la consulta.
        
        Ejemplos de comportamiento esperado:
        Input: "Quiero ver algo como Akira" -> Akira
        Input: "Busco series similares a Monster" -> Monster
        Input: "Recomiendame algo parecido a Berserk por favor" -> Berserk
        
        Input del usuario: "{query}"
        
        Nombre del anime (Solo el texto exacto):
        """
        
        raw_response = self._call(prompt, temp=0.0).strip()
        
        # --- LIMPIEZA ---
        if ":" in raw_response:
            name = raw_response.split(":")[-1].strip()
        else:
            name = raw_response
            
        name = name.replace(".", "").replace('"', '').replace("'", "").strip()
        
        # --- REGLA ANTI-ALUCINACIÓN  ---
        # Si el nombre extraído no está en la frase original, el modelo ha alucinado
        if name.lower() not in query.lower():
            print(f"ALERTA: El modelo alucinó '{name}' pero no está en la frase '{query}'.")
            
            # En caso de fallo de emergencia buscamos si las palabras de la frase coinciden con algo conocido
            # Intento de recuperación simple: si la frase es corta (ej "Bleach"), asumimos que es el nombre
            if len(query.split()) <= 2:
                name = query
                print(f"WARNING: Recuperado usando la query completa: '{name}'")
            else:
                # Si alucinó algo totalmente distinto, dev null
                print("ERROR: Descartando alucinación.")
                return "NULL"

        print(f"Entidad extraída: '{name}'")
        return name

    def prompt(self, system, user):
        full = f"System: {system}\nUser: {user}"
        return self._call(full)
    
    def chat(self, system, history, current_user_msg):
        """
        Construye un prompt con todo el historial de la conversación.
        """
        # 1. Iniciamos con las instrucciones del sistema
        full_prompt = f"System: {system}\n\n"
        
        recent_history = history[-10:]
        # 2. Añadimos el historial previo
        for msg in recent_history:
            role = "User" if msg["role"] == "user" else "Assistant"
            content = msg["content"]
            # Añadimos el turno al prompt
            full_prompt += f"{role}: {content}\n"
            
        # 3. Añadimos el mensaje actual del usuario
        full_prompt += f"User: {current_user_msg}\nAssistant:"
        
        # 4. Enviamos todo el bloque al LLM
        return self._call(full_prompt)

    