import json
import os
from agents.base_agent import BaseAgent
from database import Lead, Email, FollowUp, LeadActivity, LeadNote, Invoice, Expense, SocialPost, SessionLocal
from datetime import datetime, timedelta

# ── Reply Monitor Agent ───────────────────────────────────
class ReplyMonitorAgent(BaseAgent):
    def __init__(self):
        super().__init__("Reply Monitor", "Inbox Manager")

    def categorize_reply(self, reply_text: str, lead_id: int) -> dict:
        prompt = f"""
Analyze this email reply from a lead and categorize it:
Reply: "{reply_text}"

Categories:
- interested: They want to know more or book a demo
- not_interested: They declined or unsubscribed
- out_of_office: Auto-reply or OOO message
- question: They have a specific question
- later: They want to revisit later

Return JSON: {{"category":"interested","sentiment":"positive","suggested_response":"...","next_action":"book_demo/follow_up/close/wait"}}
Return only JSON.
"""
        result = self.think(prompt)
        try:
            clean = result.replace("```json","").replace("```","").strip()
            data = json.loads(clean)
            # Update lead status
            db = self.db
            lead = db.query(Lead).filter(Lead.id == lead_id).first()
            if lead:
                if data.get("category") == "interested":
                    lead.status = "qualified"
                elif data.get("category") == "not_interested":
                    lead.status = "lost"
                db.commit()
                # Log activity
                activity = LeadActivity(
                    lead_id=lead_id,
                    activity="Reply received",
                    description=f"Category: {data.get('category')} | {reply_text[:100]}"
                )
                db.add(activity)
                db.commit()
            self.log("categorize_reply", f"Lead {lead_id}: {data.get('category')}")
            return data
        except Exception as e:
            self.log("categorize_reply", str(e), "error")
            return {}

    def generate_reply(self, reply_text: str, category: str, lead_id: int) -> str:
        db = self.db
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        company = lead.company if lead else "your company"
        prompt = f"""
Write a professional response to this {category} reply from {company}:
Their reply: "{reply_text}"

Context: We sell SecureAI Gateway — enterprise AI access control product.
Keep response under 80 words. Professional but friendly.
If interested: propose a specific demo time.
If question: answer clearly and propose next step.
Return only the email body text, no subject line.
"""
        return self.think(prompt)


