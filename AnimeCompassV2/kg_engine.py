import os
import torch
import pickle
import numpy as np
import difflib  # Librería estándar para comparar strings

class KGEngine:
    def __init__(self, folder_path="anime_recommender_final"):
        print(f"Cargando sistema desde '{folder_path}'...")
        
        # 1. Cargar el modelo PyKEEN
        model_path = os.path.join(folder_path, "model.pt")
        self.model = torch.load(model_path, map_location=torch.device('cpu'), weights_only=False)
        
        # 2. Cargar Mapeos
        with open(os.path.join(folder_path, "triples_factory.pkl"), "rb") as f:
            triples_factory = pickle.load(f)
            self.entity_to_id = triples_factory.entity_to_id
            # Creamos una lista de nombres para búsqueda rápida
            self.all_entity_names = list(self.entity_to_id.keys())
        
        # 3. Cargar Metadatos
        with open(os.path.join(folder_path, "data_package.pkl"), "rb") as f:
            data_pkg = pickle.load(f)
            self.anime_data = data_pkg["anime_data"]
            
        # Extraer embeddings
        self.all_entity_embeddings = self.model.entity_representations[0](indices=None).detach().cpu().numpy()
        print("KG Engine listo.")

    def _find_best_match(self, user_query):
        """
        Busca el nombre de anime más parecido en la base de datos 
        basándose en lo que escribió el usuario.
        """
        # 1. Intentar coincidencia exacta (limpiando espacios y minúsculas)
        query_clean = user_query.strip().lower()
        
        # 2. Búsqueda por coincidencia cercana (Fuzzy Matching)
        # n=1 devuelve el mejor resultado, cutoff=0.4 es la sensibilidad
        matches = difflib.get_close_matches(user_query, self.all_entity_names, n=1, cutoff=0.4)
        
        if matches:
            return matches[0]
        
        # 3. Si no hay match directo, buscar si el texto del usuario está contenido en algún nombre
        for name in self.all_entity_names:
            if query_clean in name.lower():
                return name
                
        return None

    def _get_entity_vector(self, entity_name):
        """Obtiene el vector de TransR para un nombre real de la DB."""
        ent_id = self.entity_to_id.get(entity_name)
        if ent_id is not None:
            return self.all_entity_embeddings[ent_id]
        return None

    def search_top_k(self, query_text, k=5):
        # 1. Primero encontramos de qué anime está hablando el usuario realmente
        real_name = self._find_best_match(query_text)
        
        if not real_name:
            return [] # No se encontró nada parecido

        # 2. Obtenemos el vector (TransR) de ese anime encontrado
        query_vec = self._get_entity_vector(real_name)
        
        results = []
        # 3. Comparamos ese vector contra todos los demás en el grafo
        for name, eid in self.entity_to_id.items():
            ent_vec = self.all_entity_embeddings[eid]
            
            # Similitud de Coseno entre vectores de TransR
            sim_score = np.dot(query_vec, ent_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(ent_vec))
            
            # Heurística extra: si el nombre es muy parecido, subimos el score
            # (Esto ayuda a que el anime buscado salga el primero)
            heur_score = 0
            if real_name.lower() in name.lower():
                heur_score = 0.2

            results.append({
                "name": name,
                "score": float(sim_score + heur_score),
                "matched_from": real_name # Para que el LLM sepa qué entendimos
            })
        
        # Ordenar y devolver
        results = sorted(results, key=lambda x: x["score"], reverse=True)
        return results[:k]