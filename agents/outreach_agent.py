import os
import ssl
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from agents.base_agent import BaseAgent
from database import Lead, Email, Metric
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class OutreachAgent(BaseAgent):
    def __init__(self):
        super().__init__("Outreach Agent", "Email Sender")
        self.smtp_host = os.getenv("ZOHO_SMTP_HOST", "smtp.zeptomail.in")
        self.smtp_port = int(os.getenv("ZOHO_SMTP_PORT", 465))
        self.email     = os.getenv("ZOHO_EMAIL", "sales@aventrixtechnologies.com")
        self.password  = os.getenv("ZOHO_APP_PASSWORD")

    def generate_email(self, lead: dict) -> dict:
        contact = lead.get("contact_name") or "there"
        first_name = contact.split()[0] if contact and contact != "there" else "there"
        prompt = f"""
Write a cold outreach email for this lead:
Company: {lead.get('company')}
Contact: {contact} ({lead.get('title','Decision Maker')})
Industry: {lead.get('industry')}
Country: {lead.get('country')}
Why they need SecureAI Gateway: {lead.get('notes', 'AI security and access control')}

Rules:
- Subject: short, curiosity-driven, NOT spammy
- Opening: personalized to their industry pain point
- Body: 3 short paragraphs, max 100 words total
- Pain point: uncontrolled AI usage, data leaks via ChatGPT/Copilot
- Solution: SecureAI Gateway — control, monitor, secure all AI tools
- CTA: soft ask for 15 min call, no pressure
- Signature: "SecureAI Gateway Team | Aventrix Technologies | aventrixtechnologies.com" — NO personal names, NO location

Return JSON only: {{"subject":"...","body":"..."}}
"""
        result = self.think(prompt)
        try:
            clean = result.replace("```json","").replace("```","").strip()
            return json.loads(clean)
        except:
            return {"subject": "Quick question about AI security at " + lead.get("company","your company"), "body": result}

    def send_email(self, lead_id: int) -> bool:
        db = self.db
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            self.log("send_email", f"Lead {lead_id} not found", "error")
            return False
        if not lead.email:
            self.log("send_email", f"No email for lead {lead_id}", "error")
            return False

        lead_dict = {
            "company": lead.company,
            "contact_name": lead.contact_name or lead.contact_name or "there",
            "title": "",
            "email": lead.email,
            "industry": lead.industry,
            "country": lead.country,
            "notes": lead.notes
        }

        email_content = self.generate_email(lead_dict)

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = email_content["subject"]
            msg["From"]    = f"SecureAI Gateway Team <{self.email}>"
            msg["To"]      = lead.email
            msg["Reply-To"] = self.email

            # Plain text version
            msg.attach(MIMEText(email_content["body"], "plain"))

            # Send via SSL
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, context=context) as server:
                server.login("emailapikey", self.password)
                server.sendmail(self.email, lead.email, msg.as_string())

            # Save record
            email_record = Email(
                lead_id=lead_id,
                subject=email_content["subject"],
                body=email_content["body"],
                status="sent",
                sent_at=datetime.utcnow()
            )
            db.add(email_record)
            lead.status = "contacted"
            db.commit()

            # Update metrics
            metrics = db.query(Metric).first()
            if metrics:
                metrics.emails_sent += 1
                metrics.updated_at = datetime.utcnow()
                db.commit()

            self.log("send_email", f"Email sent to {lead.email}")
            return True

        except Exception as e:
            self.log("send_email", str(e), "error")
            return False

    def run_daily_outreach(self, limit: int = 20) -> dict:
        db = self.db
        leads = db.query(Lead).filter(
            Lead.status == "new",
            Lead.email != "",
            Lead.score >= 80
        ).order_by(Lead.score.desc()).limit(limit).all()

        sent = 0
        failed = 0
        skipped = 0
        for lead in leads:
            if not lead.email or "@" not in lead.email:
                skipped += 1
                continue
            success = self.send_email(lead.id)
            if success:
                sent += 1
            else:
                failed += 1

        self.log("run_daily_outreach", f"Sent:{sent} Failed:{failed} Skipped:{skipped}")
        return {"sent": sent, "failed": failed, "skipped": skipped}

    def preview_email(self, lead_id: int) -> dict:
        """Preview email without sending"""
        db = self.db
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            return {}
        lead_dict = {
            "company": lead.company,
            "contact_name": lead.contact_name or lead.contact_name or "there",
            "email": lead.email,
            "industry": lead.industry,
            "country": lead.country,
            "notes": lead.notes
        }
        return self.generate_email(lead_dict)

    def get_email_history(self) -> list:
        db = self.db
        emails = db.query(Email).order_by(Email.created_at.desc()).limit(50).all()
        return [{"id":e.id,"lead_id":e.lead_id,"subject":e.subject,
                 "status":e.status,"sent_at":str(e.sent_at)} for e in emails]
