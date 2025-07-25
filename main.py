# 📁 File: main.py

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
import os
from agents.research_agent import ResearchAgent
from agents.feature_parser_agent import FeatureParserAgent
from agents.architecture_planner_agent import ArchitecturePlannerAgent
from agents.tech_stack_selector_agent import TechStackSelectorAgent
from agents.security_infra_agent import SecurityInfraAgent

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory chat store (replace with database in production)
chat_store = {}

# 🧾 Request schema
class ProductIdea(BaseModel):
    product_idea: str

# 📄 Response schema
class Chat(BaseModel):
    id: str
    product_idea: str
    response: str

# 🔧 Health check
@app.get("/health")
def health_check():
    return {"status": "ok"}

# 🧠 AI Architecture pipeline endpoint (non-streaming)
@app.post("/blueprint")
def run_blueprint(request: ProductIdea):
    result = {}
    error = None
    try:
        result = run_blueprint_ai(request.product_idea)
        chat_id = str(uuid.uuid4())
        chat_store[chat_id] = {
            "id": chat_id,
            "product_idea": request.product_idea,
            "response": result
        }
        return chat_store[chat_id]
    except Exception as e:
        # If run_blueprint_ai returns partials, use them, else just error
        if isinstance(result, dict):
            result["error"] = str(e)
            return result
        return {"error": str(e)}


# 🧾 Return all chats
@app.get("/chats")
def get_chats():
    return list(chat_store.values())

# 🧹 Delete chat by ID
@app.delete("/chat/{chat_id}/delete")
def delete_chat(chat_id: str):
    if chat_id in chat_store:
        del chat_store[chat_id]
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Chat not found")

# 🚀 Generate via /generate-architecture-stream/
from stream_utils import stream_blueprint_ai
from fastapi.responses import StreamingResponse

@app.post("/generate-architecture-stream/")
def generate_architecture(request: ProductIdea):
    return StreamingResponse(
        stream_blueprint_ai(request.product_idea),
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
