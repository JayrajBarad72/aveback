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
            compliance_angle = "GDPR Article 25 requires data protection by design. Every AI prompt your team sends to ChatGPT or Claude passes through servers outside the EU - a potential GDPR violation."
        elif industry == "Healthcare":
            compliance_angle = "HIPAA requires that patient data never reaches third-party AI servers without a BAA agreement - which OpenAI and Anthropic don't offer by default."
        elif industry == "Finance":
            compliance_angle = "Financial regulators increasingly flag AI tools that send customer data to external servers. PCI-DSS and SOC 2 compliance is at risk with uncontrolled AI usage."
        elif industry == "Legal":
            compliance_angle = "Attorney-client privilege is at risk when lawyers use ChatGPT - client names and case details are sent to OpenAI servers and stored indefinitely."
        else:
            compliance_angle = "Every prompt your team sends to ChatGPT or Claude leaves your network - customer data, financials, and IP are stored on third-party servers with no audit trail."

        prompt = f"""Write a compelling cold outreach email for SecureAI Gateway that people actually want to read.

Lead details:
- Name: {first_name} ({title})
- Company: {company}
- Industry: {industry}
- Country: {country}
- Context: {notes[:200]}

Compliance angle: {compliance_angle}

SUBJECT LINE rules:
- Max 7 words
- Must create curiosity or speak to a specific fear
- Examples of good subjects:
  * "Is {company}'s AI usage GDPR compliant?"
  * "Your team is using ChatGPT. Here's the risk."
  * "How {industry} firms are securing AI in 2026"
  * "Quick question about AI security at {company}"
- NO clickbait, NO ALL CAPS, NO exclamation marks

EMAIL BODY structure (150-180 words max):

1. HOOK (1 sentence) - a specific, uncomfortable truth about their situation
   Example: "Right now, every ChatGPT prompt your team sends leaves your network permanently."

2. PROBLEM (2-3 sentences) - make it real and specific to their role/industry
   Use the compliance angle. Make them feel the risk.

3. SOLUTION (2-3 sentences) - introduce SecureAI Gateway naturally
   "SecureAI Gateway is an on-premise AI platform that sits between your team and any AI model."
   Mention: DLP protection blocks sensitive data, full audit logs, runs on their server, 20-min setup.

4. PROOF/CREDIBILITY (1-2 sentences) - add one compelling fact
   Example: "83% of companies have zero controls over employee AI usage. The ones that do are building an unfair advantage."

5. BLOG/RESOURCES (1 sentence) - add our website and blog naturally
   Example: "We've written about exactly this at aventrixtechnologies.com/blog - worth 5 minutes of your time."

6. CTA (1 sentence) - soft, no pressure
   Example: "Would a 15-minute call this week make sense, {first_name}?"

7. SIGNATURE:
Alex
SecureAI Gateway | Aventrix Technologies
aventrixtechnologies.com
📖 Blog: aventrixtechnologies.com/blog.html
🛡️ Learn more: aventrixtechnologies.com/features.html

Rules:
- Write like a real person, not a marketer
- Short paragraphs, max 2-3 sentences each
- NO bullet points in the email body
- NO generic phrases like "I hope this email finds you well"
- NO "I wanted to reach out" or "I came across your profile"
- Make the reader feel slightly uncomfortable about their current situation
- Then immediately offer relief

Return JSON only - no markdown:
{{"subject": "...", "body": "..."}}"""

        result = self.think(prompt)
        try:
            clean = result.replace("```json","").replace("```","").strip()
            return json.loads(clean)
        except:
            return {
                "subject": f"Quick question about AI security at {company}",
                "body": f"""Hi {first_name},

{compliance_angle}

That's the reality for most {industry} companies right now - and the exposure grows every day employees use AI tools without oversight.

SecureAI Gateway is an on-premise platform that sits between your team and any AI model (Claude, ChatGPT, or free local AI). Every prompt is scanned for sensitive data before it leaves your network. Full audit logs. Zero data stored externally. Takes 20 minutes to deploy on your own server.

83% of companies have no controls over employee AI usage. The firms building those controls now are creating a serious compliance advantage.

We've written about how {industry} companies are handling this at aventrixtechnologies.com/blog - worth a quick read.

Would a 15-minute call this week make sense, {first_name}?

Alex
SecureAI Gateway | Aventrix Technologies
aventrixtechnologies.com
📖 Blog: aventrixtechnologies.com/blog.html
🛡️ Features: aventrixtechnologies.com/features.html"""
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
            plain_body = email_content["body"]
            msg.attach(MIMEText(plain_body, "plain"))

            # HTML version - looks premium in inbox
            html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family:Georgia,serif;max-width:600px;margin:0 auto;padding:20px;color:#1a1a1a;line-height:1.7;font-size:16px">
{"".join(f'<p style="margin:0 0 16px 0">{p.strip()}</p>' for p in plain_body.split(chr(10)+chr(10)) if p.strip())}
<hr style="border:none;border-top:1px solid #e0e0e0;margin:28px 0">
<table style="width:100%">
<tr>
<td style="font-size:13px;color:#666">
  <strong style="color:#1a1a1a;font-size:14px">Alex</strong><br>
  SecureAI Gateway | Aventrix Technologies<br>
  <a href="https://aventrixtechnologies.com" style="color:#378ADD;text-decoration:none">aventrixtechnologies.com</a>
</td>
<td style="text-align:right;font-size:12px;color:#888">
  <a href="https://aventrixtechnologies.com/blog.html" style="color:#378ADD;text-decoration:none;display:block;margin-bottom:4px">📖 Read our Blog</a>
  <a href="https://aventrixtechnologies.com/features.html" style="color:#378ADD;text-decoration:none;display:block;margin-bottom:4px">🛡️ Product Features</a>
  <a href="https://aventrixtechnologies.com/contact.html" style="color:#378ADD;text-decoration:none;display:block">📅 Book a Demo</a>
</td>
</tr>
</table>
<p style="font-size:11px;color:#aaa;margin-top:20px">
To unsubscribe, reply with "unsubscribe" and we'll remove you immediately.
</p>
</body>
</html>"""
            msg.attach(MIMEText(html_body, "html"))

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
