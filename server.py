from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from agents.research_agent import ResearchAgent
from agents.feature_parser_agent import FeatureParserAgent
from agents.architecture_planner_agent import ArchitecturePlannerAgent
from agents.tech_stack_selector_agent import TechStackSelectorAgent
from agents.security_infra_agent import SecurityInfraAgent

app = FastAPI(title="Blueprint AI API", version="1.0.0")

class ProductIdeaRequest(BaseModel):
    product_idea: str

@app.post("/blueprint")
def run_blueprint(request: ProductIdeaRequest):
    try:
        # Step 1: Research Agent
        research_agent = ResearchAgent()
        research_summary = research_agent.run(request.product_idea)

        # Step 2: Feature Parser Agent
        feature_parser = FeatureParserAgent()
        parsed_features = feature_parser.run(research_summary)

        # Step 3: Architecture Planner Agent
        architecture_planner = ArchitecturePlannerAgent()
        architecture_plan = architecture_planner.run(parsed_features)

        # Step 4: Tech Stack Selector Agent
        tech_stack_selector = TechStackSelectorAgent()
        tech_stack = tech_stack_selector.run(architecture_plan)

        # Step 5: Security & Infra Expert Agent
        security_infra_agent = SecurityInfraAgent()
        security_recommendations = security_infra_agent.run(architecture_plan)

        return {
            "research_summary": research_summary,
            "parsed_features": parsed_features,
            "architecture_plan": architecture_plan,
            "tech_stack": tech_stack,
            "security_recommendations": security_recommendations
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health():
    return {"status": "ok"}
