import os
import pickle
import torch
import pandas as pd
import sys

# Configuración de rutas (Ajusta si es necesario)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "../anime_recommender_final")
TTL_DIR = os.path.join(BASE_DIR, "../data") # Asumiendo que end.ttl está aquí

def print_header(title):
    print("\n" + "="*60)
    print(f" 🔍 {title}")
    print("="*60)

def inspect_data_package():
    print_header("INSPECCIONANDO data_package.pkl")
    path = os.path.join(DATA_DIR, "data_package.pkl")
    
    if not os.path.exists(path):
        print(f"❌ Archivo no encontrado: {path}")
        return

    try:
        with open(path, "rb") as f:
            data = pickle.load(f)
        
        print(f"Tipo de dato raíz: {type(data)}")
        
        if isinstance(data, dict):
            print(f"Claves encontradas: {list(data.keys())}")
            
            if "anime_data" in data:
                anime_data = data["anime_data"]
                print(f"\n--- Contenido de 'anime_data' ---")
                print(f"Tipo: {type(anime_data)}")
                
                # Si es un DataFrame
                if isinstance(anime_data, pd.DataFrame):
                    print(f"Es un DataFrame con shape: {anime_data.shape}")
                    print(f"Columnas: {anime_data.columns.tolist()}")
                    print("\nEjemplo de primera fila:")
                    print(anime_data.iloc[0])
                
                # Si es un Diccionario (lo más probable según tus errores anteriores)
                elif isinstance(anime_data, dict):
                    print(f"Es un Diccionario con {len(anime_data)} entradas.")
                    # Miramos el primer elemento
                    first_key = next(iter(anime_data))
                    first_val = anime_data[first_key]
                    print(f"\nEjemplo de entrada (Clave: '{first_key}'):")
                    print(f"Tipo del valor: {type(first_val)}")
                    print(f"Contenido: {first_val}")
                    
                    if isinstance(first_val, dict):
                        print(f"Las claves internas son: {list(first_val.keys())}")
                    elif isinstance(first_val, list):
                        print("El valor es una lista.")
    except Exception as e:
        print(f"❌ Error leyendo pickle: {e}")

def inspect_triples_factory():
    print_header("INSPECCIONANDO triples_factory.pkl")
    path = os.path.join(DATA_DIR, "triples_factory.pkl")
    
    if not os.path.exists(path):
        print(f"❌ Archivo no encontrado: {path}")
        return

    try:
        with open(path, "rb") as f:
            tf = pickle.load(f)
            
        print(f"Clase cargada: {type(tf)}")
        if hasattr(tf, 'entity_to_id'):
            e2id = tf.entity_to_id
            print(f"Total de entidades mapeadas: {len(e2id)}")
            print("\n--- Muestra de 5 URIs (Para ver si usan 'onto:' o 'http://') ---")
            for i, (k, v) in enumerate(e2id.items()):
                if i >= 5: break
                print(f"ID {v}: {k}")
        else:
            print("⚠️ El objeto no tiene atributo 'entity_to_id'")
            print(dir(tf))
    except Exception as e:
        print(f"❌ Error: {e}")

def inspect_model():
    print_header("INSPECCIONANDO model.pt (TransR)")
    path = os.path.join(DATA_DIR, "model.pt")
    
    if not os.path.exists(path):
        print(f"❌ Archivo no encontrado: {path}")
        return

    try:
        # Usamos el fix de weights_only=False
        model = torch.load(path, map_location='cpu', weights_only=False)
        print(f"Modelo cargado: {type(model)}")
        
        if hasattr(model, 'entity_representations'):
            emb = model.entity_representations[0](indices=None)
            print(f"Forma de los embeddings (Shape): {emb.shape}")
            print(f"Dispositivo: {emb.device}")
        else:
            print("⚠️ No encuentro 'entity_representations'. Atributos disponibles:")
            print(dir(model))
            
    except Exception as e:
        print(f"❌ Error cargando modelo PyTorch: {e}")

def inspect_ttl():
    print_header("INSPECCIONANDO end.ttl (Primeras 20 líneas)")
    path = os.path.join(TTL_DIR, "end.ttl")
    
    if not os.path.exists(path):
        # Intentar buscar en la misma carpeta por si acaso
        path = os.path.join(DATA_DIR, "end.ttl")
        if not os.path.exists(path):
            print(f"❌ Archivo no encontrado en ../data ni en ../anime_recommender_final")
            return

    try:
        with open(path, "r", encoding="utf-8") as f:
            for i in range(20):
                print(f.readline().strip())
    except Exception as e:
        print(f"❌ Error leyendo TTL: {e}")

if __name__ == "__main__":
    print(f"Ejecutando diagnóstico desde: {BASE_DIR}")
    inspect_data_package()
    inspect_triples_factory()
    inspect_model()
    inspect_ttl()