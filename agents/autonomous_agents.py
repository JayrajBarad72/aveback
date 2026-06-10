"""
Autonomous Self-Learning Agents
Each agent has:
- Memory (remembers what worked/failed)
- Goals (knows what it's trying to achieve)
- Self-reflection (reviews own performance daily)
- Decision making (plans own next steps)
- Escalation (asks CEO Alex when stuck)
"""
import json
import os
from datetime import datetime, timedelta
from agents.base_agent import BaseAgent, COMPANY_CONTEXT
from agent_memory import MemoryManager
from database import (Lead, Email, Metric, BlogPost, AgentLog,
                      LeadActivity, FollowUp, SessionLocal)
from whatsapp import notify_confusion, notify_pricing_decision, notify_important_update
import anthropic

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# ── Base Autonomous Agent ─────────────────────────────────
class AutonomousAgent(BaseAgent):
    def __init__(self, name: str, role: str):
        super().__init__(name, role)
        self.memory = MemoryManager(name)

    def think_and_plan(self, situation: str, context: dict = {}) -> dict:
        """Agent thinks about what to do next given a situation"""
        memories = self.memory.recall(limit=5)
        goals = self.memory.get_goals()
        last_reflection = self.memory.get_last_reflection()

        memory_text = "\n".join([f"- [{m['outcome']}] {m['content']}" for m in memories]) or "No memories yet"
        goals_text = "\n".join([f"- {g['goal']}: {g['current']}/{g['target']} by {g['deadline']}" for g in goals]) or "No goals set yet"

        prompt = f"""
You are {self.name} ({self.role}) at Aventrix Technologies.
Product: SecureAI Gateway — Enterprise AI access control SaaS.

YOUR MEMORIES (what worked/failed before):
{memory_text}

YOUR CURRENT GOALS:
{goals_text}

LAST REFLECTION:
{json.dumps(last_reflection) if last_reflection else "First time running"}

CURRENT SITUATION:
{situation}

CONTEXT DATA:
{json.dumps(context)}

Think step by step:
1. What is the most important thing to do right now to achieve my goals?
2. What have I learned from past attempts?
3. What is my confidence level (0-1)?
4. Do I need to escalate to CEO Alex? Why?
5. What is my specific action plan for today?

Return JSON:
{{
  "analysis": "what I understand about the situation",
  "priority_action": "the single most important thing to do",
  "action_steps": ["step1", "step2", "step3"],
  "confidence": 0.85,
  "needs_escalation": false,
  "escalation_reason": "",
  "escalation_priority": "normal",
  "expected_outcome": "what I expect to happen",
  "success_metric": "how I'll know it worked"
}}
Return only JSON.
"""
        result = self.think(prompt)
        try:
            clean = result.replace("```json","").replace("```","").strip()
            plan = json.loads(clean)
            # Auto-escalate if confidence too low
            if plan.get("confidence", 1.0) < 0.6 and not plan.get("needs_escalation"):
                plan["needs_escalation"] = True
                plan["escalation_reason"] = f"Confidence too low ({plan['confidence']}) — need guidance"
            return plan
        except:
            return {"analysis": result, "confidence": 0.5, "needs_escalation": True,
                    "escalation_reason": "Could not parse my own plan — need help"}

    def reflect(self, what_did: str, results: dict) -> dict:
        """Daily self-reflection — what worked, what didn't, what to do tomorrow"""
        memories = self.memory.recall(limit=10)
        prompt = f"""
You are {self.name} at Aventrix Technologies. Do your daily reflection.

WHAT YOU DID TODAY:
{what_did}

RESULTS:
{json.dumps(results)}

PAST MEMORIES:
{json.dumps(memories)}

Reflect honestly:
1. What specifically worked well?
2. What failed or underperformed?
3. What did you learn?
4. What will you do differently tomorrow?
5. Your confidence score (0-1) for tomorrow

Return JSON:
{{
  "what_worked": "specific things that succeeded",
  "what_failed": "specific things that failed",
  "learned": "key insight from today",
  "plan_tomorrow": "specific plan for tomorrow",
  "confidence": 0.8,
  "memory_to_store": "one key learning to remember forever"
}}
Return only JSON.
"""
        result = self.think(prompt)
        try:
            clean = result.replace("```json","").replace("```","").strip()
            reflection = json.loads(clean)
            # Save to memory
            if reflection.get("memory_to_store"):
                self.memory.remember("learning", reflection["memory_to_store"],
                                     "success" if reflection.get("confidence",0) > 0.6 else "failure",
                                     reflection.get("confidence", 0.7))
            # Save reflection
            self.memory.save_reflection(
                date=datetime.utcnow().strftime("%Y-%m-%d"),
                what_did=what_did,
                worked=reflection.get("what_worked",""),
                failed=reflection.get("what_failed",""),
                learned=reflection.get("learned",""),
                plan=reflection.get("plan_tomorrow",""),
                confidence=reflection.get("confidence", 0.7)
            )
            return reflection
        except:
            return {}

    def escalate_to_ceo(self, subject: str, situation: str, what_tried: str,
                         question: str, priority: str = "normal",
                         needs_pricing: bool = False) -> int:
        """Escalate issue to CEO Alex"""
        msg_id = self.memory.send_message(
            to_agent="CEO Agent",
            message_type="escalation",
            subject=subject,
            content=json.dumps({
                "situation": situation,
                "what_tried": what_tried,
                "question": question,
                "needs_pricing_decision": needs_pricing
            }),
            priority=priority,
            requires_jayraj=needs_pricing
        )
        self.log("escalate_to_ceo", f"Escalated: {subject}")
        return msg_id

    def close(self):
        self.memory.close()
        super().close()


