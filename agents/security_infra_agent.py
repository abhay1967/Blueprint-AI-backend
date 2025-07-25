from utils.llm import call_llm

class SecurityInfraAgent:
    def run(self, architecture_plan: str) -> str:
        prompt = f"""
You are a Security & Infrastructure Specialist.

Based on this architecture plan:

{architecture_plan}

Provide:
- Security best practices for each component
- Infrastructure guidelines (cloud, CI/CD, scaling, observability)

Return your response in a markdown list format.
"""
        return call_llm(prompt)
