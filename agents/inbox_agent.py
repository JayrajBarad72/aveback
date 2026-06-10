"""
Inbox Agent — Reads sales@ inbox automatically every 30 minutes
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
from whatsapp import notify_important_update
from dotenv import load_dotenv

load_dotenv()

IMAP_HOST = "imappro.zoho.in"
IMAP_PORT = 993
SMTP_HOST = os.getenv("ZOHO_SMTP_HOST", "smtp.zeptomail.in")
SMTP_PORT = int(os.getenv("ZOHO_SMTP_PORT", 465))
EMAIL_ADDRESS = os.getenv("ZOHO_EMAIL", "sales@aventrixtechnologies.com")
EMAIL_PASSWORD = os.getenv("ZOHO_EMAIL_PASSWORD", "Jasy@7272")
SMTP_PASSWORD = os.getenv("ZOHO_APP_PASSWORD")

class InboxAgent(BaseAgent):
    def __init__(self):
        super().__init__("Inbox Agent", "Reply Monitor")

    def connect_imap(self):
        """Connect to Zoho IMAP — try multiple hosts"""
        hosts = ["imappro.zoho.in", "imap.zoho.in", "imap.zoho.com"]
        for host in hosts:
            try:
                mail = imaplib.IMAP4_SSL(host, IMAP_PORT)
                mail.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
                print(f"✅ Connected to {host}")
                return mail
            except Exception as e:
                print(f"❌ Failed {host}: {e}")
                continue
        self.log("connect_imap", f"All IMAP hosts failed", "error")
        return None

    def read_new_emails(self) -> list:
        mail = self.connect_imap()
        if not mail:
            return []
        try:
            mail.select("INBOX")
            since_date = (datetime.utcnow() - timedelta(hours=24)).strftime("%d-%b-%Y")
            status, messages = mail.search(None, f'(UNSEEN SINCE {since_date})')
            if status != "OK" or not messages[0]:
                mail.logout()
                return []
            email_ids = messages[0].split()
            emails = []
            for eid in email_ids[-20:]:
                try:
                    status, msg_data = mail.fetch(eid, "(RFC822)")
                    if status != "OK":
                        continue
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    subject = ""
                    subject_raw = msg.get("Subject", "")
                    if subject_raw:
                        decoded = decode_header(subject_raw)
                        for part, enc in decoded:
                            if isinstance(part, bytes):
                                subject += part.decode(enc or "utf-8", errors="replace")
                            else:
                                subject += str(part)
                    from_raw = msg.get("From", "")
                    sender_email = ""
                    sender_name = ""
                    if "<" in from_raw:
                        sender_name = from_raw.split("<")[0].strip().strip('"')
                        sender_email = from_raw.split("<")[1].replace(">","").strip()
                    else:
                        sender_email = from_raw.strip()
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
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
                    body_lines = body.split("\n")
                    clean_lines = []
                    for line in body_lines:
                        if line.startswith(">") or (line.startswith("On ") and "wrote:" in line):
                            break
                        clean_lines.append(line)
                    clean_body = "\n".join(clean_lines).strip()[:1000]
                    if sender_email and sender_email != EMAIL_ADDRESS:
                        emails.append({
                            "id": eid.decode(),
                            "from_email": sender_email,
                            "from_name": sender_name,
                            "subject": subject,
                            "body": clean_body,
                            "date": msg.get("Date", "")
                        })
                except Exception as e:
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
        prompt = f"""
Categorize this email reply to SecureAI Gateway outreach:
From: {email_data.get('from_name','')} <{email_data.get('from_email','')}>
Subject: {email_data.get('subject','')}
Body: {email_data.get('body','')}

Categories: HOT (wants demo/pricing), WARM (interested, has questions), COLD (not interested), UNSUBSCRIBE, OOO, BOUNCE, SPAM

Return JSON: {{"category":"HOT/WARM/COLD/UNSUBSCRIBE/OOO/BOUNCE/SPAM","has_question":true/false,"question":"","urgency":"high/medium/low","suggested_action":""}}
Return only JSON.
"""
        result = self.think(prompt)
        try:
            return json.loads(result.replace("```json","").replace("```","").strip())
        except:
            return {"category": "WARM", "has_question": False, "urgency": "low"}

    def generate_response(self, email_data: dict, category: dict) -> dict:
        cat = category.get("category","WARM")
        if cat in ["OOO","BOUNCE","SPAM","UNSUBSCRIBE"]:
            return None
        prompt = f"""
Write professional email response to this {cat} lead about SecureAI Gateway.
From: {email_data.get('from_name','there')}
Their message: {email_data.get('body','')}
Their question: {category.get('question','')}

Rules:
- HOT: Enthusiasm + propose demo time (Tuesday 3PM or Wednesday 11AM)
- WARM: Answer question + soft demo CTA
- COLD: Acknowledge, leave door open
- Under 100 words
- Signature: "SecureAI Gateway Team | Aventrix Technologies | aventrixtechnologies.com"
- NO personal names, NO pricing

Return JSON: {{"subject":"Re: ...","body":"..."}}
Return only JSON.
"""
        result = self.think(prompt)
        try:
            return json.loads(result.replace("```json","").replace("```","").strip())
        except:
            return None

    def send_reply(self, to_email: str, subject: str, body: str) -> bool:
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
        db = self.db
        lead = db.query(Lead).filter(Lead.email == sender_email).first()
        if not lead:
            return
        cat = category.get("category","WARM")
        if cat == "HOT":
            lead.status = "qualified"
        elif cat == "WARM":
            lead.status = "replied"
        elif cat in ["COLD","UNSUBSCRIBE"]:
            lead.status = "lost"
        activity = LeadActivity(
            lead_id=lead.id,
            activity=f"Reply received — {cat}",
            description=body[:100]
        )
        db.add(activity)
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

    def run_inbox_cycle(self) -> dict:
        new_emails = self.read_new_emails()
        if not new_emails:
            return {"processed": 0, "hot": 0, "replied": 0}
        processed = 0
        hot_count = 0
        replied = 0
        for email_data in new_emails:
            try:
                category = self.categorize_reply(email_data)
                cat = category.get("category","WARM")
                if cat in ["BOUNCE","SPAM","OOO"]:
                    continue
                self.update_lead_from_reply(email_data["from_email"], category, email_data["body"])
                if cat in ["HOT","WARM"]:
                    response = self.generate_response(email_data, category)
                    if response:
                        success = self.send_reply(email_data["from_email"], response.get("subject",""), response.get("body",""))
                        if success:
                            replied += 1
                if cat == "HOT":
                    hot_count += 1
                    notify_important_update(
                        "🔥 HOT LEAD REPLIED",
                        f"Company: {email_data.get('from_name','Unknown')}\n"
                        f"Email: {email_data['from_email']}\n"
                        f"Message: {email_data['body'][:150]}\n\n"
                        f"Alex auto-responded. Recommend: Schedule demo ASAP!"
                    )
                processed += 1
            except Exception as e:
                continue
        return {"processed": processed, "hot": hot_count, "replied": replied}