# ── Follow-up Agent ───────────────────────────────────────
class FollowUpAgent(BaseAgent):
    def __init__(self):
        super().__init__("Follow-up Agent", "Sequence Manager")

    def schedule_followups(self, lead_id: int):
        db = self.db
        existing = db.query(FollowUp).filter(FollowUp.lead_id == lead_id).first()
        if existing:
            return
        for day in [3, 7, 14]:
            fu = FollowUp(
                lead_id=lead_id,
                scheduled_at=datetime.utcnow() + timedelta(days=day),
                day_number=day,
                status="pending"
            )
            db.add(fu)
        db.commit()
        self.log("schedule_followups", f"Scheduled 3 follow-ups for lead {lead_id}")

    def generate_followup_email(self, lead_id: int, day: int) -> dict:
        db = self.db
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            return {}
        templates = {
            3: "gentle check-in, reference previous email, add new value point about AI data leaks",
            7: "share a relevant case study or stat about AI security incidents, soft CTA",
            14: "final follow-up, mention limited availability, breakup email style"
        }
        prompt = f"""
Write follow-up #{day} day email for:
Company: {lead.company}, Contact: {lead.contact_name}, Industry: {lead.industry}
Template: {templates.get(day, "generic follow-up")}
Product: SecureAI Gateway — enterprise AI access control
Keep under 60 words. No pressure.
Return JSON: {{"subject":"...","body":"..."}}
Return only JSON.
"""
        result = self.think(prompt)
        try:
            clean = result.replace("```json","").replace("```","").strip()
            return json.loads(clean)
        except:
            return {"subject": f"Following up — {lead.company}", "body": result}

    def send_followup_email(self, lead_id: int, email_content: dict) -> bool:
        """Actually sends the follow-up via Resend, mirroring OutreachAgent.send_email"""
        db = self.db
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead or not lead.email:
            return False
        try:
            resend_key = os.getenv("RESEND_API_KEY", "")
            sender_email = os.getenv("ZOHO_EMAIL", "sales@aventrixtechnologies.com")
            if not resend_key:
                self.log("send_followup_email", "Missing RESEND_API_KEY", "error")
                return False

            import resend, re
            resend.api_key = resend_key

            def sanitize_tag(value: str) -> str:
                value = re.sub(r"[^A-Za-z0-9_-]", "_", value or "")
                return value[:50] or "unknown"

            plain_body = email_content.get("body", "")
            subject_line = email_content.get("subject", "Following up")
            industry_label = (lead.industry or "Operations").strip()

            body_for_html = plain_body
            for marker in ("\nAlex\nSecureAI Gateway", "\nAlex,\nSecureAI Gateway", "\n\nAlex"):
                if marker in body_for_html:
                    body_for_html = body_for_html.split(marker)[0]
                    break

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
    <img src="https://aventrixtechnologies.com/images/secureai-logo-email.png" width="90" height="108" alt="SecureAI by Aventrix Technologies" style="display:block;margin-bottom:22px;border-radius:14px;">
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

            response = resend.Emails.send({
                "from": f"Alex - SecureAI Gateway <{sender_email}>",
                "to": [lead.email],
                "subject": email_content.get("subject", "Following up"),
                "text": plain_body,
                "html": html_body,
                "reply_to": sender_email,
                "tags": [
                    {"name": "lead_id", "value": str(lead_id)},
                    {"name": "industry", "value": sanitize_tag(lead.industry)},
                    {"name": "company", "value": sanitize_tag(lead.company)},
                    {"name": "type", "value": "followup"}
                ]
            })
            if not response.get("id"):
                raise Exception(f"Resend failed: {response}")

            db.add(Email(
                lead_id=lead_id,
                subject=email_content.get("subject", ""),
                body=plain_body,
                status="sent",
                sent_at=datetime.utcnow()
            ))
            self.log("send_followup_email", f"Sent via Resend to {lead.email} id={response['id']}")
            return True
        except Exception as e:
            self.log("send_followup_email", str(e), "error")
            return False

    def run_pending_followups(self) -> dict:
        db = self.db
        pending = db.query(FollowUp).filter(
            FollowUp.status == "pending",
            FollowUp.scheduled_at <= datetime.utcnow()
        ).limit(20).all()
        sent = 0
        failed = 0
        for fu in pending:
            # Skip if the lead already moved past "contacted" (e.g. replied, qualified, demo booked)
            lead = db.query(Lead).filter(Lead.id == fu.lead_id).first()
            if not lead or lead.status not in ("contacted", "opened"):
                fu.status = "skipped"
                continue
            email_content = self.generate_followup_email(fu.lead_id, fu.day_number)
            if email_content and self.send_followup_email(fu.lead_id, email_content):
                fu.status = "sent"
                activity = LeadActivity(
                    lead_id=fu.lead_id,
                    activity=f"Follow-up Day {fu.day_number} sent",
                    description=email_content.get("subject", "")
                )
                db.add(activity)
                sent += 1
            else:
                fu.status = "failed"
                failed += 1
        db.commit()
        self.log("run_pending_followups", f"Sent {sent} follow-ups, {failed} failed")
        return {"sent": sent, "failed": failed}


# ── Proposal Generator ────────────────────────────────────
class ProposalAgent(BaseAgent):
    def __init__(self):
        super().__init__("Proposal Agent", "Proposal Writer")

    def generate_proposal(self, lead_id: int) -> dict:
        db = self.db
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            return {}
        prompt = f"""
Generate a professional sales proposal for:
Company: {lead.company}
Industry: {lead.industry}
Contact: {lead.contact_name}
Company Size: {lead.company_size}
Pain Points: {lead.notes}

Product: SecureAI Gateway
Features: AI access governance, DLP protection, usage tracking, multi-model support, audit logging
Pricing options: Starter $49/mo (25 users), Business $149/mo (100 users), Enterprise $399/mo (500 users)

Create a structured proposal with:
1. Executive Summary (personalized)
2. Problem Statement (their specific pain)
3. Our Solution (how SecureAI Gateway solves it)
4. Pricing Recommendation (suggest best tier)
5. ROI Estimate
6. Next Steps

Return JSON: {{"title":"...","executive_summary":"...","problem":"...","solution":"...","pricing_tier":"Business","pricing_amount":149,"roi_estimate":"...","next_steps":"..."}}
Return only JSON.
"""
        result = self.think(prompt)
        try:
            clean = result.replace("```json","").replace("```","").strip()
            data = json.loads(clean)
            activity = LeadActivity(
                lead_id=lead_id,
                activity="Proposal generated",
                description=f"Tier: {data.get('pricing_tier')} ${data.get('pricing_amount')}/mo"
            )
            db.add(activity)
            db.commit()
            self.log("generate_proposal", f"Proposal for {lead.company}")
            return data
        except Exception as e:
            self.log("generate_proposal", str(e), "error")
            return {}


