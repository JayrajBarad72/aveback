import os
import anthropic
from database import SessionLocal, AgentLog
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

COMPANY_CONTEXT = """
You are an AI agent working for Aventrix Technologies.
Product: SecureAI Gateway — Enterprise AI access control and security SaaS.
Features: AI access governance, DLP protection, usage tracking, multi-model support (Claude, GPT, Gemini), audit logging, policy enforcement.
Target: IT, Healthcare, Finance, R&D companies, under 1000 employees, Global.
Founder: Jayraj Barad — Founder & Owner of Aventrix Technologies.
Company tagline: "AI. Secured. Governed."
IMPORTANT RULES:
- In outbound emails/marketing: NEVER mention founder name, location (Ahmedabad/India), or personal details
- Email signature must be: "SecureAI Gateway Team | Aventrix Technologies | aventrixtechnologies.com"
- Only reveal founder identity when Jayraj personally connects with a client
- Always be concise, professional, and results-focused.
"""

class BaseAgent:
    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role
        self.db = SessionLocal()

    def think(self, prompt: str, system_extra: str = "") -> str:
        system = COMPANY_CONTEXT + "\n" + system_extra
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
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
