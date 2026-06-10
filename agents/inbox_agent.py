"""
Inbox Agent — Reads sales@ inbox automatically every 30 minutes
- Reads all new emails
- Categorizes replies using AI
- Auto-responds to interested leads
- Auto-answers questions
- Updates lead status
- WhatsApps Jayraj for hot leads
"""
import imaplib
import email
import json
import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from datetime import datetime, timedelta
from agents.base_agent import BaseAgent, client
from database import Lead, Email as EmailModel, LeadActivity, Metric, SessionLocal
from whatsapp import notify_important_update, send_whatsapp
from dotenv import load_dotenv

load_dotenv()

IMAP_HOST = "imap.zoho.in"
IMAP_PORT = 993
SMTP_HOST = os.getenv("ZOHO_SMTP_HOST", "smtp.zeptomail.in")
SMTP_PORT = int(os.getenv("ZOHO_SMTP_PORT", 465))
EMAIL_ADDRESS = os.getenv("ZOHO_EMAIL", "sales@aventrixtechnologies.com")
EMAIL_PASSWORD = os.getenv("ZOHO_EMAIL_PASSWORD", "Jasy@7272")
SMTP_PASSWORD = os.getenv("ZOHO_APP_PASSWORD")

PRODUCT_KNOWLEDGE = """
SecureAI Gateway = On-premise AI access control platform.
Solves Shadow AI — employees leaking data into ChatGPT/Claude.
Key features: DLP, multi-model AI, audit logs, 20-min deployment.
Pricing: Contact us for current pricing (do not quote specific numbers).
Free trial: 7 days, no credit card.
Contact: sales@aventrixtechnologies.com | aventrixtechnologies.com
Signature: SecureAI Gateway Team | Aventrix Technologies | aventrixtechnologies.com
"""

