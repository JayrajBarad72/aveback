import json
from agents.base_agent import BaseAgent
from database import Lead, Metric
from datetime import datetime

# ── Qualifier Agent ───────────────────────────────────────
class QualifierAgent(BaseAgent):
    def __init__(self):
        super().__init__("Qualifier Agent", "Lead Qualifier")

    def qualify_lead(self, lead_id: int) -> dict:
        db = self.db
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            return {}
        prompt = f"""
Score this lead for SecureAI Gateway (0-100):
Company: {lead.company}, Industry: {lead.industry}, Size: {lead.company_size}, Country: {lead.country}
Criteria: AI adoption likelihood, security compliance needs, budget capacity, decision maker access.
Return JSON: {{"score":85,"fit":"high","reason":"...","next_action":"..."}}
Return only JSON.
"""
        result = self.think(prompt)
        try:
            clean = result.replace("```json","").replace("```","").strip()
            data = json.loads(clean)
            lead.score = data.get("score", lead.score)
            if data.get("fit") == "high" and lead.status == "contacted":
                lead.status = "qualified"
            db.commit()
            self.log("qualify_lead", f"Lead {lead_id} scored {data.get('score')}")
            return data
        except:
            return {}

    def run_qualification(self) -> dict:
        db = self.db
        leads = db.query(Lead).filter(Lead.status == "contacted").limit(20).all()
        qualified = 0
        for lead in leads:
            result = self.qualify_lead(lead.id)
            if result.get("fit") == "high":
                qualified += 1
        self.log("run_qualification", f"Qualified {qualified} leads")
        return {"qualified": qualified}


# ── Booking Agent ─────────────────────────────────────────
class BookingAgent(BaseAgent):
    def __init__(self):
        super().__init__("Booking Agent", "Demo Scheduler")

    def generate_booking_email(self, lead_id: int) -> dict:
        db = self.db
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            return {}
        prompt = f"""
Write a short follow-up email to book a 15-minute demo call.
Lead: {lead.contact_name} at {lead.company} ({lead.industry})
They showed interest in SecureAI Gateway.
Keep it under 80 words. Friendly and direct.
Return JSON: {{"subject":"...","body":"..."}}
"""
        result = self.think(prompt)
        try:
            clean = result.replace("```json","").replace("```","").strip()
            return json.loads(clean)
        except:
            return {"subject": "Quick demo — 15 mins?", "body": result}

    def mark_demo_booked(self, lead_id: int) -> bool:
        db = self.db
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if lead:
            lead.status = "demo_booked"
            db.commit()
            metrics = db.query(Metric).first()
            if metrics:
                metrics.demos_booked += 1
                metrics.pipeline_value += 149.0
                metrics.updated_at = datetime.utcnow()
                db.commit()
            self.log("mark_demo_booked", f"Demo booked for {lead.company}")
            return True
        return False


# ── Blog Writer Agent ─────────────────────────────────────
class BlogWriterAgent(BaseAgent):
    def __init__(self):
        super().__init__("Blog Writer", "Content Writer")

    def write_blog_post(self, topic: str = None) -> dict:
        if not topic:
            topic = self._pick_topic()
        prompt = f"""
Write a professional SEO blog post about: {topic}
Context: For SecureAI Gateway — enterprise AI access control product.
Structure: Title, Meta Description, Introduction (100w), 3 sections with H2 headings (150w each), Conclusion (80w), CTA.
Target audience: IT managers, CISOs, CTOs of mid-size companies.
Return JSON: {{"title":"...","meta":"...","content":"...","keywords":["...","...","..."]}}
Return only JSON.
"""
        result = self.think(prompt)
        try:
            clean = result.replace("```json","").replace("```","").strip()
            # Extract the JSON object even if the model adds prose around it
            if not clean.startswith("{"):
                start = clean.find("{")
                end = clean.rfind("}")
                if start != -1 and end != -1:
                    clean = clean[start:end+1]
            data = json.loads(clean)
            from database import BlogPost, SessionLocal
            db = SessionLocal()
            post = BlogPost(title=data["title"], content=data["content"],
                           keywords=",".join(data.get("keywords",[])), status="published")
            db.add(post)
            db.commit()
            db.close()
            self.log("write_blog_post", f"Published: {data['title'][:50]}")
            data["status"] = "published"
            return data
        except Exception as e:
            self.log("write_blog_post", f"Parse/save failed: {str(e)[:200]}", "error")
            return {"error": str(e)[:200]}

    def _pick_topic(self) -> str:
        topics = [
            "Why enterprises need AI access control in 2025",
            "Top 5 AI security risks every CISO should know",
            "How to implement DLP for AI tools in your organization",
            "ChatGPT data leaks — how to prevent them",
            "AI governance best practices for healthcare companies",
        ]
        import random
        return random.choice(topics)


