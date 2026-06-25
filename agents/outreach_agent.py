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

            # HTML version — new branded template
            industry_label = (lead.industry or "Operations").strip()
            subject_line = email_content["subject"]

            # Drop the AI's plain-text signature from the HTML body since the
            # template has its own dedicated, properly-styled signature block below.
            body_for_html = plain_body
            sig_marker = "\nAlex\nSecureAI Gateway"
            if sig_marker in body_for_html:
                body_for_html = body_for_html.split(sig_marker)[0]

            paragraphs = "".join(
                f'<p style="margin:0 0 18px 0;font-size:15.5px;line-height:1.75;color:#2C2840;letter-spacing:0.1px;">{p.strip().replace(chr(10), "<br>")}</p>'
                for p in body_for_html.split("\n\n") if p.strip()
            )

            html_body = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SecureAI Gateway</title>
</head>
<body style="margin:0;padding:0;background:#eef0f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#eef0f5;padding:48px 0;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 8px 32px rgba(20,10,50,0.08);">

  <!-- Hero band -->
  <tr><td style="background:linear-gradient(135deg,#1B0F3A 0%,#3B1670 55%,#5B21B6 100%);padding:34px 44px;">
    <img src="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjQ4MCIgdmlld0JveD0iMCAwIDQwMCA0ODAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CiAgPHJlY3Qgd2lkdGg9IjQwMCIgaGVpZ2h0PSI0ODAiIGZpbGw9IiMxNTEzMUYiLz4KICA8Zz4KICAgIDxwYXRoIGQ9Ik0yMDAgNjAgTDI2MCA4NSBMMjYwIDE4MCBRMjYwIDIzMCAyMDAgMjcwIFExNDAgMjMwIDE0MCAxODAgTDE0MCA4NSBaIgogICAgICAgICAgZmlsbD0iIzNDMzQ4OSIgc3Ryb2tlPSIjQUZBOUVDIiBzdHJva2Utd2lkdGg9IjMiLz4KICAgIDxnIHN0cm9rZT0iI0VFRURGRSIgc3Ryb2tlLXdpZHRoPSIyLjUiIGZpbGw9Im5vbmUiPgogICAgICA8bGluZSB4MT0iMTc1IiB5MT0iMTU1IiB4Mj0iMjAwIiB5Mj0iMTk1Ii8+CiAgICAgIDxsaW5lIHgxPSIyMjUiIHkxPSIxNTUiIHgyPSIyMDAiIHkyPSIxOTUiLz4KICAgICAgPGxpbmUgeDE9IjE3NSIgeTE9IjE1NSIgeDI9IjIyNSIgeTI9IjE1NSIvPgogICAgPC9nPgogICAgPGNpcmNsZSBjeD0iMTc1IiBjeT0iMTU1IiByPSI4IiBmaWxsPSIjRUVFREZFIi8+CiAgICA8Y2lyY2xlIGN4PSIyMjUiIGN5PSIxNTUiIHI9IjgiIGZpbGw9IiNFRUVERkUiLz4KICAgIDxjaXJjbGUgY3g9IjIwMCIgY3k9IjE5NSIgcj0iOCIgZmlsbD0iI0VFRURGRSIvPgogIDwvZz4KICA8dGV4dCB4PSIyMDAiIHk9IjM0NSIgZm9udC1mYW1pbHk9IkFyaWFsLCBIZWx2ZXRpY2EsIHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iNDgiIGZvbnQtd2VpZ2h0PSI2MDAiCiAgICAgICAgZmlsbD0iI0ZGRkZGRiIgdGV4dC1hbmNob3I9Im1pZGRsZSI+U2VjdXJlQUk8L3RleHQ+CiAgPHRleHQgeD0iMjAwIiB5PSIzODUiIGZvbnQtZmFtaWx5PSJBcmlhbCwgSGVsdmV0aWNhLCBzYW5zLXNlcmlmIiBmb250LXNpemU9IjIwIiBmb250LXdlaWdodD0iNDAwIgogICAgICAgIGZpbGw9IiNBRkE5RUMiIHRleHQtYW5jaG9yPSJtaWRkbGUiPmJ5IEF2ZW50cml4IFRlY2hub2xvZ2llczwvdGV4dD4KPC9zdmc+Cg==" width="90" height="108" alt="SecureAI by Aventrix Technologies" style="display:block;margin-bottom:22px;border-radius:14px;">
    <p style="margin:0 0 10px;font-size:11.5px;font-weight:700;letter-spacing:1.8px;color:#C4B5FD;text-transform:uppercase;">For {industry_label} Leaders</p>
    <h1 style="margin:0;font-size:24px;line-height:1.4;color:#ffffff;font-weight:700;">
      {subject_line}
    </h1>
  </td></tr>

  <!-- Body copy, AI generated per lead -->
  <tr><td style="padding:36px 44px 8px;">
    {paragraphs}
  </td></tr>

  <!-- CTA block -->
  <tr><td style="padding:8px 44px 8px;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background:#16121F;border-radius:12px;">
      <tr><td style="padding:24px 28px;text-align:center;">
        <p style="margin:0 0 16px;font-size:15.5px;line-height:1.7;color:#ffffff;font-weight:600;">Book a 15-minute demo directly</p>
        <a href="https://calendly.com/aventrixtechnologies-info" style="display:inline-block;background:#7C3AED;color:#ffffff;text-decoration:none;font-size:14px;font-weight:600;padding:13px 32px;border-radius:8px;">Schedule My Demo &rarr;</a>
      </td></tr>
    </table>
  </td></tr>

  <!-- Signature / link block -->
  <tr><td style="padding:28px 44px 32px">
    <table width="100%" cellpadding="0" cellspacing="0" style="border-top:1px solid #F0EEF5;padding-top:26px">
      <tr>
        <td style="vertical-align:top">
          <p style="margin:0;font-size:14px;font-weight:700;color:#16121F">Alex</p>
          <p style="margin:5px 0 4px;font-size:13px;color:#6B6680">SecureAI Gateway | Aventrix Technologies</p>
          <a href="https://aventrixtechnologies.com" style="font-size:13px;color:#7C3AED;text-decoration:none;font-weight:600;">aventrixtechnologies.com</a>
        </td>
        <td style="vertical-align:top;text-align:right">
          <a href="https://aventrixtechnologies.com/blog.html" style="display:block;font-size:12px;color:#6B6680;text-decoration:none;margin-bottom:8px">Read our Blog</a>
          <a href="https://aventrixtechnologies.com/features.html" style="display:block;font-size:12px;color:#6B6680;text-decoration:none;margin-bottom:8px">Product Features</a>
          <a href="https://calendly.com/aventrixtechnologies-info" style="display:inline-block;font-size:12px;color:#ffffff;background:#7C3AED;text-decoration:none;margin-bottom:8px;font-weight:600;padding:7px 14px;border-radius:6px;">Book a 15-Min Demo</a><br>
          <a href="https://aventrixtechnologies.com/contact.html" style="display:block;font-size:12px;color:#6B6680;text-decoration:none;margin-bottom:8px">Contact Us</a>
          <a href="https://wa.me/919104277272" style="display:block;font-size:12px;color:#25D366;text-decoration:none;font-weight:600;">WhatsApp</a>
        </td>
      </tr>
    </table>
  </td></tr>

  <!-- Footer -->
  <tr><td style="background:#FAFAFC;padding:18px 44px;border-top:1px solid #F0EEF5">
    <p style="margin:0;font-size:11px;color:#A7A2B8;line-height:1.6;">To unsubscribe reply with unsubscribe and we will remove you immediately.</p>
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

            def sanitize_tag(value: str) -> str:
                import re
                value = re.sub(r"[^A-Za-z0-9_-]", "_", value or "")
                return value[:50] or "unknown"

            response = resend.Emails.send({
                "from": f"Alex - SecureAI Gateway <{self.email}>",
                "to": [lead.email],
                "subject": email_content["subject"],
                "text": plain_body,
                "html": html_body,
                "reply_to": self.email,
                "tags": [
                    {"name": "lead_id", "value": str(lead_id)},
                    {"name": "industry", "value": sanitize_tag(lead.industry)},
                    {"name": "company", "value": sanitize_tag(lead.company)}
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

            # Auto-schedule follow-up sequence now that initial outreach succeeded
            try:
                from agents.new_agents import FollowUpAgent
                fu_agent = FollowUpAgent()
                fu_agent.schedule_followups(lead_id)
                fu_agent.close()
            except Exception as fu_err:
                self.log("send_email", f"Could not schedule follow-ups: {fu_err}", "error")

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
