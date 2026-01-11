from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from kg_engine import KGEngine

app = FastAPI(title="Anime Hybrid Server")

# Inicializar motor apuntando a la carpeta hermana
# "../anime_recommender_final" significa "sube un nivel y entra ahí"
try:
    kg = KGEngine(relative_folder_path="../anime_recommender_final")
except Exception as e:
    print(f"Error iniciando servidor: {e}")

class QueryRequest(BaseModel):
    query: str
    top_k: int = 5
    exclude: list[str] = []

@app.post("/execute/search_knowledge_graph")
def search(req: QueryRequest):
    results = kg.search_top_k(req.query, req.top_k, req.exclude)
    return {"results": results}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)