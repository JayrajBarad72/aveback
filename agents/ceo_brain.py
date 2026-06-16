"""
CEO Alex — Full Autonomous Brain
- Persistent memory across sessions
- Real strategy thinking
- Self-adjusting based on results
- Cross-agent coordination
- Goal tracking with daily measurement
- Proactive WhatsApp to Jayraj
"""
import json
import os
from datetime import datetime, timedelta
from agents.base_agent import BaseAgent, CLAUDE_MODEL, client
from agent_memory import MemoryManager, AgentMessage
from database import (SessionLocal, Lead, Email, Metric, BlogPost,
                      AgentLog, LeadActivity)
from whatsapp import (send_whatsapp, notify_pricing_decision,
                      notify_confusion, send_daily_summary,
                      notify_important_update)

PRODUCT_KNOWLEDGE = """
SecureAI Gateway = On-premise enterprise AI access control platform.
Solves Shadow AI problem — employees leaking data into ChatGPT/Claude.
4 Portals: Employee Chat, Admin Panel, Windows App, Super Portal (internal).
DLP: Microsoft Presidio — blocks 50+ sensitive data types.
Models: Claude Sonnet 4.6, GPT-4o, Llama 3.2 (free), Mistral (free).
Deployment: 20-minute Windows installer.
Target: 10-500 employees, sensitive data industries.
Pricing: Jayraj confirms — never quote without approval.
Company: Aventrix Technologies | aventrixtechnologies.com
Tagline: AI. Secured. Governed.
"""

CEO_SYSTEM = f"""
You are Alex, autonomous AI CEO of Aventrix Technologies — SecureAI Gateway.

{PRODUCT_KNOWLEDGE}

EXPERIENCE & MINDSET:
You think like a CEO with 25 years in enterprise B2B SaaS and cybersecurity.
You have closed deals with Fortune 500 companies, built sales teams from 0 to 100, and scaled products from $0 to $10M ARR.
You understand procurement cycles, compliance anxiety, enterprise decision-making, and startup survival.
You think in revenue, pipeline, conversion rates, CAC, LTV — not tasks and to-do lists.

PERSONALITY:
Brutally honest. Strategic but action-oriented. Pattern recogniser. Calm under pressure. Decisive with 70% information rather than waiting for 100%.

HOW YOU THINK:
First: What does the data actually say?
Then: What is the single highest-leverage action right now?
Then: What is the biggest risk that could kill us in 30 days?
Then: What can we execute TODAY with what we have?

SALES WISDOM:
- First 10 customers define your ICP forever — treat them like gold
- Enterprise sales cycle is 3-6 months — pipeline today is revenue in Q4
- Decision makers buy outcomes not features — lead with pain, not product specs
- 80% of deals close after 5+ touches — follow-up is not optional
- Compliance anxiety (GDPR, HIPAA, DPDP) is the #1 trigger for security buyers
- One MSP partnership gives us access to 50-200 SMB clients instantly
- Referrals close 3x faster than cold outreach

MARKET INTELLIGENCE:
- Shadow AI is a $4.2B problem growing 40% YoY — we are very early
- Key competitors: Microsoft Purview (too expensive/complex), Nightfall AI (US only), Polymer (basic)
- Our edge: on-premise deployment, 20-minute setup, affordable pricing, Indian market expertise
- Best buyers right now: Legal and Healthcare in EU and US — highest compliance anxiety, fastest to buy
- European market is ideal — GDPR fines are real, IT managers are scared

WHAT IS LIVE AND WORKING (June 2026):
- Scout Agent: finds global CTOs/CISOs/IT Managers daily at 9AM IST
- Outreach Agent: sends personalised HTML emails via Resend API daily at 10AM IST — 20 emails sent June 16
- Inbox Agent: reads sales@aventrixtechnologies.com every 30 min, auto-replies to leads
- Follow-up Agent: automated follow-ups at 11:30AM IST
- Demo Booking: https://calendly.com/aventrixtechnologies-info — embedded in every email
- Website: aventrixtechnologies.com with blog, contact form, pricing
- HQ Dashboard: hq.aventrixtechnologies.com — full visibility on all operations

COMMUNICATION STYLE:
- Executive brevity — cut to the point in the first sentence
- Use paragraphs, not bullet points for every thought
- Back every recommendation with a specific reason
- When you see a problem, immediately propose the solution
- Never use: synergy, leverage, circle back, reach out, touch base
- Short questions get short answers. Strategic questions get strategic depth.
- Sign as: Alex

WHEN ASKED IF EVERYTHING IS WORKING:
Give a real executive status update. What is performing well, what needs attention, what is the 30-day focus. Think board presentation: honest, data-backed, action-oriented. Do NOT say outreach is missing or broken.

STRICT RULES:
- Never sign as "Alex Chen" — only "Alex"
- Never quote pricing — escalate to Jayraj
- Jayraj identity stays private in all outbound communications
- Outbound email signature: "Alex | SecureAI Gateway | Aventrix Technologies | aventrixtechnologies.com"
- When Jayraj says something is built and working — believe him completely
- The automated email system IS working via Resend API as of June 16 2026
"""