# ── Contract Generator ────────────────────────────────────
class ContractAgent(BaseAgent):
    def __init__(self):
        super().__init__("Contract Agent", "Contract Writer")

    def generate_contract(self, lead_id: int, plan: str, amount: float) -> str:
        db = self.db
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            return ""
        today = datetime.utcnow().strftime("%B %d, %Y")
        prompt = f"""
Generate a basic SaaS service agreement for:
Client: {lead.company}
Contact: {lead.contact_name}
Plan: {plan} — ${amount}/month
Date: {today}
Provider: Aventrix Technologies, Ahmedabad, India
Product: SecureAI Gateway

Include sections:
1. Service Description
2. Payment Terms
3. Data Privacy & Security
4. Acceptable Use Policy
5. Termination (30 day notice)
6. Limitation of Liability
7. Governing Law (India)
8. Signature Block

Keep professional, concise. Under 500 words.
Return plain text, no JSON.
"""
        return self.think(prompt)


# ── Invoice Generator ─────────────────────────────────────
class InvoiceAgent(BaseAgent):
    def __init__(self):
        super().__init__("Invoice Agent", "Finance")

    def create_invoice(self, client_name: str, client_email: str, items: list, currency: str = "USD") -> dict:
        db = self.db
        count = db.query(Invoice).count() + 1
        invoice_no = f"INV-{datetime.utcnow().strftime('%Y%m')}-{count:03d}"
        total = sum(item.get("amount", 0) for item in items)
        due_date = (datetime.utcnow() + timedelta(days=15)).strftime("%Y-%m-%d")
        invoice = Invoice(
            invoice_no=invoice_no,
            client_name=client_name,
            client_email=client_email,
            amount=total,
            currency=currency,
            status="draft",
            due_date=due_date,
            items=json.dumps(items)
        )
        db.add(invoice)
        db.commit()
        self.log("create_invoice", f"{invoice_no} for {client_name} — {currency}{total}")
        return {"invoice_no": invoice_no, "total": total, "due_date": due_date, "id": invoice.id}


# ── Landing Page Generator ────────────────────────────────
class LandingPageAgent(BaseAgent):
    def __init__(self):
        super().__init__("Landing Page Agent", "Marketing")

    def generate_landing_page(self, target_industry: str = "enterprise") -> str:
        prompt = f"""
Generate a complete, professional HTML landing page for SecureAI Gateway targeting {target_industry} companies.

Requirements:
- Modern, clean design with CSS included in <style> tags
- Dark navy (#0A1628) and blue (#378ADD) color scheme
- Sections: Hero, Pain Points, Features, How It Works, Pricing, CTA, Footer
- Hero: Bold headline about AI security risk + CTA button "Book a Free Demo"
- Pain Points: 3 specific problems (data leaks via ChatGPT, uncontrolled AI usage, compliance risk)
- Features: 6 key features with icons (use emoji)
- Pricing: 3 tiers (Starter $49, Business $149, Enterprise $399)
- CTA: "Start Free Trial" form with name + email
- Mobile responsive
- Professional fonts (use Google Fonts - Inter)
- Include JavaScript for smooth scroll

Return complete HTML file only, starting with <!DOCTYPE html>
"""
        result = self.think(prompt)
        # Strip markdown code fences if present
        result = result.strip()
        if result.startswith("```html"):
            result = result[7:]
        if result.startswith("```"):
            result = result[3:]
        if result.endswith("```"):
            result = result[:-3]
        return result.strip()


