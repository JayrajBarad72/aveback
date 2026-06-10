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

    def run_pending_followups(self) -> dict:
        db = self.db
        pending = db.query(FollowUp).filter(
            FollowUp.status == "pending",
            FollowUp.scheduled_at <= datetime.utcnow()
        ).limit(20).all()
        sent = 0
        for fu in pending:
            email_content = self.generate_followup_email(fu.lead_id, fu.day_number)
            if email_content:
                fu.status = "sent"
                activity = LeadActivity(
                    lead_id=fu.lead_id,
                    activity=f"Follow-up Day {fu.day_number} sent",
                    description=email_content.get("subject", "")
                )
                db.add(activity)
                sent += 1
        db.commit()
        self.log("run_pending_followups", f"Sent {sent} follow-ups")
        return {"sent": sent}


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
