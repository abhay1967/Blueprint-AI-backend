# 📁 File: main.py

from fastapi import FastAPI, HTTPException, status, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth
import functools
from fastapi.middleware.cors import CORSMiddleware
import json
from pydantic import BaseModel
import os
import uvicorn
import uuid
import datetime
print("[DEBUG] DATABASE_URL:", os.getenv("DATABASE_URL"))
from agents.research_agent import ResearchAgent
from agents.feature_parser_agent import FeatureParserAgent
from agents.architecture_planner_agent import ArchitecturePlannerAgent
from agents.tech_stack_selector_agent import TechStackSelectorAgent
from agents.security_infra_agent import SecurityInfraAgent
from db import chat, database

# Initialize Firebase Admin SDK if not already initialized
if not firebase_admin._apps:
    cred = credentials.Certificate(os.path.join(os.path.dirname(__file__), 'firebase-service-account.json'))
    firebase_admin.initialize_app(cred)

app = FastAPI()

@app.get("/")
def root():
    return {"message": "👋 Welcome to Blueprint AI Backend!", "status": "ok"}

# Auth scheme for extracting JWT
bearer_scheme = HTTPBearer()

def authenticate_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    token = credentials.credentials
    try:
        decoded_token = firebase_auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        print(f"[AUTH] Invalid token: {e}")
        raise HTTPException(status_code=401, detail="Invalid or missing authentication token")


@app.on_event("startup")
async def startup():
    await database.connect()
    print("[DEBUG] DATABASE_URL:", os.getenv("DATABASE_URL"))

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 🧾 Request schema
class ProductIdea(BaseModel):
    title: str

# 📄 Response schema
class Chat(BaseModel):
    id: str
    title: str
    created_at: str

# 🔧 Health check
@app.get("/health")
def health_check():
    return {"status": "ok"}

# 🧠 AI Architecture pipeline endpoint (non-streaming)
@app.post("/blueprint")
async def run_blueprint(request: ProductIdea, user=Depends(authenticate_user)):
    try:
        result = run_blueprint_ai(request.title)
    except Exception as e:
        return {"error": str(e)}, 500
    chat_id = str(uuid.uuid4())
    now = datetime.datetime.utcnow()
    user_message_id = str(uuid.uuid4())
    assistant_message_id = str(uuid.uuid4())
    user_id = user["uid"]
    query = chat.insert().values(
        id=chat_id,
        user_id=user_id,
        title=request.title,
        user_message=request.title,
        assistant_message=json.dumps(result),
        created_at=now
    )
    await database.execute(query)
    return {
        "id": chat_id,
        "title": request.title,
        "createdAt": now.isoformat(),
        "messages": [
            {"id": user_message_id, "role": "user", "content": request.title},
            {"id": assistant_message_id, "role": "assistant", "content": json.dumps(result)}
        ]
    }

# 🧾 Return all chats
@app.get("/chats")
async def get_chat(user=Depends(authenticate_user)):
    import traceback
    print("[BACKEND] Fetching chat for user:", user)
    print("[BACKEND] user['uid']:", user.get('uid'), type(user.get('uid')))
    try:
        query = chat.select().where(chat.c.user_id == user["uid"]).order_by(chat.c.created_at.desc())
        rows = await database.fetch_all(query)
        chats_list = []
        for row in rows:
            chats_list.append({
                "id": str(row["id"]),
                "title": row["title"],
                "createdAt": row["created_at"].isoformat() if row["created_at"] else None,
                "messages": [
                    {"id": str(uuid.uuid4()), "role": "user", "content": row["user_message"]},
                    {"id": str(uuid.uuid4()), "role": "assistant", "content": row["assistant_message"]}
                ]
            })
        print(f"[BACKEND] Returning {len(chats_list)} chat for user {user['uid']}")
        return chats_list
    except Exception as e:
        print("[BACKEND] Exception in /chat endpoint:", str(e))
        traceback.print_exc()
        return JSONResponse({"status": "error", "detail": str(e)}, status_code=500)


# 💾 Save chat (insert or update)
class SaveChatRequest(BaseModel):
    chat_id: str
    title: str
    messages: list

