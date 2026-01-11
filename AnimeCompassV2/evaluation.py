import pandas as pd
import numpy as np
from kg_engine import KGEngine

# Inicializamos el motor
kg = KGEngine(relative_folder_path="../anime_recommender_final")

def calculate_precision_at_k(test_anime_name, k=5):
    """
    Calcula la precisión basándose en si las recomendaciones comparten
    al menos un género con el anime original.
    (Basado en Diapositiva 50: Precision@N)
    """
    # 1. Obtenemos los datos del anime 'query' (Ground Truth)
    target_row = kg.df[kg.df['Name'] == test_anime_name]
    if target_row.empty:
        return 0.0
    
    target_genres = set(target_row.iloc[0]['Genres']) # Asumiendo que es una lista o set
    
    # 2. Pedimos recomendaciones
    recommendations = kg.search_top_k(test_anime_name, k=k)
    
    hits = 0
    for rec in recommendations:
        # Buscamos los géneros del recomendado en el DF
        rec_row = kg.df[kg.df['Name'] == rec['name']].iloc[0]
        rec_genres = set(rec_row['Genres'])
        
        # CRITERIO DE RELEVANCIA:
        # Si comparten al menos un género, lo consideramos "Relevante" (Hit)
        if not target_genres.isdisjoint(rec_genres):
            hits += 1
            
    # Precision = Relevantes / Recomendados
    return hits / k

def run_evaluation_suite():
    print("\n📊 --- INICIANDO EVALUACIÓN OFFLINE (Precision@5) ---")
    
    # Lista de test (Animes conocidos de diferentes géneros)
    test_cases = [
        "Naruto", "Death Note", "Your Lie in April", 
        "Steins;Gate", "Haikyuu!!", "Toradora!", 
        "Attack on Titan", "Spirited Away"
    ]
    
    scores = []
    
    for anime in test_cases:
        try:
            score = calculate_precision_at_k(anime, k=5)
            scores.append(score)
            print(f"✅ {anime}: Precision@5 = {score:.2f}")
        except Exception as e:
            print(f"⚠️ Saltando {anime}: {e}")

    mean_precision = np.mean(scores)
    print(f"\n🏆 MAP (Mean Average Precision) estimado: {mean_precision:.4f}")
    print("----------------------------------------------------")

if __name__ == "__main__":
    run_evaluation_suite()