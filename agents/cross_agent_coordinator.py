"""
Cross-Agent Coordinator
Agents talk to each other and share intelligence.
Example: Marketing publishes HIPAA blog → tells Sales to target healthcare now
"""
import json
from datetime import datetime
from agents.base_agent import BaseAgent, client
from agent_memory import MemoryManager, AgentMessage
from database import Lead, BlogPost, Email, SessionLocal

class CrossAgentCoordinator(BaseAgent):
    def __init__(self):
        super().__init__("Coordinator", "Cross-Agent Intelligence")

    def coordinate_daily(self) -> list:
        """
        Run daily cross-agent coordination.
        Each agent shares its status and gets instructions from others.
        """
        db = self.db
        actions = []

        # ── Marketing → Sales Intelligence ───────────────
        # If new blog published → tell sales to use it in outreach
        recent_blogs = db.query(BlogPost).order_by(
            BlogPost.created_at.desc()
        ).limit(3).all()

        if recent_blogs:
            blog_topics = [b.title for b in recent_blogs]
            # Find leads matching blog topics
            for blog in recent_blogs:
                keywords = (blog.keywords or "").split(",")
                for kw in keywords[:2]:
                    kw = kw.strip()
                    if not kw:
                        continue
                    # Find leads in related industry
                    if "healthcare" in kw.lower() or "hipaa" in kw.lower():
                        actions.append({
                            "from": "Marketing",
                            "to": "Sales",
                            "action": f"Blog published: '{blog.title}' — prioritize Healthcare leads, mention blog in outreach",
                            "priority": "high"
                        })
                    elif "finance" in kw.lower() or "fintech" in kw.lower():
                        actions.append({
                            "from": "Marketing",
                            "to": "Sales",
                            "action": f"Blog published: '{blog.title}' — prioritize Finance leads today",
                            "priority": "high"
                        })

        # ── Sales → Marketing Intelligence ───────────────
        # If many qualified leads → marketing should create case studies
        qualified_count = db.query(Lead).filter(Lead.status=="qualified").count()
        demo_count = db.query(Lead).filter(Lead.status=="demo_booked").count()

        if qualified_count > 5:
            actions.append({
                "from": "Sales",
                "to": "Marketing",
                "action": f"{qualified_count} qualified leads. Create urgency content — case studies, ROI calculators",
                "priority": "high"
            })

        if demo_count > 2:
            actions.append({
                "from": "Sales",
                "to": "Marketing",
                "action": f"{demo_count} demos booked. Prepare demo follow-up email sequence and proposal templates",
                "priority": "urgent"
            })

        # ── Finance → Sales Intelligence ─────────────────
        emails_sent = db.query(Email).count()
        if emails_sent > 100:
            actions.append({
                "from": "Finance",
                "to": "Sales",
                "action": f"High email volume ({emails_sent}). Focus on quality over quantity — target score 80+ leads only",
                "priority": "normal"
            })

        # ── R&D → All Agents Intelligence ────────────────
        # Suggest focus areas based on market
        actions.append({
            "from": "R&D",
            "to": "Marketing",
            "action": "EU AI Act enforcement increasing. Create content about AI compliance — strong SEO opportunity",
            "priority": "normal"
        })

        # Store all coordination actions in agent messages
        for action in actions:
            from_memory = MemoryManager(action["from"] + " Agent")
            from_memory.send_message(
                to_agent=action["to"] + " Team",
                message_type="coordination",
                subject=action["action"][:100],
                content=json.dumps({"action": action["action"], "from": action["from"]}),
                priority=action["priority"]
            )
            from_memory.close()

        self.log("coordinate_daily", f"Generated {len(actions)} cross-agent actions")
        return actions

    def generate_company_intelligence_report(self) -> dict:
        """Full company intelligence — what every agent knows"""
        db = self.db

        leads = db.query(Lead).all()
        total = len(leads)
        by_status = {}
        by_industry = {}
        top_leads = []

        for lead in leads:
            # Count by status
            by_status[lead.status] = by_status.get(lead.status, 0) + 1
            # Count by industry
            by_industry[lead.industry] = by_industry.get(lead.industry, 0) + 1
            # Top leads
            if lead.score >= 80 and lead.status in ["new","contacted"]:
                top_leads.append({
                    "company": lead.company,
                    "contact": lead.contact_name,
                    "email": lead.email,
                    "score": lead.score,
                    "status": lead.status
                })

        top_leads.sort(key=lambda x: x["score"], reverse=True)

        emails_sent = db.query(Email).filter(Email.direction=="outbound").count()
        replies = db.query(Email).filter(Email.direction=="inbound").count()
        reply_rate = round((replies/emails_sent*100),1) if emails_sent > 0 else 0

        blogs = db.query(BlogPost).count()

        report = {
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "leads": {
                "total": total,
                "by_status": by_status,
                "by_industry": by_industry,
                "top_priority": top_leads[:5]
            },
            "outreach": {
                "emails_sent": emails_sent,
                "replies_received": replies,
                "reply_rate": f"{reply_rate}%"
            },
            "content": {
                "blog_posts": blogs
            },
            "recommendations": self._generate_recommendations(by_status, reply_rate, total)
        }

        self.log("intelligence_report", f"Report generated: {total} leads, {reply_rate}% reply rate")
        return report

    def _generate_recommendations(self, status_counts: dict, reply_rate: float, total_leads: int) -> list:
        """AI generates recommendations based on company data"""
        prompt = f"""
Analyze this sales data and give 3 specific recommendations:
- Total leads: {total_leads}
- Lead statuses: {json.dumps(status_counts)}
- Email reply rate: {reply_rate}%

For each recommendation, say exactly what to do and why.
Return JSON: [{{"action":"...","reason":"...","priority":"high/medium/low"}}]
Return only JSON array.
"""
        result = self.think(prompt)
        try:
            clean = result.replace("```json","").replace("```","").strip()
            return json.loads(clean)
        except:
            return []