@app.post("/chat/save")
async def save_chat(request: Request, user=Depends(authenticate_user)):
    data = await request.json()
    print("[BACKEND] Received /chat/save data:", data)
    print("[BACKEND] Authenticated user:", user)
    chat_id = data.get("chat_id")
    title = data.get("title")
    messages = data.get("messages")
    user_message = ""
    assistant_message = ""
    if messages and len(messages) >= 2:
        user_message = messages[-2]["content"]
        assistant_message = messages[-1]["content"]
    elif messages and len(messages) == 1:
        user_message = messages[0]["content"]
    try:
        # UPSERT: Insert or update on conflict (id, user_id)
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        now = datetime.datetime.utcnow()
        upsert_stmt = pg_insert(chat).values(
            id=chat_id,
            user_id=user["uid"],
            title=title,
            user_message=user_message,
            assistant_message=assistant_message,
            created_at=now
        ).on_conflict_do_update(
            index_elements=[chat.c.id],
            set_={
                "user_id": user["uid"],
                "title": title,
                "user_message": user_message,
                "assistant_message": assistant_message,
                "created_at": now
            }
        )
        upsert_stmt = upsert_stmt.returning(chat)
        result = await database.fetch_one(upsert_stmt)
        print("[BACKEND] Upsert result (inserted/updated row):", result)
        # Debug: fetch all chat to confirm insert
        try:
            all_chat = await database.fetch_all(chat.select())
            print(f"[DEBUG] All chat in DB after save: {all_chat}")
        except Exception as db_debug_exc:
            print("[DEBUG] Error fetching all chats:", db_debug_exc)
        return {"status": "saved", "row": dict(result) if result else None}
    except Exception as e:
        import traceback
        print("[ERROR] Exception in /chat/save:", e)
        traceback.print_exc()
        return JSONResponse({"status": "error", "detail": str(e)}, status_code=500)

# 🧹 Delete chat by ID
@app.delete("/chat/{chat_id}/delete")
async def delete_chat(chat_id: str):
    query = chat.delete().where(chat.c.id == chat_id)
    await database.execute(query)
    return {"status": "deleted"}

# 🚀 Generate via /generate-architecture-stream/
from stream_utils import stream_blueprint_ai
from fastapi.responses import StreamingResponse

@app.post("/generate-architecture-stream/")
def generate_architecture(request: ProductIdea):
    return StreamingResponse(
        stream_blueprint_ai(request.title),
        media_type="text/event-stream"
    )

def run_blueprint_ai(product_idea: str):
    print("\n🧠 Starting Blueprint AI Pipeline...\n")
    partials = {}
    try:
        print("🔍 Running Research Agent...")
        research_agent = ResearchAgent()
        research_summary = research_agent.run(product_idea)
        print("\n✅ Research Summary:\n", research_summary)
        partials["research_summary"] = research_summary

        print("🤩 Running Feature Parser Agent...")
        feature_parser = FeatureParserAgent()
        parsed_features = feature_parser.run(research_summary)
        print("\n✅ Parsed Features:\n", parsed_features)
        partials["parsed_features"] = parsed_features

        print("🏗️ Running Architecture Planner Agent...")
        architecture_planner = ArchitecturePlannerAgent()
        architecture_plan = architecture_planner.run(parsed_features)
        print("\n✅ Architecture Plan:\n", architecture_plan)
        partials["architecture_plan"] = architecture_plan

        print("🧱 Running Tech Stack Selector Agent...")
        tech_stack_selector = TechStackSelectorAgent()
        tech_stack = tech_stack_selector.run(architecture_plan)
        print("\n✅ Tech Stack:\n", tech_stack)
        partials["tech_stack"] = tech_stack

        print("🔐 Running Security & Infrastructure Agent...")
        security_infra_agent = SecurityInfraAgent()
        security_recommendations = security_infra_agent.run(architecture_plan)
        print("\n✅ Security Recommendations:\n", security_recommendations)
        partials["security_recommendations"] = security_recommendations

        return partials
    except Exception as e:
        # Return whatever partials are available, plus error
        partials["error"] = str(e)
        return partials
