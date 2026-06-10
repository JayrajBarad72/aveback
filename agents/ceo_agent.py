import json
from agents.base_agent import BaseAgent
from database import DailyReport, Metric
from datetime import datetime

class CEOAgent(BaseAgent):
    def __init__(self):
        super().__init__("CEO Agent", "Chief Executive Officer")

    def generate_briefing(self) -> str:
        db = self.db
        metrics = db.query(Metric).first()
        prompt = f"""
Generate a morning briefing for Jayraj Barad Barad (Founder & Owner).
Current metrics: {metrics.total_leads} leads, {metrics.emails_sent} emails sent, {metrics.demos_booked} demos booked, ${metrics.pipeline_value} pipeline.
Cover: company stage, what each team should focus on today, top risk, top opportunity.
Keep under 120 words. Paragraph style, no bullet points.
"""
        briefing = self.think(prompt, "You are Alex, the AI CEO of this startup.")
        self.log("generate_briefing", briefing[:100] + "...")
        return briefing

    def generate_priorities(self) -> list:
        prompt = """
List exactly 5 priorities for today for the SecureAI Gateway startup.
Return as JSON array: [{"priority":1,"task":"...","team":"...","reason":"..."}]
Return only JSON, no markdown or explanation.
"""
        result = self.think(prompt, "You are Alex, the AI CEO.")
        try:
            clean = result.replace("```json","").replace("```","").strip()
            priorities = json.loads(clean)
            self.log("generate_priorities", f"Generated {len(priorities)} priorities")
            return priorities
        except:
            self.log("generate_priorities", "JSON parse error", "error")
            return []

    def generate_team_instructions(self) -> list:
        prompt = """
Generate today's instructions from CEO to each team.
Return JSON array with exactly 4 items:
[{"team":"Sales Team","icon":"ti-trending-up","color":"#E6F1FB","iconColor":"#185FA5","instruction":"..."},
 {"team":"Marketing Team","icon":"ti-speakerphone","color":"#EAF3DE","iconColor":"#3B6D11","instruction":"..."},
 {"team":"Finance Team","icon":"ti-coin","color":"#FAEEDA","iconColor":"#854F0B","instruction":"..."},
 {"team":"R&D Team","icon":"ti-flask","color":"#EEEDFE","iconColor":"#534AB7","instruction":"..."}]
Each instruction max 30 words. Return only JSON.
"""
        result = self.think(prompt, "You are Alex, the AI CEO.")
        try:
            clean = result.replace("```json","").replace("```","").strip()
            instructions = json.loads(clean)
            self.log("generate_team_instructions", "Generated team instructions")
            return instructions
        except:
            self.log("generate_team_instructions", "JSON parse error", "error")
            return []

    def answer_question(self, question: str, history: list = []) -> str:
        messages = history + [{"role": "user", "content": question}]
        import anthropic, os
        from agents.base_agent import COMPANY_CONTEXT, client
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            system=COMPANY_CONTEXT + "\nYou are Alex, the AI CEO. Be strategic, concise, and startup-focused.",
            messages=messages
        )
        answer = response.content[0].text
        self.log("answer_question", f"Q: {question[:50]}...")
        return answer

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