# ── Autonomous Sales Manager ──────────────────────────────
class AutonomousSalesManager(AutonomousAgent):
    def __init__(self):
        super().__init__("Sales Manager", "Sales Team Lead")
        # Set initial goals
        self.memory.set_goal("Book demo calls this month", 10, self._end_of_month())
        self.memory.set_goal("Generate qualified leads", 50, self._end_of_month())
        self.memory.set_goal("Send outreach emails", 200, self._end_of_month())

    def _end_of_month(self):
        now = datetime.utcnow()
        return (now.replace(day=1) + timedelta(days=32)).replace(day=1).strftime("%Y-%m-%d")

    def run_autonomous_cycle(self) -> dict:
        """Full autonomous daily cycle"""
        db = self.db

        # Gather current metrics
        total_leads = db.query(Lead).count()
        emails_sent = db.query(Email).count()
        demos = db.query(Lead).filter(Lead.status == "demo_booked").count()
        qualified = db.query(Lead).filter(Lead.status == "qualified").count()
        new_leads = db.query(Lead).filter(Lead.status == "new").count()

        context = {
            "total_leads": total_leads,
            "emails_sent": emails_sent,
            "demos_booked": demos,
            "qualified_leads": qualified,
            "new_uncontacted_leads": new_leads
        }

        # Think and plan
        situation = f"""
Current sales status:
- {total_leads} total leads in system
- {new_leads} new leads not yet contacted
- {emails_sent} total emails sent
- {qualified} qualified leads
- {demos} demos booked this month
Goal: 10 demos this month
I need to decide: what should my sales team focus on today?
"""
        plan = self.think_and_plan(situation, context)

        actions_taken = []

        # Execute based on plan
        if plan.get("needs_escalation"):
            msg_id = self.escalate_to_ceo(
                subject=f"Sales Strategy Question: {plan.get('escalation_reason','')}",
                situation=situation,
                what_tried="Analyzed metrics and past performance",
                question=plan.get("escalation_reason", "Need guidance on next steps"),
                priority=plan.get("escalation_priority", "normal")
            )
            actions_taken.append(f"Escalated to CEO: {plan.get('escalation_reason')}")
        else:
            # Auto-execute approved actions
            priority_action = plan.get("priority_action", "")
            actions_taken.append(f"Priority: {priority_action}")

            # If many uncontacted leads — trigger outreach
            if new_leads > 5:
                actions_taken.append(f"Flagging {new_leads} uncontacted leads for outreach")
                self.memory.remember("strategy", f"When {new_leads}+ uncontacted leads exist, prioritize outreach", "success")

            # Update goal progress
            self.memory.update_goal_progress("demo", demos)
            self.memory.update_goal_progress("leads", total_leads)
            self.memory.update_goal_progress("emails", emails_sent)

        # Reflect on today
        reflection = self.reflect(
            what_did=f"Analyzed sales pipeline. {new_leads} new leads, {demos} demos booked.",
            results=context
        )

        self.log("autonomous_cycle", f"Sales cycle complete. Actions: {len(actions_taken)}")

        return {
            "agent": "Sales Manager",
            "plan": plan,
            "actions_taken": actions_taken,
            "reflection": reflection,
            "metrics": context
        }


