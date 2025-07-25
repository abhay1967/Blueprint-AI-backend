from utils.llm import call_llm

class TechStackSelectorAgent:
    def run(self, architecture_plan: str) -> str:
        prompt = f"""
You are a Tech Stack Strategist.

Given the following system architecture plan:

{architecture_plan}

Recommend:
- Programming languages
- Frameworks/libraries (frontend & backend)
- Database(s)
- DevOps tools
- Any LLM or vector DBs if needed

Output your answer as clear, concise bullet points grouped by component type. Do NOT use tables or markdown tables. Use plain markdown lists for each group, with bolded group headings. Example:

**Frontend Recommendations:**
- Framework: React.js
- Libraries: Axios, Redux, React Router

**Backend Recommendations:**
- Language: Node.js
- Framework: Express.js
- Libraries: JWT, Swagger

**Database Recommendations:**
- Relational: PostgreSQL
- NoSQL: MongoDB
- Caching: Redis

"""
        return call_llm(prompt)
