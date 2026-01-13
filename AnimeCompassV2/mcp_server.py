from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from kg_engine import KGEngine
from typing import Optional, Dict, Any, List
from db_management import load_db, save_db
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
    try:
        results = kg.search_top_k(req.query, req.top_k, req.exclude)
        return {"results": results}
    except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

class ReviewRequest(BaseModel):
    nick: str
    comment: str

@app.get("/reviews")
def get_reviews():
    db = load_db()
    all_comments = []
    for nick, data in db.items():
        for msg in data.get("comments", []):
            all_comments.append({"nick": nick, "text": msg})
    return {"reviews": all_comments}

@app.post("/reviews/add")
def add_review(req: ReviewRequest):
    db = load_db()
    if req.nick not in db:
        db[req.nick] = {"comments": []}
    
    db[req.nick]["comments"].append(req.comment)
    save_db(db)
    return {"status": "success"}

class InteractionRequest(BaseModel):
    nick: str
    anime_name: str


@app.post("/user/like")
def add_like(req: InteractionRequest):
    db = load_db()
    nick = req.nick.lower()
    if nick in db:
        if "likes" not in db[nick]: db[nick]["likes"] = []
        if req.anime_name not in db[nick]["likes"]:
            db[nick]["likes"].append(req.anime_name)
            save_db(db)
    return {"status": "success"}

@app.post("/user/dislike")
def add_dislike(req: InteractionRequest):
    db = load_db()
    nick = req.nick.lower()
    if nick in db:
        if "disliked_animes" not in db[nick]: db[nick]["disliked_animes"] = []
        if req.anime_name not in db[nick]["disliked_animes"]:
            db[nick]["disliked_animes"].append(req.anime_name)
            save_db(db)
    return {"status": "success"}

@app.post("/user/add")
def add_user(req: ReviewRequest):
    db = load_db()
    nick = req.nick.lower()
    if nick not in db:
        db[nick] = {"comments": [], "disliked_animes": [], "likes": []}
        save_db(db)
    return {"status": "success", "data": db[nick]} 


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)