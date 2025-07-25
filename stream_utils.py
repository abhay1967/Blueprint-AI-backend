from fastapi.responses import StreamingResponse
import json
import time

# Utility to format as SSE
def sse_format(data: dict):
    return f"data: {json.dumps(data)}\n\n"

def stream_blueprint_ai(product_idea: str):
    from agents.research_agent import ResearchAgent
    from agents.feature_parser_agent import FeatureParserAgent
    from agents.architecture_planner_agent import ArchitecturePlannerAgent
    from agents.tech_stack_selector_agent import TechStackSelectorAgent
    from agents.security_infra_agent import SecurityInfraAgent

    try:
        # 1. Research Agent
        research_agent = ResearchAgent()
        research_summary = research_agent.run(product_idea)
        yield sse_format({"agent_name": "ResearchAgent", "output": research_summary})
        time.sleep(0.2)

        # 2. Feature Parser Agent
        feature_parser = FeatureParserAgent()
        parsed_features = feature_parser.run(research_summary)
        yield sse_format({"agent_name": "FeatureParserAgent", "output": parsed_features})
        time.sleep(0.2)

        # 3. Architecture Planner Agent
        architecture_planner = ArchitecturePlannerAgent()
        architecture_plan = architecture_planner.run(parsed_features)
        yield sse_format({"agent_name": "ArchitecturePlannerAgent", "output": architecture_plan})
        time.sleep(0.2)

        # 4. Tech Stack Selector Agent
        tech_stack_selector = TechStackSelectorAgent()
        tech_stack = tech_stack_selector.run(architecture_plan)
        yield sse_format({"agent_name": "TechStackSelectorAgent", "output": tech_stack})
        time.sleep(0.2)

        # 5. Security & Infra Expert Agent
        security_infra_agent = SecurityInfraAgent()
        security_recommendations = security_infra_agent.run(architecture_plan)
        yield sse_format({"agent_name": "SecurityInfraAgent", "output": security_recommendations})
        time.sleep(0.2)

        # End of stream
        yield "data: STREAM_END\n\n"
    except Exception as e:
        # Send error as SSE
        yield sse_format({"agent_name": "Error", "output": str(e)})
        yield "data: STREAM_END\n\n"