# ── Autonomous Marketing Manager ──────────────────────────
class AutonomousMarketingManager(AutonomousAgent):
    def __init__(self):
        super().__init__("Marketing Manager", "Marketing Team Lead")
        self.memory.set_goal("Publish blog posts this month", 8, self._end_of_month())
        self.memory.set_goal("Generate social media posts", 30, self._end_of_month())

    def _end_of_month(self):
        now = datetime.utcnow()
        return (now.replace(day=1) + timedelta(days=32)).replace(day=1).strftime("%Y-%m-%d")

    def run_autonomous_cycle(self) -> dict:
        db = self.db
        blog_count = db.query(BlogPost).count()
        leads_count = db.query(Lead).count()

        context = {"blog_posts": blog_count, "total_leads": leads_count}

        situation = f"""
Marketing status:
- {blog_count} blog posts written
- Goal: 8 posts this month
- {leads_count} leads in pipeline need nurturing content
What should marketing focus on today?
"""
        plan = self.think_and_plan(situation, context)
        actions_taken = []

        if plan.get("needs_escalation"):
            self.escalate_to_ceo(
                subject=f"Marketing Strategy: {plan.get('escalation_reason')}",
                situation=situation,
                what_tried="Reviewed content calendar and lead pipeline",
                question=plan.get("escalation_reason", "")
            )
            actions_taken.append("Escalated to CEO Alex")
        else:
            actions_taken.append(f"Plan: {plan.get('priority_action','')}")
            self.memory.update_goal_progress("blog", blog_count)

        reflection = self.reflect(
            what_did=f"Reviewed marketing pipeline. {blog_count} posts published.",
            results=context
        )

        return {"agent": "Marketing Manager", "plan": plan,
                "actions_taken": actions_taken, "reflection": reflection}


# ── Autonomous Finance Agent ──────────────────────────────
class AutonomousFinanceAgent(AutonomousAgent):
    def __init__(self):
        super().__init__("Finance Agent", "Financial Controller")
        self.memory.set_goal("Reach MRR target", 1000, self._end_of_month())

    def _end_of_month(self):
        now = datetime.utcnow()
        return (now.replace(day=1) + timedelta(days=32)).replace(day=1).strftime("%Y-%m-%d")

    def run_autonomous_cycle(self) -> dict:
        db = self.db
        metrics = db.query(Metric).first()
        mrr = metrics.mrr if metrics else 0
        pipeline = metrics.pipeline_value if metrics else 0

        context = {"mrr": mrr, "pipeline_value": pipeline}

        situation = f"""
Finance status:
- Current MRR: ${mrr}
- Pipeline value: ${pipeline}
- Target MRR: $1000/month
What financial actions should be taken today?
"""
        plan = self.think_and_plan(situation, context)
        actions_taken = []

        if plan.get("needs_escalation"):
            needs_pricing = "pricing" in plan.get("escalation_reason","").lower()
            self.escalate_to_ceo(
                subject=f"Finance Alert: {plan.get('escalation_reason')}",
                situation=situation,
                what_tried="Analyzed revenue metrics",
                question=plan.get("escalation_reason",""),
                needs_pricing=needs_pricing
            )
            actions_taken.append("Escalated to CEO Alex")

        reflection = self.reflect(
            what_did=f"Reviewed finances. MRR: ${mrr}, Pipeline: ${pipeline}",
            results=context
        )

        return {"agent": "Finance Agent", "plan": plan,
                "actions_taken": actions_taken, "reflection": reflection}


# ── Autonomous R&D Agent ──────────────────────────────────
class AutonomousRnDAgent(AutonomousAgent):
    def __init__(self):
        super().__init__("R&D Agent", "Research & Development")

    def run_autonomous_cycle(self) -> dict:
        situation = """
R&D status:
- Need to research competitor movements
- Need to identify new feature opportunities
- Market is evolving rapidly in AI governance space
What should R&D focus on this week?
"""
        plan = self.think_and_plan(situation, {})
        actions_taken = [f"Plan: {plan.get('priority_action','')}"]

        if plan.get("needs_escalation"):
            self.escalate_to_ceo(
                subject=f"R&D Insight: {plan.get('escalation_reason')}",
                situation=situation,
                what_tried="Market research and competitor analysis",
                question=plan.get("escalation_reason","")
            )

        reflection = self.reflect("Conducted R&D research", {"plan": plan})
        return {"agent": "R&D Agent", "plan": plan,
                "actions_taken": actions_taken, "reflection": reflection}


