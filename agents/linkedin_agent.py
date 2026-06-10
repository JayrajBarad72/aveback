"""
LinkedIn Agent — Generates personalized LinkedIn outreach messages
for each lead. Sales team uses these to manually send or 
via LinkedIn automation tools.
"""
import json
from agents.base_agent import BaseAgent
from database import Lead, LeadActivity
from datetime import datetime

class LinkedInAgent(BaseAgent):
    def __init__(self):
        super().__init__("LinkedIn Agent", "Social Outreach")

    def generate_connection_request(self, lead_id: int) -> str:
        """Generate LinkedIn connection request message (300 chars max)"""
        db = self.db
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            return ""

        prompt = f"""
Write a LinkedIn connection request message for:
Name: {lead.contact_name}
Company: {lead.company}
Industry: {lead.industry}
Title context: {lead.notes or 'IT/Security decision maker'}

Rules:
- Max 300 characters (LinkedIn limit)
- Personalized to their industry
- No pitching yet — just connecting
- Professional and genuine
- NO personal names in sender info
- From: SecureAI Gateway team

Return only the message text, nothing else.
"""
        return self.think(prompt)

    def generate_followup_message(self, lead_id: int) -> str:
        """Generate LinkedIn follow-up after connection accepted"""
        db = self.db
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            return ""

        prompt = f"""
Write a LinkedIn follow-up message after connection was accepted.
Lead: {lead.contact_name} at {lead.company} ({lead.industry})
Notes: {lead.notes or 'AI security needs'}

Rules:
- Max 500 characters
- Soft intro to SecureAI Gateway
- Focus on their pain point (shadow AI, data leaks)
- End with a question to start conversation
- NO pricing, NO hard sell
- Professional and conversational

Return only the message text.
"""
        return self.think(prompt)

    def generate_batch_messages(self, industry: str = "IT", limit: int = 10) -> list:
        """Generate LinkedIn messages for multiple leads"""
        db = self.db
        leads = db.query(Lead).filter(
            Lead.industry == industry,
            Lead.status.in_(["new","contacted"]),
            Lead.score >= 70
        ).order_by(Lead.score.desc()).limit(limit).all()

        messages = []
        for lead in leads:
            connection_msg = self.generate_connection_request(lead.id)
            messages.append({
                "lead_id": lead.id,
                "company": lead.company,
                "contact": lead.contact_name,
                "email": lead.email,
                "score": lead.score,
                "connection_request": connection_msg,
                "linkedin_url": lead.linkedin or ""
            })

            # Log activity
            activity = LeadActivity(
                lead_id=lead.id,
                activity="LinkedIn message generated",
                description=connection_msg[:100]
            )
            db.add(activity)

        db.commit()
        self.log("generate_batch_messages", f"Generated {len(messages)} LinkedIn messages for {industry}")
        return messages