# ── Social Media Agent ────────────────────────────────────
class SocialMediaAgent(BaseAgent):
    def __init__(self):
        super().__init__("Social Media Agent", "Social Media Manager")

    def generate_posts(self, platform: str = "linkedin") -> list:
        prompt = f"""
Generate 3 {platform} posts for SecureAI Gateway.
Mix: 1 educational, 1 product feature highlight, 1 thought leadership.
Each post max 150 words. Include relevant hashtags.
Return JSON array: [{{"type":"educational","content":"...","hashtags":["..."]}}]
Return only JSON.
"""
        result = self.think(prompt)
        try:
            clean = result.replace("```json","").replace("```","").strip()
            posts = json.loads(clean)
            self.log("generate_posts", f"Generated {len(posts)} {platform} posts")
            return posts
        except:
            return []


# ── Finance Agent ─────────────────────────────────────────
class FinanceAgent(BaseAgent):
    def __init__(self):
        super().__init__("Finance Agent", "Financial Controller")

    def get_summary(self) -> dict:
        db = self.db
        metrics = db.query(Metric).first()
        prompt = f"""
Analyze this startup's financial position:
Pipeline value: ${metrics.pipeline_value if metrics else 0}
Demos booked: {metrics.demos_booked if metrics else 0}
Total leads: {metrics.total_leads if metrics else 0}
Emails sent: {metrics.emails_sent if metrics else 0}
Product: SaaS, pricing TBD (est $49-$399/month per company)

Give a 3-sentence financial summary and 2 revenue projections (conservative/optimistic).
Return JSON: {{"summary":"...","conservative_mrr":0,"optimistic_mrr":0,"advice":"..."}}
Return only JSON.
"""
        result = self.think(prompt)
        try:
            clean = result.replace("```json","").replace("```","").strip()
            return json.loads(clean)
        except:
            return {}


# ── R&D Agent ─────────────────────────────────────────────
class RnDAgent(BaseAgent):
    def __init__(self):
        super().__init__("R&D Agent", "Research & Development")

    def research_competitors(self) -> list:
        prompt = """
List top 5 competitors to SecureAI Gateway (AI access control / enterprise AI security).
For each: company name, key features, pricing, weakness vs SecureAI Gateway.
Return JSON array: [{"name":"...","features":"...","pricing":"...","weakness":"..."}]
Return only JSON.
"""
        result = self.think(prompt)
        try:
            clean = result.replace("```json","").replace("```","").strip()
            competitors = json.loads(clean)
            self.log("research_competitors", f"Found {len(competitors)} competitors")
            return competitors
        except:
            return []

    def generate_product_ideas(self) -> list:
        prompt = """
Generate 5 feature improvement ideas for SecureAI Gateway based on market trends in enterprise AI security.
Return JSON array: [{"idea":"...","priority":"high/medium/low","reason":"...","effort":"small/medium/large"}]
Return only JSON.
"""
        result = self.think(prompt)
        try:
            clean = result.replace("```json","").replace("```","").strip()
            ideas = json.loads(clean)
            self.log("generate_product_ideas", f"Generated {len(ideas)} ideas")
            return ideas
        except:
            return []
