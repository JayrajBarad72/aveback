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
        self.email      = os.getenv("ZOHO_EMAIL", "sales@aventrixtechnologies.com")
        self.resend_key = os.getenv("RESEND_API_KEY", "")

    def generate_email(self, lead: dict) -> dict:
        contact = lead.get("contact_name") or "there"
        first_name = contact.split()[0] if contact and contact != "there" else "there"
        title = lead.get("title", "")
        industry = lead.get("industry", "")
        country = lead.get("country", "Global")
        company = lead.get("company", "")
        notes = lead.get("notes", "")

        prompt = f"""You are Alex, a sales rep for SecureAI Gateway - an on-premise AI security platform.

Write a cold outreach email to this specific person:

Name: {first_name}
Job Title: {title}
Company: {company}
Industry: {industry}
Country: {country}
What we know about them: {notes}

Your job: Write an email that feels like it was written SPECIFICALLY for this person.
Not a template. Not a generic pitch. A real email from one professional to another.

Think about:
- What does someone with this exact title worry about at night?
- What specific AI risk does their industry face?
- What would make THEM personally look bad if something went wrong?

SUBJECT LINE:
- Max 7 words
- Specific to their situation
- Creates curiosity or speaks to a real fear they have
- No generic phrases

EMAIL BODY (150 words max):
- First line: one sharp, specific observation about their situation. No greeting fluff.
- Second paragraph: what the real risk is for someone in their exact role
- Third paragraph: what SecureAI Gateway does, in plain language. One sentence max per idea.
- Fourth paragraph: one credibility point or fact
- Fifth paragraph: mention our blog at aventrixtechnologies.com/blog - one natural sentence
- Last line: one soft question to start a conversation

SIGNATURE (copy exactly, no changes):
Alex
SecureAI Gateway | Aventrix Technologies
aventrixtechnologies.com

CRITICAL: Never use em dashes or hyphens in the email body. Write full sentences instead.
CRITICAL: The signature must be exactly as shown above. Do not add "Team" or change anything.

STRICT RULES:
- End every email body with this exact line: "Book a 15-minute demo directly: https://calendly.com/aventrixtechnologies-info"
- Never use the word "ensure"
- Never use "I hope this finds you well" or any variation
- Never use "I wanted to reach out"
- Never use dashes like this: -  or this: --
- No bullet points
- No exclamation marks
- No bold or caps for emphasis
- Write how a smart, confident person talks
- Every sentence must be about THEM, not about us
- The product is mentioned briefly, not pitched heavily

Return JSON only, no markdown:
{{"subject": "...", "body": "..."}}"""

        result = self.think(prompt)
        try:
            clean = result.replace("```json","").replace("```","").strip()
            parsed = json.loads(clean)
            # Clean up AI bad habits
            for key in ["subject", "body"]:
                if key in parsed:
                    parsed[key] = parsed[key].replace(" — ", " ").replace("—", "")
                    parsed[key] = parsed[key].replace(" -- ", " ").replace("--", "")
                    parsed[key] = parsed[key].replace("Best regards,", "")
                    parsed[key] = parsed[key].replace("Kind regards,", "")
                    parsed[key] = parsed[key].replace("SecureAI Gateway Team", "SecureAI Gateway")
            return parsed
        except:
            # Simple fallback - fully personalised to their role
            body = f"""Hi {first_name},

Most {title}s at {industry} companies are dealing with the same problem right now. Their teams are using AI tools daily and nobody has visibility into what data is being shared or where it goes.

SecureAI Gateway puts that control back in your hands. It runs on your own server, scans every AI prompt before it reaches any external provider, and keeps a full audit log. Your team keeps using the AI tools they rely on. You get visibility and control.

We wrote something about this recently that might be worth your time: aventrixtechnologies.com/blog

Would a quick call make sense this week?

Alex
SecureAI Gateway | Aventrix Technologies
aventrixtechnologies.com"""
            return {
                "subject": f"AI visibility at {company}",
                "body": body
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

            # HTML version
            paragraphs = "".join(
                f'<p style="margin:0 0 18px 0;font-size:16px;line-height:1.75;color:#1a1a1a">{p.strip()}</p>'
                for p in plain_body.split("\n\n") if p.strip()
            )
            html_body = """<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f4f4;font-family:Georgia,serif">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f4;padding:32px 0">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08)">
<tr><td style="padding:40px 48px 32px">""" + paragraphs + """</td></tr>
<tr><td style="padding:0 48px 32px">
<table width="100%" cellpadding="0" cellspacing="0" style="border-top:1px solid #eeeeee;padding-top:24px">
<tr>
<td style="vertical-align:top">
  <p style="margin:0;font-size:14px;font-weight:bold;color:#1a1a1a">Alex</p>
  <p style="margin:4px 0 2px;font-size:13px;color:#555555">SecureAI Gateway | Aventrix Technologies</p>
  <a href="https://aventrixtechnologies.com" style="font-size:13px;color:#378ADD;text-decoration:none">aventrixtechnologies.com</a>
</td>
<td style="vertical-align:top;text-align:right">
  <a href="https://aventrixtechnologies.com/blog.html" style="display:block;font-size:12px;color:#378ADD;text-decoration:none;margin-bottom:6px">Read our Blog</a>
  <a href="https://aventrixtechnologies.com/features.html" style="display:block;font-size:12px;color:#378ADD;text-decoration:none;margin-bottom:6px">Product Features</a>
  <a href="https://calendly.com/aventrixtechnologies-info" style="display:block;font-size:12px;color:#378ADD;text-decoration:none;margin-bottom:6px;font-weight:bold">Book a 15-Min Demo</a>
  <a href="https://aventrixtechnologies.com/contact.html" style="display:block;font-size:12px;color:#378ADD;text-decoration:none;margin-bottom:6px">Contact Us</a>
  <a href="https://wa.me/919104277272" style="display:block;font-size:12px;color:#25D366;text-decoration:none">WhatsApp</a>
</td>
</tr>
</table>
</td></tr>
<tr><td style="background:#f9f9f9;padding:16px 48px;border-top:1px solid #eeeeee">
  <p style="margin:0;font-size:11px;color:#aaaaaa">To unsubscribe reply with unsubscribe and we will remove you immediately.</p>
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""
            msg.attach(MIMEText(html_body, "html"))

            # Send via Resend API (HTTP - works on Render, SMTP is blocked)
            import resend
            resend.api_key = self.resend_key
            response = resend.Emails.send({
                "from": f"Alex - SecureAI Gateway <{self.email}>",
                "to": [lead.email],
                "subject": email_content["subject"],
                "text": plain_body,
                "html": html_body,
                "reply_to": self.email,
                "tags": [
                    {"name": "lead_id", "value": str(lead_id)},
                    {"name": "industry", "value": lead.industry or "unknown"},
                    {"name": "company", "value": (lead.company or "unknown")[:50]}
                ]
            })
            if not response.get("id"):
                raise Exception(f"Resend failed: {response}")
            self.log("send_email", f"Sent via Resend to {lead.email} id={response['id']}")

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