from fastapi import FastAPI, HTTPException, status, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth
import functools
from fastapi.middleware.cors import CORSMiddleware
import json
from pydantic import BaseModel
import os
import uvicorn
import uuid
import datetime
print("[DEBUG] DATABASE_URL:", os.getenv("DATABASE_URL"))
from agents.research_agent import ResearchAgent
from agents.feature_parser_agent import FeatureParserAgent
from agents.architecture_planner_agent import ArchitecturePlannerAgent
from agents.tech_stack_selector_agent import TechStackSelectorAgent
from agents.security_infra_agent import SecurityInfraAgent
from db import chat, database

# Initialize Firebase Admin SDK if not already initialized
if not firebase_admin._apps:
    cred = credentials.Certificate(os.path.join(os.path.dirname(__file__), 'firebase-service-account.json'))
    firebase_admin.initialize_app(cred)

app = FastAPI()

@app.get("/")
def root():
    return {"message": "👋 Welcome to Blueprint AI Backend!", "status": "ok"}

# Auth scheme for extracting JWT
bearer_scheme = HTTPBearer()

def authenticate_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    token = credentials.credentials
    try:
        decoded_token = firebase_auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        print(f"[AUTH] Invalid token: {e}")
        raise HTTPException(status_code=401, detail="Invalid or missing authentication token")


@app.on_event("startup")
async def startup():
    await database.connect()
    print("[DEBUG] DATABASE_URL:", os.getenv("DATABASE_URL"))

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 🧾 Request schema
class ProductIdea(BaseModel):
    title: str

# 📄 Response schema
class Chat(BaseModel):
    id: str
    title: str
    created_at: str

# 🔧 Health check
@app.get("/health")
def health_check():
    return {"status": "ok"}

# 🧠 AI Architecture pipeline endpoint (non-streaming)
@app.post("/blueprint")
async def run_blueprint(request: ProductIdea, user=Depends(authenticate_user)):
    try:
        result = run_blueprint_ai(request.title)
    except Exception as e:
        return {"error": str(e)}, 500
    chat_id = str(uuid.uuid4())
    now = datetime.datetime.utcnow()
    user_message_id = str(uuid.uuid4())
    assistant_message_id = str(uuid.uuid4())
    user_id = user["uid"]
    query = chat.insert().values(
        id=chat_id,
        user_id=user_id,
        title=request.title,
        user_message=request.title,
        assistant_message=json.dumps(result),
        created_at=now
    )
    await database.execute(query)
    return {
        "id": chat_id,
        "title": request.title,
        "createdAt": now.isoformat(),
        "messages": [
            {"id": user_message_id, "role": "user", "content": request.title},
            {"id": assistant_message_id, "role": "assistant", "content": json.dumps(result)}
        ]
    }

# 🧾 Return all chats
@app.get("/chats")
async def get_chat(user=Depends(authenticate_user)):
    import traceback
    print("[BACKEND] Fetching chat for user:", user)
    print("[BACKEND] user['uid']:", user.get('uid'), type(user.get('uid')))
    try:
        query = chat.select().where(chat.c.user_id == user["uid"]).order_by(chat.c.created_at.desc())
        rows = await database.fetch_all(query)
        chats_list = []
        for row in rows:
            chats_list.append({
                "id": str(row["id"]),
                "title": row["title"],
                "createdAt": row["created_at"].isoformat() if row["created_at"] else None,
                "messages": [
                    {"id": str(uuid.uuid4()), "role": "user", "content": row["user_message"]},
                    {"id": str(uuid.uuid4()), "role": "assistant", "content": row["assistant_message"]}
                ]
            })
        print(f"[BACKEND] Returning {len(chats_list)} chat for user {user['uid']}")
        return chats_list
    except Exception as e:
        print("[BACKEND] Exception in /chat endpoint:", str(e))
        traceback.print_exc()
        return JSONResponse({"status": "error", "detail": str(e)}, status_code=500)


# 💾 Save chat (insert or update)
class SaveChatRequest(BaseModel):
    chat_id: str
    title: str
    messages: list

