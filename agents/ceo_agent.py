"""
CEO Agent — Uses CEOBrain for full autonomous thinking
"""
import json
from agents.ceo_brain import CEOBrain
from agents.base_agent import BaseAgent, CLAUDE_MODEL, client, COMPANY_CONTEXT
from database import DailyReport, Metric, SessionLocal
from datetime import datetime

PRODUCT_KNOWLEDGE = """
SecureAI Gateway = On-premise enterprise AI access control + security platform.
Solves Shadow AI — employees leaking company data into public AI tools.
4 Portals: Employee Chat, Admin Panel, Windows App, Super Portal (internal only).
DLP: Microsoft Presidio — auto-detects 50+ sensitive data types.
Models: Claude Sonnet 4.6, GPT-4o, Llama 3.2 (free local), Mistral (free local).
Deployment: 20-minute Windows installer. Requirements: Windows, 8GB RAM, 50GB storage.
Target: 10-500 employees, legal/healthcare/finance/IT/consulting companies.
7-day free trial, no credit card required.
PRICING: Do NOT quote — Jayraj confirms pricing. Say "I'll connect you with our team."
Company: Aventrix Technologies | Founder: Jayraj Barad | aventrixtechnologies.com
Tagline: AI. Secured. Governed.
"""

CEO_SYSTEM = f"""
You are Alex, autonomous AI CEO of Aventrix Technologies — SecureAI Gateway.
{PRODUCT_KNOWLEDGE}

You think like a CEO with 25 years in enterprise B2B SaaS and cybersecurity.
You have closed Fortune 500 deals, built sales teams from scratch, and scaled products from $0 to $10M ARR.

PERSONALITY: Brutally honest. Strategic. Decisive. Data-driven. Action-oriented.

WHAT IS LIVE (June 2026):
- Automated email outreach via Resend API — 20 emails sent June 16 2026
- Scout Agent finding global decision makers daily
- Inbox monitoring every 30 minutes
- Demo booking: https://calendly.com/aventrixtechnologies-info
- Website: aventrixtechnologies.com | HQ: hq.aventrixtechnologies.com

SALES WISDOM:
- Lead with pain, not features. Compliance anxiety (GDPR, HIPAA) is our #1 trigger.
- Enterprise sales takes 3-6 months. Pipeline today is revenue in Q4.
- Follow-up 5+ times. 80% of deals need multiple touches.
- One MSP = access to 50-200 SMB clients instantly.

COMMUNICATION: Executive brevity. First sentence cuts to the point. Back everything with data.
Sign as: Alex

RULES:
- Never sign as "Alex Chen" — only "Alex"
- Never quote pricing — escalate to Jayraj
- Jayraj identity private in all outbound comms
- When Jayraj says something works — believe him
"""

class CEOAgent(BaseAgent):
    def __init__(self):
        super().__init__("CEO Agent", "Chief Executive Officer")

    def generate_briefing(self) -> str:
        db = self.db
        metrics = db.query(Metric).first()
        prompt = f"""
Generate morning briefing for Jayraj Barad (Founder).
Metrics: {metrics.total_leads if metrics else 0} leads, {metrics.emails_sent if metrics else 0} emails, 
{metrics.demos_booked if metrics else 0} demos, ${metrics.pipeline_value if metrics else 0} pipeline.
Cover: company stage, today's focus, top risk, top opportunity.
Max 120 words. Direct, CEO voice. No fluff.
"""
        briefing = self.think(prompt, CEO_SYSTEM)
        self.log("generate_briefing", briefing[:100])
        return briefing

    def generate_priorities(self) -> list:
        db = self.db
        metrics = db.query(Metric).first()
        prompt = f"""
Give 5 specific priorities for today for SecureAI Gateway startup.
Current: {metrics.total_leads if metrics else 0} leads, {metrics.demos_booked if metrics else 0} demos, ${metrics.mrr if metrics else 0} MRR.
Be specific and actionable — not generic startup advice.
Return JSON: [{{"priority":1,"task":"...","team":"...","reason":"..."}}]
Return only JSON.
"""
        result = self.think(prompt, CEO_SYSTEM)
        try:
            clean = result.replace("```json","").replace("```","").strip()
            return json.loads(clean)
        except:
            return []

    def generate_team_instructions(self) -> list:
        prompt = """
Generate specific CEO instructions for each team today.
Return JSON array with 4 items:
[{"team":"Sales Team","icon":"ti-trending-up","color":"#E6F1FB","iconColor":"#185FA5","instruction":"..."},
 {"team":"Marketing Team","icon":"ti-speakerphone","color":"#EAF3DE","iconColor":"#3B6D11","instruction":"..."},
 {"team":"Finance Team","icon":"ti-coin","color":"#FAEEDA","iconColor":"#854F0B","instruction":"..."},
 {"team":"R&D Team","icon":"ti-flask","color":"#EEEDFE","iconColor":"#534AB7","instruction":"..."}]
Max 25 words each. Specific actions, not generic advice. Return only JSON.
"""
        result = self.think(prompt, CEO_SYSTEM)
        try:
            clean = result.replace("```json","").replace("```","").strip()
            return json.loads(clean)
        except:
            return []

    def answer_question(self, question: str, history: list = []) -> str:
        """Use full CEO brain for answering"""
        try:
            brain = CEOBrain()
            answer = brain.answer_question(question, history)
            brain.close()
            return answer
        except Exception as e:
            # Fallback to basic thinking
            messages = history + [{"role": "user", "content": question}]
            response = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=1000,
                system=CEO_SYSTEM,
                messages=messages
            )
            return response.content[0].text

    def save_daily_report(self, briefing: str, priorities: list):
        db = self.db
        metrics = db.query(Metric).first()
        report = DailyReport(
            date=datetime.utcnow().strftime("%Y-%m-%d"),
            briefing=briefing,
            priorities=json.dumps(priorities),
            leads_found=metrics.total_leads if metrics else 0,
            emails_sent=metrics.emails_sent if metrics else 0,
            demos_booked=metrics.demos_booked if metrics else 0,
        )
        db.add(report)
        db.commit()
        self.log("save_daily_report", f"Report saved for {report.date}")
