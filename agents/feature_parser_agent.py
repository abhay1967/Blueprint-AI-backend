from utils.llm import call_llm

class FeatureParserAgent:
    def run(self, research_summary: str) -> str:
        prompt = f"""
You are a Product Feature Analyst.

Given this research summary:

{research_summary}

Extract and list:
- Core features the product must have
- Any optional or innovative features
- User flow or UX implications

Return in structured markdown format with headings.
"""
        return call_llm(prompt)
