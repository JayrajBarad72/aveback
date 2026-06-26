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
        prompt = f"""You are a senior content strategist writing an SEO blog post that should rank on Google's first page.

TOPIC: {topic}
PRODUCT CONTEXT: SecureAI Gateway by Aventrix Technologies — an on-premise enterprise AI security and DLP platform. It lets companies give employees Claude, GPT-4o and local AI (Llama, Mistral) with real-time data loss prevention, admin controls, and audit logs. Never claim it has an existing client base.
READER: An IT manager, CISO, or CTO at a 20-500 employee company in legal, healthcare, finance, IT/MSP, consulting, or manufacturing. They are searching Google for a real problem.

SEO REQUIREMENTS (follow precisely):
1. Identify the primary keyword phrase a person would Google for this topic. Put it in the title, in the first sentence, and naturally in 2-3 H2 headings.
2. Title: under 60 characters, compelling, includes the primary keyword. Not clickbait.
3. First paragraph: answer the core question directly in the first 2 sentences (Google rewards this and it can win a featured snippet).
4. Length: 900-1200 words. Use 4-5 H2 (##) sections.
5. Include one short bulleted or numbered list ONLY where it genuinely helps (e.g. a checklist or steps). Do not bullet everything.
6. Write a meta description: 150-160 characters, includes the keyword, reads like a human wrote it.

WRITING STYLE (critical — must not read like generic AI):
- Write like an experienced practitioner talking to a peer, not a marketing bot.
- Vary sentence length. Use specific, concrete examples (a real-sounding scenario, an actual number, a named regulation).
- Avoid these AI tells: do NOT start sections with "In today's fast-paced world" or "In the ever-evolving landscape." Do NOT overuse bold sub-labels like "**Key Point:**". Do NOT end with "In conclusion." Do NOT use the words "delve", "leverage", "robust", "seamless", "landscape", "realm", "tapestry".
- Have a point of view. It's fine to be a little opinionated.
- Mention SecureAI Gateway naturally only once or twice, where it genuinely fits — not as a hard sell in every section. The CTA goes at the very end only.

Return your answer in EXACTLY this format, using these literal markers on their own lines:

===TITLE===
(title here, one line, under 60 chars)
===META===
(meta description here, one line, 150-160 chars)
===KEYWORDS===
(6 comma-separated keywords, primary keyword first)
===CONTENT===
(the full markdown blog body — intro, 4-5 ## sections, natural CTA at the end)
===END==="""

        result = self.think_long(prompt, max_tokens=4000)
        try:
            def between(text, start, end):
                s = text.find(start)
                if s == -1: return ""
                s += len(start)
                e = text.find(end, s)
                return (text[s:e] if e != -1 else text[s:]).strip()

            title = between(result, "===TITLE===", "===META===")
            meta = between(result, "===META===", "===KEYWORDS===")
            keywords = between(result, "===KEYWORDS===", "===CONTENT===")
            content = between(result, "===CONTENT===", "===END===")

            if not title or not content:
                raise ValueError("Missing title or content in model output")

            from database import BlogPost, SessionLocal
            db = SessionLocal()
            # Store meta description at the top of keywords field if BlogPost has no meta column,
            # so the website can use it. Prefix with META: for easy parsing.
            kw_field = keywords
            try:
                post = BlogPost(title=title, content=content, keywords=keywords,
                                meta_description=meta, status="published")
            except TypeError:
                # BlogPost model has no meta_description column; fold it into content as HTML comment
                content_with_meta = f"<!--META:{meta}-->\n{content}"
                post = BlogPost(title=title, content=content_with_meta, keywords=keywords, status="published")
            db.add(post)
            db.commit()
            pid = post.id
            db.close()
            self.log("write_blog_post", f"Published: {title[:50]}")
            return {"id": pid, "title": title, "meta": meta, "keywords": keywords, "content": content, "status": "published"}
        except Exception as e:
            self.log("write_blog_post", f"Failed: {str(e)[:200]}", "error")
            return {"error": str(e)[:200]}

    def _pick_topic(self) -> str:
        # Keyword-targeted topics built around real search demand and buyer intent.
        # Each maps to a phrase prospects actually search, across the 6 target verticals.
        topics = [
            # Problem-aware / high intent
            "How to stop employees leaking data to ChatGPT",
            "Shadow AI risks and how to control them in the enterprise",
            "How to write an enterprise AI usage policy (with template)",
            "On-premise AI vs cloud AI: which is safer for sensitive data",
            "How to give employees ChatGPT access without security risk",
            "AI data loss prevention (DLP): a complete guide for IT teams",
            "How to detect and block PII before it reaches an AI model",
            # Compliance angle
            "HIPAA-compliant AI: how healthcare can use ChatGPT safely",
            "GDPR and AI: keeping employee AI use compliant in Europe",
            "AI compliance under India's DPDP Act: what businesses must do",
            "SOC 2 and AI tools: building an auditable AI workflow",
            "AI governance for law firms: protecting client confidentiality",
            # Vertical-specific
            "AI security for financial services: preventing data exposure",
            "Protecting trade secrets when manufacturing teams use AI",
            "AI access control for MSPs managing multiple client environments",
            "How consulting firms keep client data safe while using AI",
            # Comparison / decision
            "Self-hosted LLMs vs API models: a security comparison",
            "How to choose an enterprise AI gateway: a buyer's checklist",
            "The real cost of an AI data breach (and how to avoid it)",
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