@app.post("/chat/save")
async def save_chat(request: Request, user=Depends(authenticate_user)):
    data = await request.json()
    print("[BACKEND] Received /chat/save data:", data)
    print("[BACKEND] Authenticated user:", user)
    chat_id = data.get("chat_id")
    title = data.get("title")
    messages = data.get("messages")
    user_message = ""
    assistant_message = ""
    if messages and len(messages) >= 2:
        user_message = messages[-2]["content"]
        assistant_message = messages[-1]["content"]
    elif messages and len(messages) == 1:
        user_message = messages[0]["content"]
    try:
        # UPSERT: Insert or update on conflict (id, user_id)
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        now = datetime.datetime.utcnow()
        upsert_stmt = pg_insert(chat).values(
            id=chat_id,
            user_id=user["uid"],
            title=title,
            user_message=user_message,
            assistant_message=assistant_message,
            created_at=now
        ).on_conflict_do_update(
            index_elements=[chat.c.id],
            set_={
                "user_id": user["uid"],
                "title": title,
                "user_message": user_message,
                "assistant_message": assistant_message,
                "created_at": now
            }
        )
        upsert_stmt = upsert_stmt.returning(chat)
        result = await database.fetch_one(upsert_stmt)
        print("[BACKEND] Upsert result (inserted/updated row):", result)
        # Debug: fetch all chat to confirm insert
        try:
            all_chat = await database.fetch_all(chat.select())
            print(f"[DEBUG] All chat in DB after save: {all_chat}")
        except Exception as db_debug_exc:
            print("[DEBUG] Error fetching all chats:", db_debug_exc)
        return {"status": "saved", "row": dict(result) if result else None}
    except Exception as e:
        import traceback
        print("[ERROR] Exception in /chat/save:", e)
        traceback.print_exc()
        return JSONResponse({"status": "error", "detail": str(e)}, status_code=500)

# 🧹 Delete chat by ID
@app.delete("/chat/{chat_id}/delete")
async def delete_chat(chat_id: str):
    query = chat.delete().where(chat.c.id == chat_id)
    await database.execute(query)
    return {"status": "deleted"}

# 🚀 Generate via /generate-architecture-stream/
from stream_utils import stream_blueprint_ai
from fastapi.responses import StreamingResponse

@app.post("/generate-architecture-stream/")
def generate_architecture(request: ProductIdea):
    return StreamingResponse(
        stream_blueprint_ai(request.title),
        media_type="text/event-stream"
    )

def run_blueprint_ai(product_idea: str):
    print("\n🧠 Starting Blueprint AI Pipeline...\n")
    partials = {}
    try:
        print("🔍 Running Research Agent...")
        research_agent = ResearchAgent()
        research_summary = research_agent.run(product_idea)
        print("\n✅ Research Summary:\n", research_summary)
        partials["research_summary"] = research_summary

        print("🤩 Running Feature Parser Agent...")
        feature_parser = FeatureParserAgent()
        parsed_features = feature_parser.run(research_summary)
        print("\n✅ Parsed Features:\n", parsed_features)
        partials["parsed_features"] = parsed_features

        print("🏗️ Running Architecture Planner Agent...")
        architecture_planner = ArchitecturePlannerAgent()
        architecture_plan = architecture_planner.run(parsed_features)
        print("\n✅ Architecture Plan:\n", architecture_plan)
        partials["architecture_plan"] = architecture_plan

        print("🧱 Running Tech Stack Selector Agent...")
        tech_stack_selector = TechStackSelectorAgent()
        tech_stack = tech_stack_selector.run(architecture_plan)
        print("\n✅ Tech Stack:\n", tech_stack)
        partials["tech_stack"] = tech_stack

        print("🔐 Running Security & Infrastructure Agent...")
        security_infra_agent = SecurityInfraAgent()
        security_recommendations = security_infra_agent.run(architecture_plan)
        print("\n✅ Security Recommendations:\n", security_recommendations)
        partials["security_recommendations"] = security_recommendations

        return partials
    except Exception as e:
        # Return whatever partials are available, plus error
        partials["error"] = str(e)
        return partials