# ── Newsletter Agent ──────────────────────────────────────
class NewsletterAgent(BaseAgent):
    def __init__(self):
        super().__init__("Newsletter Agent", "Marketing")

    def generate_newsletter(self) -> dict:
        prompt = f"""
Generate a weekly email newsletter for SecureAI Gateway subscribers.
Date: {datetime.utcnow().strftime('%B %d, %Y')}

Sections:
1. Subject line (compelling)
2. Header: "AI Security Weekly by Aventrix Technologies"
3. Top AI security news/incident this week (realistic)
4. Feature spotlight (one SecureAI Gateway feature)
5. Tip of the week (AI governance tip)
6. CTA: Book a demo

Keep professional, under 300 words total.
Return JSON: {{"subject":"...","body":"..."}}
Return only JSON.
"""
        result = self.think(prompt)
        try:
            clean = result.replace("```json","").replace("```","").strip()
            return json.loads(clean)
        except:
            return {"subject": "AI Security Weekly", "body": result}


# ── Social Calendar Agent ─────────────────────────────────
class SocialCalendarAgent(BaseAgent):
    def __init__(self):
        super().__init__("Social Calendar Agent", "Marketing")

    def generate_30_day_calendar(self) -> list:
        prompt = f"""
Generate a 30-day LinkedIn content calendar for SecureAI Gateway.
Start date: {datetime.utcnow().strftime('%Y-%m-%d')}

Mix of content types:
- Educational (AI security tips) — 40%
- Product features — 20%
- Thought leadership — 20%
- Case studies/stats — 20%

Return JSON array of 30 posts:
[{{"day":1,"date":"2026-06-05","type":"educational","hook":"...","content":"...","hashtags":["AIGov","CyberSecurity"],"cta":"..."}}]
Keep each post under 150 words. Return only JSON array.
"""
        result = self.think(prompt)
        try:
            clean = result.replace("```json","").replace("```","").strip()
            posts = json.loads(clean)
            db = self.db
            for post in posts:
                sp = SocialPost(
                    platform="linkedin",
                    content=post.get("content",""),
                    hashtags=",".join(post.get("hashtags",[])),
                    scheduled_at=post.get("date",""),
                    status="scheduled"
                )
                db.add(sp)
            db.commit()
            self.log("generate_calendar", f"Created {len(posts)} posts")
            return posts
        except Exception as e:
            self.log("generate_calendar", str(e), "error")
            return []


# ── Market Trend Agent ────────────────────────────────────
class MarketTrendAgent(BaseAgent):
    def __init__(self):
        super().__init__("Market Trend Agent", "R&D")

    def generate_trend_report(self) -> dict:
        prompt = f"""
Generate a weekly AI security market intelligence report for {datetime.utcnow().strftime('%B %Y')}.

Include:
1. Top 3 AI security incidents/news this week (realistic, plausible)
2. Market size update (enterprise AI security market)
3. Regulatory update (EU AI Act, GDPR, India DPDP)
4. Opportunity for SecureAI Gateway this week
5. Recommended action for Aventrix Technologies

Return JSON: {{"title":"...","date":"...","incidents":[{{"title":"...","summary":"...","impact":"..."}}],"market_update":"...","regulatory_update":"...","opportunity":"...","recommended_action":"..."}}
Return only JSON.
"""
        result = self.think(prompt)
        try:
            clean = result.replace("```json","").replace("```","").strip()
            return json.loads(clean)
        except:
            return {}


# ── Feedback Analyzer ─────────────────────────────────────
class FeedbackAnalyzerAgent(BaseAgent):
    def __init__(self):
        super().__init__("Feedback Analyzer", "R&D")

    def analyze_all_replies(self) -> dict:
        db = self.db
        emails = db.query(Email).filter(Email.direction == "inbound").limit(50).all()
        if not emails:
            return {"insights": [], "top_objections": [], "feature_requests": [], "sentiment": "neutral"}
        replies = [e.body for e in emails if e.body]
        if not replies:
            return {"insights": [], "top_objections": [], "feature_requests": [], "sentiment": "neutral"}
        replies_text = "\n---\n".join(replies[:20])
        prompt = f"""
Analyze these email replies from prospects about SecureAI Gateway:
{replies_text[:2000]}

Extract:
1. Top objections (price, features, timing)
2. Feature requests mentioned
3. Overall sentiment
4. Key insights for product improvement

Return JSON: {{"insights":["..."],"top_objections":["..."],"feature_requests":["..."],"sentiment":"positive/neutral/negative","recommendation":"..."}}
Return only JSON.
"""
        result = self.think(prompt)
        try:
            clean = result.replace("```json","").replace("```","").strip()
            return json.loads(clean)
        except:
            return {}
