
# Módulo: Gestión de Base de Datos
# Descripción: Funciones utilitarias para la gestion de datos en archivos JSON.
# Maneja la carga y guardado de usuarios, historial de likes/dislikes y reviews.

import json
import os

DB_PATH = "users.json"

def load_db():
    if not os.path.exists(DB_PATH):
        return {}
    with open(DB_PATH, "r") as f:
        return json.load(f)

def save_db(data):
    with open(DB_PATH, "w") as f:
        json.dump(data, f, indent=4)