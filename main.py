"""
FastAPI backend skeleton for the Heritage Language Translator.
Run: uvicorn main:app --reload
Requires: pip install fastapi uvicorn pymongo --break-system-packages

/translate returns a placeholder until the trained model is plugged in.
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pymongo import MongoClient
from datetime import datetime

app = FastAPI(title="Heritage Language Translator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to your real frontend domain once you have one
    allow_methods=["*"],
    allow_headers=["*"],
)

# Reads from environment variables — set these in Render's dashboard.
# Falls back to localhost for local development.
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client["heritage_translator"]

# ============================================================
# Request/response models
# ============================================================

class TranslateRequest(BaseModel):
    text: str
    source_language: str   # "tulu" | "kodava" | "english"
    target_language: str

class ContributeRequest(BaseModel):
    type: str               # "word" | "sentence" | "audio"
    language: str
    dialect: str | None = None
    content: dict
    contributor_username: str

# ============================================================
# Endpoints
# ============================================================

@app.get("/")
def root():
    return FileResponse("frontend.html")

@app.get("/api")
def api_status():
    return {"status": "Heritage Language Translator API running"}

@app.post("/translate")
def translate(req: TranslateRequest):
    # PLACEHOLDER — swap this out once the trained model is ready.
    # Real version will load the fine-tuned checkpoint and call model.generate().
    result = {
        "translation": "Model loading... (placeholder response)",
        "source_text": req.text,
        "source_language": req.source_language,
        "target_language": req.target_language,
    }

    # Log every translation request for analytics/eval later
    db.translations.insert_one({
        **result,
        "model_version": "placeholder",
        "created_at": datetime.utcnow(),
    })
    return result

@app.get("/dictionary/search")
def search_dictionary(q: str, language: str | None = None):
    query = {"$text": {"$search": q}}
    if language:
        query["language"] = language
    results = list(db.words.find(query, {"_id": 0}).limit(20))
    return {"query": q, "results": results}

@app.get("/dialects")
def get_dialects(language: str | None = None):
    query = {"language": language} if language else {}
    dialects = list(db.dialects.find(query, {"_id": 0}))
    return {"dialects": dialects}

@app.get("/contribute/count")
def contribution_count(username: str):
    count = db.submissions.count_documents({"contributor_username": username})
    return {"username": username, "count": count}

@app.post("/contribute")
def contribute(req: ContributeRequest):
    submission = {
        "type": req.type,
        "payload": {
            "language": req.language,
            "dialect": req.dialect,
            **req.content,
        },
        "status": "pending",
        "contributor_username": req.contributor_username,
        "created_at": datetime.utcnow(),
    }
    result = db.submissions.insert_one(submission)
    return {"message": "Submission received, pending admin review", "id": str(result.inserted_id)}

@app.get("/admin/pending")
def get_pending_submissions():
    pending = list(db.submissions.find({"status": "pending"}))
    for p in pending:
        p["_id"] = str(p["_id"])
    return {"pending": pending}

@app.post("/admin/verify/{submission_id}")
def verify_submission(submission_id: str, approve: bool):
    from bson import ObjectId
    status = "approved" if approve else "rejected"
    db.submissions.update_one(
        {"_id": ObjectId(submission_id)},
        {"$set": {"status": status}}
    )
    return {"message": f"Submission {status}"}
