from fastapi import FastAPI
from pydantic import BaseModel
from kg_engine import KGEngine
import uvicorn

app = FastAPI()
# Inicializamos tu sistema con la carpeta de tus archivos .pt y .pkl
kg = KGEngine(folder_path="../anime_recommender_final")

class QueryRequest(BaseModel):
    query: str
    top_k: int = 5

@app.post("/execute/search_knowledge_graph")
def execute_search(request: QueryRequest):
    results = kg.search_top_k(request.query, request.top_k)
    return {"results": results}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)