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
        title = lead.get("title", "")
        industry = lead.get("industry", "")
        country = lead.get("country", "Global")
        company = lead.get("company", "")
        notes = lead.get("notes", "")

        # Detect European leads for GDPR angle
        eu_countries = ["germany", "france", "netherlands", "spain", "italy",
                        "sweden", "denmark", "norway", "finland", "belgium",
                        "switzerland", "austria", "poland", "uk", "europe"]
        is_european = any(c in country.lower() for c in eu_countries)

        compliance_angle = ""
        if is_european or "gdpr" in notes.lower():
            compliance_angle = "GDPR Article 25 requires data protection by design. Every AI prompt your team sends to ChatGPT or Claude passes through servers outside the EU — a potential GDPR violation."
        elif industry == "Healthcare":
            compliance_angle = "HIPAA requires that patient data never reaches third-party AI servers without a BAA agreement — which OpenAI and Anthropic don't offer by default."
        elif industry == "Finance":
            compliance_angle = "Financial regulators increasingly flag AI tools that send customer data to external servers. PCI-DSS and SOC 2 compliance is at risk with uncontrolled AI usage."
        elif industry == "Legal":
            compliance_angle = "Attorney-client privilege is at risk when lawyers use ChatGPT — client names and case details are sent to OpenAI servers and stored indefinitely."
        else:
            compliance_angle = "Every prompt your team sends to ChatGPT or Claude leaves your network — customer data, financials, and IP are stored on third-party servers with no audit trail."

        prompt = f"""Write a short, genuine cold outreach email for SecureAI Gateway.

Lead details:
- Name: {first_name} ({title})
- Company: {company}
- Industry: {industry}
- Country: {country}
- Context: {notes[:200]}

Compliance angle to use: {compliance_angle}

Rules:
- Subject line: max 8 words, specific to their industry, NOT generic
- Body: max 100 words total — short is better
- Sound like a real human, NOT a marketing email
- Open with ONE specific pain point relevant to their role/industry
- Mention SecureAI Gateway once — "on-premise AI security platform"
- Mention: runs on their own server, DLP protection, 20-minute setup
- End with a simple question like "Would a 15-minute call make sense?"
- NO bullet points, NO ALL CAPS, NO exclamation marks
- Sign as: "Alex\nSecureAI Gateway Team | Aventrix Technologies"
- NO pricing

Return JSON only:
{{"subject": "...", "body": "..."}}"""

        result = self.think(prompt)
        try:
            clean = result.replace("```json","").replace("```","").strip()
            return json.loads(clean)
        except:
            return {
                "subject": f"AI data security for {company}",
                "body": f"Hi {first_name},\n\n{compliance_angle}\n\nSecureAI Gateway gives your team access to Claude and ChatGPT with full DLP protection — running on your own server. 20-minute setup, no data leaves your network.\n\nWould a 15-minute call make sense?\n\nAlex\nSecureAI Gateway Team | Aventrix Technologies | aventrixtechnologies.com"
            }


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
