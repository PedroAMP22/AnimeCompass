
# Módulo: Motor del Grafo de Conocimiento
# Descripción: Carga y gestiona el grafo de animes. Contiene los algoritmos
# de búsqueda semántica, filtrado y cálculo de puntuaciones de similitud.

import os
import torch
import pickle
import numpy as np
import pandas as pd
import difflib
import math

# Prefijo definido
ONTO_PREFIX = "http://www.fdi.ucm.es/mia/sbc/animeontology/"

class KGEngine:
    def __init__(self, relative_folder_path="../anime_recommender_final"):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_path = os.path.normpath(os.path.join(current_dir, relative_folder_path))
        
        print(f"Cargando motor híbrido desde: {self.data_path}")
        
        try:
            # Cargar Modelo
            self.model = torch.load(
                os.path.join(self.data_path, "model.pt"), 
                map_location=torch.device('cpu'),
                weights_only=False 
            )
            
            # Cargar Mapeos
            with open(os.path.join(self.data_path, "triples_factory.pkl"), "rb") as f:
                self.triples_factory = pickle.load(f)
                self.entity_to_id = self.triples_factory.entity_to_id
            
            # Cargar Datos
            with open(os.path.join(self.data_path, "data_package.pkl"), "rb") as f:
                data_pkg = pickle.load(f)
                raw_data = data_pkg["anime_data"]
                
                # Convertir a DataFrame
                self.df = pd.DataFrame.from_dict(raw_data, orient='index')
                self.df.reset_index(inplace=True)
                self.df.rename(columns={'index': 'Name'}, inplace=True)
                
                # Mapeo de columnas
                map_cols = {'N': 'Episodes', 'A': 'Year', 'G': 'Genres', 'E': 'VoiceActors'}
                self.df.rename(columns=map_cols, inplace=True)
                
                # Rellenar columnas faltantes
                if 'Studio' not in self.df.columns: self.df['Studio'] = None
                
                print(f"CORRECT DataFrame listo. Total animes: {len(self.df)}")

            # Embeddings
            embeddings = self.model.entity_representations[0](indices=None).detach().cpu().numpy()
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            self.entity_embeddings = embeddings / (norms + 1e-9)
            
            print("CORRECT KG Engine Híbrido listo.")
            
        except Exception as e:
            print(f"ERROR: Error fatal: {e}")
            raise e

    def _find_best_match(self, user_query):
        query_clean = user_query.strip().lower()
        all_names = self.df['Name'].astype(str).tolist()
        matches = difflib.get_close_matches(user_query, all_names, n=1, cutoff=0.4)
        if matches: return matches[0]
        for name in all_names:
            if query_clean in name.lower(): return name
        return None

    def _get_embedding_id(self, anime_name):
        search_key = str(anime_name).replace(" ", "_") 
        uri = f"<{ONTO_PREFIX}{search_key}>"
        if uri in self.entity_to_id: return self.entity_to_id[uri]
        for u, eid in self.entity_to_id.items():
            if search_key in u: return eid
        return None

    # --- HEURÍSTICAS  ---

    def _is_valid(self, val):
        """Devuelve True si el valor no es None ni NaN"""
        if val is None: return False
        if isinstance(val, float) and (math.isnan(val) or math.isinf(val)): return False
        if isinstance(val, str) and (val.lower() == 'nan' or val.strip() == ''): return False
        return True

    def _jaccard(self, val_a, val_b):
        """Para Géneros y Actores"""
        if not self._is_valid(val_a) or not self._is_valid(val_b): return 0.0
        
        try:
            # Listas
            set_a = set(val_a) if isinstance(val_a, (list, set, tuple)) else set([val_a])
            set_b = set(val_b) if isinstance(val_b, (list, set, tuple)) else set([val_b])
            
            if not set_a and not set_b: return 0.0
            intersection = len(set_a.intersection(set_b))
            union = len(set_a.union(set_b))
            return intersection / union if union > 0 else 0.0
        except:
            return 0.0

    def _exact_match(self, val_a, val_b):
        """Para Estudio"""
        if not self._is_valid(val_a) or not self._is_valid(val_b): return 0.0
        return 1.0 if str(val_a).strip().lower() == str(val_b).strip().lower() else 0.0

    def _exp_decay(self, val_a, val_b, alpha=0.05):
        """Para Episodios"""
        if not self._is_valid(val_a) or not self._is_valid(val_b): return 0.0
        try:
            a = float(val_a)
            b = float(val_b)
            diff = abs(a - b)
            return math.exp(-alpha * diff)
        except: return 0.0

    def _linear_decay(self, val_a, val_b, max_diff=20):
        """Para Año"""
        if not self._is_valid(val_a) or not self._is_valid(val_b): return 0.0
        try:
            a = float(val_a)
            b = float(val_b)
            diff = abs(a - b)
            if diff > max_diff: return 0.0
            return 1.0 - (diff / max_diff)
        except: return 0.0

    def _calculate_heuristic_score(self, target, candidate):
        # Calculamos cada parte por separado. Si una falla, devuelve 0.0
        s_genres = self._jaccard(target.get('Genres'), candidate.get('Genres'))
        s_studio = self._exact_match(target.get('Studio'), candidate.get('Studio'))
        s_actors = self._jaccard(target.get('VoiceActors'), candidate.get('VoiceActors'))
        s_episodes = self._exp_decay(target.get('Episodes'), candidate.get('Episodes'))
        s_year = self._linear_decay(target.get('Year'), candidate.get('Year'))
        
        # Suma ponderada
        total = (s_genres * 0.7) + (s_studio * 0.10) + (s_actors * 0.05) + \
                (s_episodes * 0.05) + (s_year * 0.1)
        
        return total

    def _safe_float(self, val):
        """Limpia NaNs finales para el JSON"""
        try:
            f = float(val)
            if math.isnan(f) or math.isinf(f): return 0.0
            return f
        except: return 0.0

    def search_top_k(self, query_text, k=5, exclude_list= None):
        if exclude_list is None:
            exclude_list = []

        print(f"\nBuscando: '{query_text}' (Excluyendo {len(exclude_list)} items)")
        target_name = self._find_best_match(query_text)
        if not target_name: 
            print("ERROR No encontrado en DF")
            return []

        target_row = self.df[self.df['Name'] == target_name].iloc[0]
        target_id = self._get_embedding_id(target_name)
        
        target_vec = None
        if target_id is not None:
            target_vec = self.entity_embeddings[target_id]
        
        results = []
        
        for idx, row in self.df.iterrows():
            cand_name = row['Name']
            if cand_name == target_name: continue
            if cand_name in exclude_list: continue
            
            # 1. TransR (0.8)
            transr_sim = 0.0
            if target_vec is not None:
                cand_id = self._get_embedding_id(cand_name)
                if cand_id is not None:
                    cand_vec = self.entity_embeddings[cand_id]
                    sim = np.dot(target_vec, cand_vec)
                    transr_sim = (sim + 1) / 2
            
            # 2. Heurística (0.2)
            heur_sim = self._calculate_heuristic_score(target_row, row)
            
            # 3. Final
            final_score = (0.8 * transr_sim) + (0.2 * heur_sim)
            
            results.append({
                "name": str(cand_name),
                "score": self._safe_float(final_score),
                "transr": self._safe_float(transr_sim),
                "heuristic": self._safe_float(heur_sim),
                "details": f"Géneros: {row.get('Genres')}, Año: {row.get('Year')}"
            })
            
        results = sorted(results, key=lambda x: x["score"], reverse=True)[:k]
        return results