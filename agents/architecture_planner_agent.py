from utils.llm import call_llm

class ArchitecturePlannerAgent:
    def run(self, parsed_features: str) -> str:
        prompt = f"""
You are a Systems Architect.

Given the following product features:

{parsed_features}

Design a scalable system architecture. Include:
- Major components (frontend, backend, databases, APIs, etc.)
- Key interactions and responsibilities

Do NOT provide a Mermaid.js diagram or any diagram. Only return a clear, structured explanation of the architecture in markdown text.
"""
        return call_llm(prompt)