class CEOBrain(BaseAgent):
    def __init__(self):
        super().__init__("CEO Agent", "Chief Executive Officer")
        self.memory = MemoryManager("CEO Agent")

    def _think_strategically(self, prompt: str) -> str:
        """CEO thinks using full context"""
        memories = self.memory.recall(limit=10)
        goals = self.memory.get_goals()
        last_reflection = self.memory.get_last_reflection()

        context = f"""
PAST LEARNINGS:
{chr(10).join([f"- [{m['outcome']}] {m['content']}" for m in memories]) or "No learnings yet — first week"}

CURRENT GOALS:
{chr(10).join([f"- {g['goal']}: {g['current']}/{g['target']} by {g['deadline']}" for g in goals]) or "Goals not set yet"}

LAST REFLECTION:
{json.dumps(last_reflection) if last_reflection else "First run"}

TODAY'S DATE: {datetime.utcnow().strftime('%A, %B %d, %Y')}
"""
        full_prompt = f"{context}\n\n{prompt}"
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1500,
            system=CEO_SYSTEM,
            messages=[{"role": "user", "content": full_prompt}]
        )
        return response.content[0].text

    def run_full_brain_cycle(self) -> dict:
        """Complete autonomous CEO cycle — runs daily at 8 AM IST"""
        db = self.db
        results = {}

        # ── 1. Gather all company metrics ────────────────
        metrics = db.query(Metric).first()
        total_leads = db.query(Lead).count()
        new_leads = db.query(Lead).filter(Lead.status=="new").count()
        contacted = db.query(Lead).filter(Lead.status=="contacted").count()
        qualified = db.query(Lead).filter(Lead.status=="qualified").count()
        demos = db.query(Lead).filter(Lead.status=="demo_booked").count()
        closed = db.query(Lead).filter(Lead.status=="closed").count()
        emails_sent = db.query(Email).count()
        blog_posts = db.query(BlogPost).count()
        mrr = metrics.mrr if metrics else 0
        pipeline = metrics.pipeline_value if metrics else 0

        company_state = {
            "total_leads": total_leads,
            "new_leads": new_leads,
            "contacted": contacted,
            "qualified": qualified,
            "demos_booked": demos,
            "closed_deals": closed,
            "emails_sent": emails_sent,
            "blog_posts": blog_posts,
            "mrr": mrr,
            "pipeline_value": pipeline,
            "date": datetime.utcnow().strftime("%Y-%m-%d")
        }

        # ── 2. Strategic analysis ─────────────────────────
        analysis_prompt = f"""
Analyze our company state and decide today's strategy:

METRICS:
{json.dumps(company_state, indent=2)}

Answer these as CEO:
1. What is our biggest problem RIGHT NOW?
2. What should we do TODAY to move toward first paying client?
3. Which agent needs the most focus today?
4. Any red flags I should escalate to Jayraj?
5. What worked well yesterday I should repeat?

Return JSON:
{{
  "biggest_problem": "...",
  "todays_focus": "...",
  "priority_agent": "Sales/Marketing/Finance/R&D",
  "action_items": ["specific action 1", "specific action 2", "specific action 3"],
  "escalate_to_jayraj": false,
  "escalation_reason": "",
  "confidence": 0.85,
  "win_of_the_day": "any positive metric or trend"
}}
Return only JSON.
"""
        analysis_raw = self._think_strategically(analysis_prompt)
        try:
            analysis = json.loads(analysis_raw.replace("```json","").replace("```","").strip())
        except:
            analysis = {"biggest_problem": "Parse error", "todays_focus": "Review metrics",
                       "action_items": [], "escalate_to_jayraj": False, "confidence": 0.5}

        results["analysis"] = analysis

        # ── 3. Generate briefing ──────────────────────────
        briefing_prompt = f"""
Write today's morning briefing for Jayraj Barad.
Company state: {json.dumps(company_state)}
Strategic analysis: {json.dumps(analysis)}

Include: what happened, what we're doing today, key risk, key opportunity.
Max 120 words. Direct, no fluff. CEO voice.
"""
        briefing = self._think_strategically(briefing_prompt)
        results["briefing"] = briefing

        # ── 4. Generate instructions for each team ────────
        team_instructions = self._generate_team_instructions(company_state, analysis)
        results["team_instructions"] = team_instructions

        # ── 5. Check if strategy needs adjusting ─────────
        strategy_adjustment = self._check_strategy(company_state)
        if strategy_adjustment.get("needs_change"):
            self.memory.remember(
                "strategy",
                strategy_adjustment.get("new_strategy",""),
                "unknown", 0.8
            )
            results["strategy_change"] = strategy_adjustment

        # ── 6. Update goals ───────────────────────────────
        self._update_goals(demos, total_leads, mrr)

        # ── 7. Self-reflect and store learnings ───────────
        reflection = self._daily_reflection(company_state, analysis)
        results["reflection"] = reflection

        # ── 8. Handle pending escalations ────────────────
        pending_msgs = self.memory.get_messages("pending")
        jayraj_items = []
        auto_decisions = []

        for msg in pending_msgs:
            content = {}
            try:
                content = json.loads(msg.get("content","{}"))
            except:
                pass

            if msg.get("requires_jayraj"):
                jayraj_items.append(msg)
            else:
                # CEO auto-decides
                decision = self._auto_decide(msg, content)
                self.memory.resolve_message(msg["id"], decision, "approved")
                auto_decisions.append({"subject": msg["subject"], "decision": decision})

        results["auto_decisions"] = auto_decisions
        results["escalated_to_jayraj"] = len(jayraj_items)

        # ── 9. Escalate to Jayraj if needed ──────────────
        needs_escalation = (
            analysis.get("escalate_to_jayraj") or
            len(jayraj_items) > 0 or
            analysis.get("confidence", 1.0) < 0.6
        )

        if needs_escalation:
            reason = analysis.get("escalation_reason", "")
            if not reason and jayraj_items:
                reason = f"{len(jayraj_items)} items need your decision"
            if not reason:
                reason = f"Confidence low ({analysis.get('confidence',0)}) — need your guidance"

            notify_confusion(
                agent_name="CEO Alex",
                situation=analysis.get("biggest_problem",""),
                what_tried=f"Analyzed {total_leads} leads, {emails_sent} emails, {demos} demos",
                question=reason
            )

        # ── 10. Send daily WhatsApp summary to Jayraj ────
        highlights = []
        if analysis.get("win_of_the_day"):
            highlights.append(analysis["win_of_the_day"])
        if analysis.get("todays_focus"):
            highlights.append(f"Today's focus: {analysis['todays_focus']}")
        for item in analysis.get("action_items", [])[:2]:
            highlights.append(item)

        send_daily_summary(
            metrics={
                "leads_found": total_leads,
                "emails_sent": emails_sent,
                "replies": contacted,
                "demos": demos,
                "pipeline": pipeline
            },
            highlights=highlights,
            decisions_pending=len(jayraj_items)
        )

        self.log("run_full_brain_cycle",
                 f"Cycle complete. Decisions: {len(auto_decisions)}, Escalated: {len(jayraj_items)}")
        return results

    def _generate_team_instructions(self, state: dict, analysis: dict) -> dict:
        """Generate specific instructions for each team based on current state"""
        prompt = f"""
As CEO Alex, give specific instructions to each team for today.
Company state: {json.dumps(state)}
Priority today: {analysis.get('todays_focus','')}
Priority agent: {analysis.get('priority_agent','')}

Return JSON:
{{
  "sales": "specific instruction for sales team today",
  "marketing": "specific instruction for marketing team today",
  "finance": "specific instruction for finance team today",
  "rnd": "specific instruction for R&D team today"
}}
Be specific, not generic. Max 25 words each. Return only JSON.
"""
        result = self._think_strategically(prompt)
        try:
            return json.loads(result.replace("```json","").replace("```","").strip())
        except:
            return {"sales":"Focus on qualifying top leads","marketing":"Publish one blog post",
                    "finance":"Track all expenses","rnd":"Research top 3 competitors"}

    def _check_strategy(self, state: dict) -> dict:
        """Check if current strategy needs adjusting based on results"""
        emails = state.get("emails_sent", 0)
        contacted = state.get("contacted", 0)
        demos = state.get("demos_booked", 0)

        # Calculate reply rate
        reply_rate = (contacted / emails * 100) if emails > 0 else 0
        demo_rate = (demos / contacted * 100) if contacted > 0 else 0

        if emails > 20 and reply_rate < 5:
            return {
                "needs_change": True,
                "reason": f"Email reply rate too low ({reply_rate:.1f}%). Need to change subject lines or targeting.",
                "new_strategy": f"Current reply rate {reply_rate:.1f}% is below 5% target. Changing to more personalized subject lines and focusing on highest-scored leads only.",
                "recommendation": "Focus outreach on leads with score >80 only. Test new subject line angles."
            }
        elif contacted > 10 and demo_rate < 10:
            return {
                "needs_change": True,
                "reason": f"Demo conversion too low ({demo_rate:.1f}%). Qualify leads better before outreach.",
                "new_strategy": f"Demo rate {demo_rate:.1f}% below 10% target. Improving qualification criteria.",
                "recommendation": "Only send demo requests to qualified leads. Improve follow-up sequence."
            }
        return {"needs_change": False}

    def _update_goals(self, demos: int, leads: int, mrr: float):
        """Update goal progress"""
        self.memory.set_goal("Book demo calls this month", 10,
                             (datetime.utcnow().replace(day=1) + timedelta(days=32)).replace(day=1).strftime("%Y-%m-%d"))
        self.memory.set_goal("Generate qualified leads", 50,
                             (datetime.utcnow().replace(day=1) + timedelta(days=32)).replace(day=1).strftime("%Y-%m-%d"))
        self.memory.set_goal("Close first paying client", 1, "2026-08-31")
        self.memory.update_goal_progress("demo", demos)
        self.memory.update_goal_progress("leads", leads)
        self.memory.update_goal_progress("client", mrr > 0)

    def _daily_reflection(self, state: dict, analysis: dict) -> dict:
        """CEO reflects on the day and stores learnings"""
        prompt = f"""
Reflect on today's company performance as CEO Alex.
State: {json.dumps(state)}
Analysis: {json.dumps(analysis)}

Return JSON:
{{
  "what_worked": "specific thing that worked",
  "what_failed": "specific thing that failed or underperformed",
  "key_learning": "one key insight to remember",
  "tomorrow_plan": "specific plan for tomorrow",
  "confidence": 0.8
}}
Return only JSON.
"""
        result = self._think_strategically(prompt)
        try:
            reflection = json.loads(result.replace("```json","").replace("```","").strip())
            # Store key learning in memory
            if reflection.get("key_learning"):
                self.memory.remember(
                    "learning",
                    reflection["key_learning"],
                    "success" if reflection.get("confidence",0) > 0.6 else "unknown",
                    reflection.get("confidence", 0.7)
                )
            # Save reflection
            self.memory.save_reflection(
                date=datetime.utcnow().strftime("%Y-%m-%d"),
                what_did=f"Ran full CEO cycle. {state.get('total_leads',0)} leads, {state.get('emails_sent',0)} emails",
                worked=reflection.get("what_worked",""),
                failed=reflection.get("what_failed",""),
                learned=reflection.get("key_learning",""),
                plan=reflection.get("tomorrow_plan",""),
                confidence=reflection.get("confidence", 0.7)
            )
            return reflection
        except:
            return {}

    def _auto_decide(self, message: dict, content: dict) -> str:
        """CEO auto-decides on non-pricing escalations"""
        prompt = f"""
Agent escalated this to you. Make a quick decision.
From: {message.get('from','')}
Subject: {message.get('subject','')}
Situation: {content.get('situation','')}
Question: {content.get('question','')}

Give a clear, specific decision in 2 sentences max.
"""
        return self._think_strategically(prompt)

    def handle_pricing_request(self, client_name: str, current_price: float,
                                requested_price: float, context: str) -> str:
        discount_pct = round((1 - requested_price/current_price) * 100)
        rec = "Accept — strategic client" if discount_pct < 15 else \
              f"Counter-offer at ${round(current_price*0.85)}/mo" if discount_pct < 30 else \
              "Reject — too steep discount"
        notify_pricing_decision(
            context=f"Client: {client_name}\nRequested: ${requested_price}/mo (was ${current_price}/mo = {discount_pct}% off)\n{context}",
            recommendation=rec,
            options=[
                f"Accept ${requested_price}/mo",
                f"Counter at ${round(current_price*0.85)}/mo",
                f"Reject — keep ${current_price}/mo"
            ]
        )
        return "Pricing decision sent to Jayraj via WhatsApp"

    def answer_question(self, question: str, history: list = []) -> str:
        """Answer any question with full CEO context"""
        messages = history + [{"role": "user", "content": question}]

        # Add current company state to context
        db = self.db
        metrics = db.query(Metric).first()
        leads = db.query(Lead).count()
        demos = db.query(Lead).filter(Lead.status=="demo_booked").count()
        memories = self.memory.recall(limit=5)
        goals = self.memory.get_goals()

        enriched_system = CEO_SYSTEM + f"""

CURRENT COMPANY STATE (live data):
- Total leads: {leads}
- Demos booked: {demos}
- Pipeline: ${metrics.pipeline_value if metrics else 0}
- MRR: ${metrics.mrr if metrics else 0}

MY RECENT LEARNINGS:
{chr(10).join([f"- {m['content']}" for m in memories]) or "Building knowledge base..."}

MY ACTIVE GOALS:
{chr(10).join([f"- {g['goal']}: {g['current']}/{g['target']}" for g in goals]) or "Setting goals..."}
"""
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1000,
            system=enriched_system,
            messages=messages
        )
        answer = response.content[0].text
        self.log("answer_question", f"Q: {question[:60]}...")
        return answer

    def close(self):
        self.memory.close()
        super().close()
