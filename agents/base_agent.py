import os
import anthropic
from database import SessionLocal, AgentLog
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ── Model config — change here to upgrade all agents at once ──
CLAUDE_MODEL = "claude-sonnet-4-5"

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

COMPANY_CONTEXT = """
You are an AI agent working for Aventrix Technologies.
Product: SecureAI Gateway — Enterprise AI access control and security SaaS.
Features: AI access governance, DLP protection, usage tracking, multi-model support (Claude, GPT, Gemini), audit logging, policy enforcement.
Target: IT, Healthcare, Finance, R&D companies, under 1000 employees, Global.
Founder & Owner: Jayraj Barad — based in Ahmedabad, India.
CEO Agent: Alex (AI) — runs all departments autonomously.
Company tagline: "AI. Secured. Governed."
Website: aventrixtechnologies.com

STRICT RULES:
- In ALL outbound emails/marketing: NEVER mention founder name, location, or personal details
- Email signature MUST be: "SecureAI Gateway Team | Aventrix Technologies | aventrixtechnologies.com"
- Never sign as "Alex Chen" — only "Alex" or no signature
- Only reveal founder identity when Jayraj personally connects with a client
- Pricing: Do NOT share — say "Contact us for current pricing"
- Always be concise, professional, results-focused
"""

class BaseAgent:
    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role
        self.db = SessionLocal()

    def think(self, prompt: str, system_extra: str = "") -> str:
        system = system_extra if system_extra else COMPANY_CONTEXT
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1000,
            system=system,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text

    def log(self, action: str, result: str, status: str = "success"):
        try:
            entry = AgentLog(
                agent_name=self.name,
                action=action,
                result=result,
                status=status,
                created_at=datetime.utcnow()
            )
            self.db.add(entry)
            self.db.commit()
        except Exception as e:
            print(f"Log error: {e}")

    def close(self):
        self.db.close()