class InboxAgent(BaseAgent):
    def __init__(self):
        super().__init__("Inbox Agent", "Reply Monitor")

    def connect_imap(self):
        """Connect to Zoho IMAP"""
        try:
            mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
            mail.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            return mail
        except Exception as e:
            self.log("connect_imap", str(e), "error")
            return None

    def read_new_emails(self) -> list:
        """Read unread emails from inbox"""
        mail = self.connect_imap()
        if not mail:
            return []

        try:
            mail.select("INBOX")
            # Search for unread emails from last 24 hours
            since_date = (datetime.utcnow() - timedelta(hours=24)).strftime("%d-%b-%Y")
            status, messages = mail.search(None, f'(UNSEEN SINCE {since_date})')

            if status != "OK" or not messages[0]:
                mail.logout()
                return []

            email_ids = messages[0].split()
            emails = []

            for eid in email_ids[-20:]:  # Max 20 emails
                try:
                    status, msg_data = mail.fetch(eid, "(RFC822)")
                    if status != "OK":
                        continue

                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)

                    # Decode subject
                    subject = ""
                    subject_raw = msg.get("Subject", "")
                    if subject_raw:
                        decoded = decode_header(subject_raw)
                        for part, enc in decoded:
                            if isinstance(part, bytes):
                                subject += part.decode(enc or "utf-8", errors="replace")
                            else:
                                subject += str(part)

                    # Get sender
                    from_raw = msg.get("From", "")
                    sender_email = ""
                    sender_name = ""
                    if "<" in from_raw:
                        sender_name = from_raw.split("<")[0].strip().strip('"')
                        sender_email = from_raw.split("<")[1].replace(">","").strip()
                    else:
                        sender_email = from_raw.strip()

                    # Get body
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            ctype = part.get_content_type()
                            if ctype == "text/plain":
                                try:
                                    body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                                    break
                                except:
                                    pass
                    else:
                        try:
                            body = msg.get_payload(decode=True).decode("utf-8", errors="replace")
                        except:
                            pass

                    # Clean body — remove quoted text
                    body_lines = body.split("\n")
                    clean_lines = []
                    for line in body_lines:
                        if line.startswith(">") or line.startswith("On ") and "wrote:" in line:
                            break
                        clean_lines.append(line)
                    clean_body = "\n".join(clean_lines).strip()[:1000]

                    if sender_email and not sender_email == EMAIL_ADDRESS:
                        emails.append({
                            "id": eid.decode(),
                            "from_email": sender_email,
                            "from_name": sender_name,
                            "subject": subject,
                            "body": clean_body,
                            "date": msg.get("Date", "")
                        })

                except Exception as e:
                    self.log("parse_email", str(e), "error")
                    continue

            mail.logout()
            self.log("read_new_emails", f"Found {len(emails)} new emails")
            return emails

        except Exception as e:
            self.log("read_new_emails", str(e), "error")
            try:
                mail.logout()
            except:
                pass
            return []

    def categorize_reply(self, email_data: dict) -> dict:
        """AI categorizes the email reply"""
        prompt = f"""
Categorize this email reply to SecureAI Gateway outreach:

From: {email_data.get('from_name','')} <{email_data.get('from_email','')}>
Subject: {email_data.get('subject','')}
Body: {email_data.get('body','')}

Categories:
- HOT: Very interested, wants demo, wants pricing, wants to proceed
- WARM: Interested but has questions or wants more info
- COLD: Not interested right now but not hostile
- UNSUBSCRIBE: Wants to be removed from list
- OOO: Out of office auto-reply
- BOUNCE: Email delivery failure
- SPAM: Spam or irrelevant

Return JSON:
{{
  "category": "HOT/WARM/COLD/UNSUBSCRIBE/OOO/BOUNCE/SPAM",
  "sentiment": "positive/neutral/negative",
  "key_points": ["what they said in brief"],
  "has_question": true/false,
  "question": "their specific question if any",
  "urgency": "high/medium/low",
  "suggested_action": "what to do next"
}}
Return only JSON.
"""
        result = self.think(prompt)
        try:
            clean = result.replace("```json","").replace("```","").strip()
            return json.loads(clean)
        except:
            return {"category": "WARM", "sentiment": "neutral",
                    "has_question": False, "urgency": "low",
                    "suggested_action": "Manual review needed"}

    def generate_response(self, email_data: dict, category: dict) -> dict:
        """Generate appropriate response"""
        cat = category.get("category","WARM")

        if cat in ["OOO", "BOUNCE", "SPAM", "UNSUBSCRIBE"]:
            return None

        prompt = f"""
Write a professional email response to this {cat} lead.

Their email:
From: {email_data.get('from_name','there')}
Subject: {email_data.get('subject','')}
Message: {email_data.get('body','')}

Category: {cat}
Their question: {category.get('question','')}
Key points: {category.get('key_points',[])}

Product knowledge:
{PRODUCT_KNOWLEDGE}

Instructions:
- HOT leads: Express enthusiasm, propose specific demo time (e.g. "Would Tuesday 3PM or Wednesday 11AM work?")
- WARM leads: Answer their questions clearly, soft CTA for demo
- COLD leads: Acknowledge, leave door open, no pressure
- Keep under 100 words
- Professional but friendly tone
- NO personal names in signature
- Signature: "SecureAI Gateway Team | Aventrix Technologies | aventrixtechnologies.com"

Return JSON: {{"subject": "Re: ...", "body": "..."}}
Return only JSON.
"""
        result = self.think(prompt)
        try:
            clean = result.replace("```json","").replace("```","").strip()
            return json.loads(clean)
        except:
            return None

    def send_reply(self, to_email: str, subject: str, body: str) -> bool:
        """Send reply via ZeptoMail SMTP"""
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject if subject.startswith("Re:") else f"Re: {subject}"
            msg["From"] = f"SecureAI Gateway Team <{EMAIL_ADDRESS}>"
            msg["To"] = to_email
            msg.attach(MIMEText(body, "plain"))

            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as server:
                server.login("emailapikey", SMTP_PASSWORD)
                server.sendmail(EMAIL_ADDRESS, to_email, msg.as_string())

            self.log("send_reply", f"Reply sent to {to_email}")
            return True
        except Exception as e:
            self.log("send_reply", str(e), "error")
            return False

    def update_lead_from_reply(self, sender_email: str, category: dict, body: str):
        """Update lead record based on reply"""
        db = self.db
        lead = db.query(Lead).filter(Lead.email == sender_email).first()

        if not lead:
            return

        cat = category.get("category","WARM")
        old_status = lead.status

        # Update status based on category
        if cat == "HOT":
            lead.status = "qualified"
            m = db.query(Metric).first()
            if m:
                m.pipeline_value += 149.0
                db.commit()
        elif cat == "WARM":
            lead.status = "replied"
        elif cat in ["COLD","UNSUBSCRIBE"]:
            lead.status = "lost"

        # Log activity
        activity = LeadActivity(
            lead_id=lead.id,
            activity=f"Reply received — {cat}",
            description=f"Category: {cat} | {body[:100]}"
        )
        db.add(activity)

        # Save email record
        email_record = EmailModel(
            lead_id=lead.id,
            subject=f"Reply from {sender_email}",
            body=body,
            direction="inbound",
            status="received",
            sent_at=datetime.utcnow()
        )
        db.add(email_record)
        db.commit()

        self.log("update_lead", f"Lead {lead.company} updated: {old_status} → {lead.status}")

    def run_inbox_cycle(self) -> dict:
        """Main cycle — reads inbox and processes all emails"""
        self.log("run_inbox_cycle", "Starting inbox check...")

        new_emails = self.read_new_emails()
        if not new_emails:
            self.log("run_inbox_cycle", "No new emails")
            return {"processed": 0, "hot": 0, "replied": 0}

        processed = 0
        hot_count = 0
        replied = 0

        for email_data in new_emails:
            try:
                # Categorize
                category = self.categorize_reply(email_data)
                cat = category.get("category","WARM")

                # Skip non-actionable
                if cat in ["BOUNCE","SPAM","OOO"]:
                    continue

                # Update lead record
                self.update_lead_from_reply(
                    email_data["from_email"],
                    category,
                    email_data["body"]
                )

                # Handle unsubscribe
                if cat == "UNSUBSCRIBE":
                    db = self.db
                    lead = db.query(Lead).filter(Lead.email == email_data["from_email"]).first()
                    if lead:
                        lead.status = "lost"
                        db.commit()
                    processed += 1
                    continue

                # Generate and send response
                if cat in ["HOT","WARM"]:
                    response = self.generate_response(email_data, category)
                    if response:
                        success = self.send_reply(
                            email_data["from_email"],
                            response.get("subject",""),
                            response.get("body","")
                        )
                        if success:
                            replied += 1

                # WhatsApp Jayraj for HOT leads
                if cat == "HOT":
                    hot_count += 1
                    notify_important_update(
                        "🔥 HOT LEAD REPLIED",
                        f"Company: {email_data.get('from_name','Unknown')}\n"
                        f"Email: {email_data['from_email']}\n"
                        f"Message: {email_data['body'][:150]}\n\n"
                        f"Action: Alex has auto-responded and marked as QUALIFIED.\n"
                        f"Recommend: Schedule demo call ASAP!"
                    )

                processed += 1

            except Exception as e:
                self.log("process_email", str(e), "error")
                continue

        result = {"processed": processed, "hot": hot_count, "replied": replied}
        self.log("run_inbox_cycle",
                 f"Done: {processed} processed, {hot_count} hot, {replied} replied")
        return result
