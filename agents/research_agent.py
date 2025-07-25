from utils.llm import call_llm

class ResearchAgent:
    def run(self, product_idea: str) -> str:
        prompt = f"""
You are a Research Expert. Your task is to analyze the market and user landscape for the following product idea:

"{product_idea}"

Provide:
- A summary of the target audience and user pain points
- Competitive analysis
- Key trends and opportunities

Return your response in clear, markdown-formatted text.
"""
        return call_llm(prompt)