# ── CEO Alex — The Orchestrator ───────────────────────────
class CEOAlex(AutonomousAgent):
    def __init__(self):
        super().__init__("CEO Agent", "Chief Executive Officer")
        self.memory.set_goal("Close first paying client", 1, "2026-07-31")
        self.memory.set_goal("Reach 10 demos booked", 10, "2026-06-30")

    def run_daily_orchestration(self) -> dict:
        """CEO runs all departments, handles escalations, reports to Jayraj"""
        from agents.ceo_agent import CEOAgent
        base_ceo = CEOAgent()

        # 1. Get department reports
        sales_report = AutonomousSalesManager().run_autonomous_cycle()
        marketing_report = AutonomousMarketingManager().run_autonomous_cycle()
        finance_report = AutonomousFinanceAgent().run_autonomous_cycle()
        rnd_report = AutonomousRnDAgent().run_autonomous_cycle()

        # 2. Handle pending escalations
        pending = self.memory.get_messages("pending")
        decisions_made = []
        needs_jayraj = []

        for msg in pending:
            if msg.get("requires_jayraj"):
                needs_jayraj.append(msg)
            else:
                # CEO auto-decides
                decision = self._make_decision(msg)
                self.memory.resolve_message(msg["id"], decision["response"], decision["status"])
                decisions_made.append({"message": msg["subject"], "decision": decision["response"]})

        # 3. Handle escalations needing Jayraj
        for msg in needs_jayraj:
            content = json.loads(msg.get("content","{}"))
            notify_confusion(
                agent_name=msg["from"],
                situation=content.get("situation",""),
                what_tried=content.get("what_tried",""),
                question=content.get("question","")
            )

        # 4. Generate daily briefing
        db = self.db
        metrics = db.query(Metric).first()
        leads = db.query(Lead).count()
        demos = db.query(Lead).filter(Lead.status=="demo_booked").count()
        emails = db.query(Email).count()

        # 5. Self-reflect as CEO
        situation = f"""
Company status today:
- {leads} total leads
- {demos} demos booked  
- {emails} emails sent
- {len(pending)} escalations received
- {len(needs_jayraj)} items need Jayraj's input
Sales: {sales_report.get('plan',{}).get('analysis','')}
Marketing: {marketing_report.get('plan',{}).get('analysis','')}
Finance: {finance_report.get('plan',{}).get('analysis','')}
"""
        ceo_plan = self.think_and_plan(situation, {"demos": demos, "leads": leads})

        # 6. Send daily WhatsApp summary to Jayraj
        highlights = []
        for report in [sales_report, marketing_report, finance_report, rnd_report]:
            action = report.get("plan",{}).get("priority_action","")
            if action:
                highlights.append(f"{report['agent']}: {action}")

        from whatsapp import send_daily_summary
        send_daily_summary(
            metrics={"leads_found": leads, "emails_sent": emails,
                     "replies": 0, "demos": demos,
                     "pipeline": metrics.pipeline_value if metrics else 0},
            highlights=highlights,
            decisions_pending=len(needs_jayraj)
        )

        self.log("daily_orchestration", f"CEO cycle complete. {len(decisions_made)} decisions, {len(needs_jayraj)} need Jayraj")

        return {
            "ceo_plan": ceo_plan,
            "department_reports": {
                "sales": sales_report,
                "marketing": marketing_report,
                "finance": finance_report,
                "rnd": rnd_report
            },
            "decisions_made": decisions_made,
            "escalated_to_jayraj": len(needs_jayraj),
            "metrics": {"leads": leads, "demos": demos, "emails": emails}
        }

    def _make_decision(self, message: dict) -> dict:
        """CEO auto-decides on non-pricing escalations"""
        content = json.loads(message.get("content","{}"))
        prompt = f"""
You are Alex, CEO of Aventrix Technologies (SecureAI Gateway).
An agent has escalated this to you:

From: {message['from']}
Subject: {message['subject']}
Situation: {content.get('situation','')}
Question: {content.get('question','')}
What they tried: {content.get('what_tried','')}

Make a clear decision. Be specific and actionable.
Return JSON: {{"decision":"approve/reject/modify","response":"your specific guidance","action_items":["what agent should do next"]}}
Return only JSON.
"""
        result = self.think(prompt)
        try:
            clean = result.replace("```json","").replace("```","").strip()
            data = json.loads(clean)
            return {"status": data.get("decision","approved"),
                    "response": data.get("response","") + " | Steps: " + str(data.get("action_items",[]))}
        except:
            return {"status": "approved", "response": "Proceed with your best judgment. I trust you."}

    def handle_pricing_request(self, client_name: str, current_price: float,
                                requested_price: float, context: str) -> str:
        """CEO asks Jayraj about pricing via WhatsApp"""
        discount_pct = round((1 - requested_price/current_price) * 100)
        notify_pricing_decision(
            context=f"Client: {client_name}\nRequested: ${requested_price}/mo (was ${current_price}/mo = {discount_pct}% discount)\n{context}",
            recommendation=f"{'Accept — strategic client' if discount_pct < 20 else 'Counter-offer at ' + str(round(current_price*0.85)) if discount_pct < 35 else 'Reject — too steep'}",
            options=[
                f"Accept ${requested_price}/mo",
                f"Counter-offer at ${round(current_price*0.85)}/mo",
                f"Reject — keep ${current_price}/mo"
            ]
        )
        return "Pricing decision sent to Jayraj via WhatsApp. Waiting for response."
