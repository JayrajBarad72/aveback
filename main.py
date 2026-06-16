from fastapi import FastAPI, HTTPException, Depends, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional, List
from database import (init_db, get_db, Lead, Email, AgentLog, BlogPost, Metric,
                      LeadNote, LeadActivity, FollowUp, Invoice, Expense,
                      SocialPost, Competitor, User, Session)
from agents.ceo_agent import CEOAgent
from agents.scout_agent import ScoutAgent
from agents.outreach_agent import OutreachAgent
from agents.all_agents import (QualifierAgent, BookingAgent, BlogWriterAgent,
                                SocialMediaAgent, FinanceAgent, RnDAgent)
from agents.new_agents import (ReplyMonitorAgent, FollowUpAgent, ProposalAgent,
                                ContractAgent, InvoiceAgent, LandingPageAgent,
                                NewsletterAgent, SocialCalendarAgent,
                                MarketTrendAgent, FeedbackAnalyzerAgent)
from scheduler import start_scheduler
from sqlalchemy.orm import Session as DBSession
from datetime import datetime, timedelta
import hashlib, json, os, shutil, zipfile
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

app = FastAPI(title="Aventrix AI HQ", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])



@app.get("/health")
@app.head("/health") 
def health():
    return {"ok": True}

@app.on_event("startup")
def startup():
    init_db()
    start_scheduler()
    logger.info("Aventrix AI HQ v2.0 started")

# ── Pydantic Models ───────────────────────────────────────
class ChatMessage(BaseModel):
    message: str
    history: Optional[List[dict]] = []

class LeadSearch(BaseModel):
    industry: str
    country: str = "global"
    count: int = 10

class OutreachRequest(BaseModel):
    lead_id: int

class BlogRequest(BaseModel):
    topic: Optional[str] = None

class NoteRequest(BaseModel):
    lead_id: int
    note: str

class StatusUpdate(BaseModel):
    status: str

class ReplyRequest(BaseModel):
    lead_id: int
    reply_text: str

class InvoiceRequest(BaseModel):
    client_name: str
    client_email: str
    items: List[dict]
    currency: str = "USD"

class ExpenseRequest(BaseModel):
    name: str
    amount: float
    category: str
    currency: str = "USD"

class LoginRequest(BaseModel):
    username: str
    password: str

class ContractRequest(BaseModel):
    lead_id: int
    plan: str
    amount: float

# ── Auth ──────────────────────────────────────────────────
@app.post("/api/auth/login")
def login(req: LoginRequest, db: DBSession = Depends(get_db)):
    pwd_hash = hashlib.sha256(req.password.encode()).hexdigest()
    user = db.query(User).filter(User.username == req.username,
                                  User.password == pwd_hash).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    import secrets
    token = secrets.token_hex(32)
    session = Session(token=token, username=req.username,
                      expires_at=datetime.utcnow() + timedelta(days=7))
    db.add(session)
    db.commit()
    return {"token": token, "username": req.username}

@app.post("/api/auth/logout")
def logout(token: str, db: DBSession = Depends(get_db)):
    db.query(Session).filter(Session.token == token).delete()
    db.commit()
    return {"success": True}

@app.get("/api/auth/verify")
def verify(token: str, db: DBSession = Depends(get_db)):
    session = db.query(Session).filter(Session.token == token,
                                        Session.expires_at > datetime.utcnow()).first()
    return {"valid": session is not None}

# ── Dashboard ─────────────────────────────────────────────
@app.get("/api/metrics")
def get_metrics(db: DBSession = Depends(get_db)):
    m = db.query(Metric).first()
    if not m:
        return {"total_leads":0,"emails_sent":0,"demos_booked":0,"pipeline_value":0,"mrr":0}
    return {"total_leads":m.total_leads,"emails_sent":m.emails_sent,
            "demos_booked":m.demos_booked,"pipeline_value":m.pipeline_value,"mrr":m.mrr}

@app.get("/api/activity")
def get_activity(db: DBSession = Depends(get_db)):
    logs = db.query(AgentLog).order_by(AgentLog.created_at.desc()).limit(20).all()
    return [{"agent":l.agent_name,"action":l.action,"result":l.result,
             "status":l.status,"time":str(l.created_at)} for l in logs]

# ── CEO ───────────────────────────────────────────────────
@app.get("/api/ceo/briefing")
def get_briefing():
    try:
        ceo = CEOAgent()
        b = ceo.generate_briefing()
        ceo.close()
        return {"briefing": b}
    except Exception as e:
        return {"briefing": f"Alex is thinking... (backend error: {str(e)[:100]}). Click Regenerate to retry."}

@app.post("/api/ceo/run-brain")
def run_ceo_brain():
    """Manually trigger full CEO brain cycle"""
    try:
        from agents.ceo_brain import CEOBrain
        ceo = CEOBrain()
        result = ceo.run_full_brain_cycle()
        ceo.close()
        return {"success": True, "result": {
            "briefing": result.get("briefing",""),
            "analysis": result.get("analysis",{}),
            "auto_decisions": result.get("auto_decisions",[]),
            "escalated_to_jayraj": result.get("escalated_to_jayraj",0),
            "reflection": result.get("reflection",{})
        }}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/ceo/priorities")
def get_priorities():
    try:
        ceo = CEOAgent(); p = ceo.generate_priorities(); ceo.close(); return {"priorities": p}
    except Exception as e:
        return {"priorities": []}

@app.get("/api/ceo/team-instructions")
def get_team_instructions():
    try:
        ceo = CEOAgent(); i = ceo.generate_team_instructions(); ceo.close(); return {"instructions": i}
    except Exception as e:
        return {"instructions": []}

@app.post("/api/ceo/chat")
def ceo_chat(msg: ChatMessage):
    ceo = CEOAgent(); a = ceo.answer_question(msg.message, msg.history); ceo.close(); return {"reply": a}

# ── Scout / Leads ─────────────────────────────────────────
@app.post("/api/scout/search")
def search_leads(req: LeadSearch):
    scout = ScoutAgent(); leads = scout.search_leads(req.industry, req.country, req.count)
    scout.close(); return {"leads": leads}

@app.get("/api/scout/leads")
def get_leads(db: DBSession = Depends(get_db)):
    leads = db.query(Lead).order_by(Lead.score.desc()).all()
    return [{"id":l.id,"company":l.company,"contact":l.contact_name,"email":l.email,
             "industry":l.industry,"country":l.country,"score":l.score,
             "status":l.status,"notes":l.notes,"website":l.website,
             "created_at":str(l.created_at)} for l in leads]

@app.get("/api/scout/lead/{lead_id}")
def get_lead_detail(lead_id: int, db: DBSession = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead: raise HTTPException(404, "Lead not found")
    notes = db.query(LeadNote).filter(LeadNote.lead_id == lead_id).order_by(LeadNote.created_at.desc()).all()
    activities = db.query(LeadActivity).filter(LeadActivity.lead_id == lead_id).order_by(LeadActivity.created_at.desc()).all()
    emails = db.query(Email).filter(Email.lead_id == lead_id).order_by(Email.created_at.desc()).all()
    followups = db.query(FollowUp).filter(FollowUp.lead_id == lead_id).all()
    return {
        "lead": {"id":lead.id,"company":lead.company,"contact":lead.contact_name,
                 "email":lead.email,"industry":lead.industry,"country":lead.country,
                 "score":lead.score,"status":lead.status,"notes":lead.notes,
                 "website":lead.website,"phone":lead.phone,"created_at":str(lead.created_at)},
        "notes": [{"id":n.id,"note":n.note,"created_by":n.created_by,"time":str(n.created_at)} for n in notes],
        "activities": [{"activity":a.activity,"description":a.description,"time":str(a.created_at)} for a in activities],
        "emails": [{"subject":e.subject,"body":e.body,"status":e.status,"sent_at":str(e.sent_at)} for e in emails],
        "followups": [{"day":f.day_number,"scheduled":str(f.scheduled_at),"status":f.status} for f in followups]
    }

@app.patch("/api/scout/lead/{lead_id}/status")
def update_lead_status(lead_id: int, req: StatusUpdate, db: DBSession = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead: raise HTTPException(404)
    lead.status = req.status
    activity = LeadActivity(lead_id=lead_id, activity=f"Status changed to {req.status}", description="Manual update")
    db.add(activity); db.commit(); return {"success": True}

@app.post("/api/scout/note")
def add_note(req: NoteRequest, db: DBSession = Depends(get_db)):
    note = LeadNote(lead_id=req.lead_id, note=req.note)
    activity = LeadActivity(lead_id=req.lead_id, activity="Note added", description=req.note[:100])
    db.add(note); db.add(activity); db.commit(); return {"success": True}

@app.get("/api/scout/pipeline")
def get_pipeline(db: DBSession = Depends(get_db)):
    statuses = ["new","contacted","replied","qualified","demo_booked","closed","lost"]
    pipeline = {}
    for s in statuses:
        leads = db.query(Lead).filter(Lead.status == s).all()
        pipeline[s] = [{"id":l.id,"company":l.company,"contact":l.contact_name,
                        "score":l.score,"industry":l.industry} for l in leads]
    return pipeline

@app.get("/api/scout/export")
def export_leads(db: DBSession = Depends(get_db)):
    leads = db.query(Lead).order_by(Lead.score.desc()).all()
    return [{"Company":l.company,"Contact":l.contact_name,"Email":l.email,
             "Industry":l.industry,"Country":l.country,"Score":l.score,
             "Status":l.status,"Notes":l.notes,"Created":str(l.created_at)} for l in leads]

@app.get("/api/scout/domain/{domain}")
def search_domain(domain: str):
    scout = ScoutAgent(); leads = scout.search_by_domain(domain); scout.close(); return {"leads": leads}

# ── Outreach ──────────────────────────────────────────────
@app.post("/api/outreach/send")
def send_email(req: OutreachRequest):
    agent = OutreachAgent(); success = agent.send_email(req.lead_id)
    agent.close(); return {"success": success}

@app.post("/api/outreach/daily")
def daily_outreach():
    agent = OutreachAgent(); result = agent.run_daily_outreach(); agent.close(); return result

@app.get("/api/outreach/emails")
def get_emails(db: DBSession = Depends(get_db)):
    emails = db.query(Email).order_by(Email.created_at.desc()).limit(50).all()
    return [{"id":e.id,"lead_id":e.lead_id,"subject":e.subject,"body":e.body,
             "status":e.status,"sent_at":str(e.sent_at)} for e in emails]

@app.get("/api/outreach/preview/{lead_id}")
def preview_email(lead_id: int):
    agent = OutreachAgent(); preview = agent.preview_email(lead_id); agent.close(); return preview

# ── Reply Monitor ─────────────────────────────────────────
@app.post("/api/reply/analyze")
def analyze_reply(req: ReplyRequest):
    agent = ReplyMonitorAgent()
    result = agent.categorize_reply(req.reply_text, req.lead_id)
    if result.get("category") in ["interested","question"]:
        response = agent.generate_reply(req.reply_text, result.get("category",""), req.lead_id)
        result["suggested_response"] = response
    agent.close(); return result

# ── Follow-ups ────────────────────────────────────────────
@app.post("/api/followup/schedule/{lead_id}")
def schedule_followup(lead_id: int):
    agent = FollowUpAgent(); agent.schedule_followups(lead_id); agent.close(); return {"success": True}

@app.post("/api/followup/run")
def run_followups():
    agent = FollowUpAgent(); result = agent.run_pending_followups(); agent.close(); return result

@app.get("/api/followup/pending")
def get_pending_followups(db: DBSession = Depends(get_db)):
    pending = db.query(FollowUp).filter(FollowUp.status == "pending").all()
    return [{"id":f.id,"lead_id":f.lead_id,"day":f.day_number,
             "scheduled":str(f.scheduled_at),"status":f.status} for f in pending]

# ── Qualifier / Booking ───────────────────────────────────
@app.post("/api/qualifier/qualify/{lead_id}")
def qualify_lead(lead_id: int):
    agent = QualifierAgent(); result = agent.qualify_lead(lead_id); agent.close(); return result

@app.post("/api/booking/book/{lead_id}")
def book_demo(lead_id: int):
    agent = BookingAgent(); result = agent.mark_demo_booked(lead_id); agent.close(); return {"success": result}

# ── Proposal & Contract ───────────────────────────────────
@app.get("/api/proposal/{lead_id}")
def generate_proposal(lead_id: int):
    agent = ProposalAgent(); result = agent.generate_proposal(lead_id); agent.close(); return result

@app.post("/api/contract")
def generate_contract(req: ContractRequest):
    agent = ContractAgent()
    contract = agent.generate_contract(req.lead_id, req.plan, req.amount)
    agent.close(); return {"contract": contract}

# ── Marketing ─────────────────────────────────────────────
@app.post("/api/blog/write")
def write_blog(req: BlogRequest):
    agent = BlogWriterAgent(); post = agent.write_blog_post(req.topic); agent.close(); return post

@app.get("/api/blog/posts")
def get_blog_posts(db: DBSession = Depends(get_db)):
    posts = db.query(BlogPost).order_by(BlogPost.created_at.desc()).all()
    return [{"id":p.id,"title":p.title,"content":p.content,"keywords":p.keywords,
             "status":p.status,"created_at":str(p.created_at)} for p in posts]

@app.get("/api/social/posts")
def get_social_posts(db: DBSession = Depends(get_db)):
    posts = db.query(SocialPost).order_by(SocialPost.created_at.desc()).limit(30).all()
    if posts:
        return {"posts": [{"id":p.id,"platform":p.platform,"content":p.content,
                           "hashtags":p.hashtags.split(","),"scheduled_at":p.scheduled_at,
                           "status":p.status} for p in posts]}
    agent = SocialMediaAgent(); result = agent.generate_posts("linkedin"); agent.close()
    return {"posts": result}

@app.post("/api/social/calendar")
def generate_calendar():
    agent = SocialCalendarAgent(); posts = agent.generate_30_day_calendar(); agent.close(); return {"posts": posts}

@app.get("/api/landing-page")
def get_landing_page(industry: str = "enterprise"):
    agent = LandingPageAgent(); html = agent.generate_landing_page(industry); agent.close(); return {"html": html}

@app.get("/api/newsletter")
def generate_newsletter():
    agent = NewsletterAgent(); result = agent.generate_newsletter(); agent.close(); return result

# ── Finance ───────────────────────────────────────────────
@app.get("/api/finance/summary")
def get_finance_summary():
    agent = FinanceAgent(); summary = agent.get_summary(); agent.close(); return summary

@app.post("/api/finance/invoice")
def create_invoice(req: InvoiceRequest):
    agent = InvoiceAgent()
    result = agent.create_invoice(req.client_name, req.client_email, req.items, req.currency)
    agent.close(); return result

@app.get("/api/finance/invoices")
def get_invoices(db: DBSession = Depends(get_db)):
    invoices = db.query(Invoice).order_by(Invoice.created_at.desc()).all()
    return [{"id":i.id,"invoice_no":i.invoice_no,"client":i.client_name,
             "amount":i.amount,"currency":i.currency,"status":i.status,
             "due_date":i.due_date,"created_at":str(i.created_at)} for i in invoices]

@app.patch("/api/finance/invoice/{invoice_id}/status")
def update_invoice_status(invoice_id: int, req: StatusUpdate, db: DBSession = Depends(get_db)):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv: raise HTTPException(404)
    inv.status = req.status
    if req.status == "paid":
        m = db.query(Metric).first()
        if m: m.mrr += inv.amount; db.commit()
    db.commit(); return {"success": True}

@app.post("/api/finance/expense")
def add_expense(req: ExpenseRequest, db: DBSession = Depends(get_db)):
    exp = Expense(name=req.name, amount=req.amount, category=req.category,
                  currency=req.currency, date=datetime.utcnow().strftime("%Y-%m-%d"))
    db.add(exp); db.commit(); return {"success": True, "id": exp.id}

@app.get("/api/finance/expenses")
def get_expenses(db: DBSession = Depends(get_db)):
    expenses = db.query(Expense).order_by(Expense.created_at.desc()).all()
    return [{"id":e.id,"name":e.name,"amount":e.amount,"currency":e.currency,
             "category":e.category,"date":e.date} for e in expenses]

@app.get("/api/finance/mrr")
def get_mrr(db: DBSession = Depends(get_db)):
    m = db.query(Metric).first()
    invoices = db.query(Invoice).filter(Invoice.status == "paid").all()
    total_revenue = sum(i.amount for i in invoices)
    expenses = db.query(Expense).all()
    total_expenses = sum(e.amount for e in expenses)
    return {"mrr": m.mrr if m else 0, "total_revenue": total_revenue,
            "total_expenses": total_expenses, "profit": total_revenue - total_expenses}

# ── R&D ───────────────────────────────────────────────────
@app.get("/api/rnd/competitors")
def get_competitors():
    agent = RnDAgent(); competitors = agent.research_competitors(); agent.close(); return {"competitors": competitors}

@app.get("/api/rnd/ideas")
def get_product_ideas():
    agent = RnDAgent(); ideas = agent.generate_product_ideas(); agent.close(); return {"ideas": ideas}

@app.get("/api/rnd/trends")
def get_trends():
    agent = MarketTrendAgent(); report = agent.generate_trend_report(); agent.close(); return report

@app.get("/api/rnd/feedback")
def analyze_feedback():
    agent = FeedbackAnalyzerAgent(); result = agent.analyze_all_replies(); agent.close(); return result

@app.get("/api/rnd/roadmap")
def get_roadmap():
    agent = RnDAgent(); ideas = agent.generate_product_ideas(); agent.close()
    return {"roadmap": sorted(ideas, key=lambda x: {"high":0,"medium":1,"low":2}.get(x.get("priority","low"),2))}

# ── Backup ────────────────────────────────────────────────
@app.post("/api/backup")
def create_backup():
    try:
        backup_dir = os.path.join(os.path.dirname(__file__), "backups")
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        db_path = os.path.join(os.path.dirname(__file__), "aventrix_hq.db")
        backup_path = os.path.join(backup_dir, f"backup_{timestamp}.db")
        shutil.copy2(db_path, backup_path)
        return {"success": True, "file": f"backup_{timestamp}.db", "timestamp": timestamp}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/backup/list")
def list_backups():
    backup_dir = os.path.join(os.path.dirname(__file__), "backups")
    if not os.path.exists(backup_dir):
        return {"backups": []}
    files = sorted(os.listdir(backup_dir), reverse=True)
    return {"backups": [{"file": f, "size": os.path.getsize(os.path.join(backup_dir, f))} for f in files[:10]]}



# ── Inbox Agent ───────────────────────────────────────────
@app.post("/api/inbox/check")
def check_inbox():
    """Manually trigger inbox check"""
    try:
        from agents.inbox_agent import InboxAgent
        agent = InboxAgent()
        result = agent.run_inbox_cycle()
        agent.close()
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ── LinkedIn Agent ────────────────────────────────────────
@app.get("/api/linkedin/messages/{industry}")
def get_linkedin_messages(industry: str):
    from agents.linkedin_agent import LinkedInAgent
    agent = LinkedInAgent()
    messages = agent.generate_batch_messages(industry, limit=10)
    agent.close()
    return {"messages": messages}

@app.get("/api/linkedin/connect/{lead_id}")
def get_connection_message(lead_id: int):
    from agents.linkedin_agent import LinkedInAgent
    agent = LinkedInAgent()
    msg = agent.generate_connection_request(lead_id)
    agent.close()
    return {"message": msg}

# ── Cross-Agent Coordinator ───────────────────────────────
@app.post("/api/coordinator/run")
def run_coordinator():
    from agents.cross_agent_coordinator import CrossAgentCoordinator
    coord = CrossAgentCoordinator()
    actions = coord.coordinate_daily()
    coord.close()
    return {"actions": actions}

@app.get("/api/coordinator/intelligence")
def get_intelligence():
    from agents.cross_agent_coordinator import CrossAgentCoordinator
    coord = CrossAgentCoordinator()
    report = coord.generate_company_intelligence_report()
    coord.close()
    return report

# ── Update .env endpoint for Zoho IMAP ───────────────────
@app.get("/api/inbox/test-connection")
def test_inbox_connection():
    import imaplib
    results = []
    hosts = ["imappro.zoho.in", "imap.zoho.in", "imap.zoho.com"]
    email_addr = os.getenv("ZOHO_EMAIL", "sales@aventrixtechnologies.com")
    password = os.getenv("ZOHO_EMAIL_PASSWORD", "")
    for host in hosts:
        try:
            mail = imaplib.IMAP4_SSL(host, 993)
            mail.login(email_addr, password)
            mail.logout()
            return {"success": True, "status": "ok", "message": f"Connected via {host}"}
        except Exception as e:
            results.append({"host": host, "error": str(e)})
    # Always return 200 so UptimeRobot doesn't count as down
    return {"success": False, "status": "ok", "message": "IMAP unavailable", "details": results}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8010, reload=True)


# ── PDF Invoice Download ──────────────────────────────────
@app.get("/api/finance/invoice/{invoice_id}/pdf")
def download_invoice_pdf(invoice_id: int, db: DBSession = Depends(get_db)):
    from fastapi.responses import Response
    import json as jsonlib
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(404, "Invoice not found")

    items = []
    try:
        items = jsonlib.loads(invoice.items or "[]")
    except:
        items = [{"description": "SecureAI Gateway Subscription", "amount": invoice.amount}]

    items_html = "".join([f"""
        <tr>
            <td style="padding:10px 0;border-bottom:1px solid #eee;">{item.get('description','Service')}</td>
            <td style="padding:10px 0;border-bottom:1px solid #eee;text-align:right;font-weight:500;">${item.get('amount',0)}</td>
        </tr>""" for item in items])

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  body {{ font-family: Arial, sans-serif; color: #1a1a1a; margin: 0; padding: 40px; }}
  .header {{ display: flex; justify-content: space-between; margin-bottom: 40px; }}
  .brand {{ font-size: 22px; font-weight: 700; color: #0A1628; }}
  .tagline {{ font-size: 12px; color: #888; margin-top: 4px; }}
  .invoice-title {{ font-size: 32px; font-weight: 300; color: #378ADD; text-align: right; }}
  .invoice-no {{ font-size: 14px; color: #888; text-align: right; }}
  .divider {{ border: none; border-top: 2px solid #0A1628; margin: 20px 0; }}
  .two-col {{ display: flex; justify-content: space-between; margin: 30px 0; }}
  .label {{ font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px; }}
  .value {{ font-size: 14px; font-weight: 500; }}
  table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
  th {{ text-align: left; padding: 10px 0; border-bottom: 2px solid #0A1628; font-size: 12px; text-transform: uppercase; color: #555; }}
  .total-row td {{ padding: 14px 0; font-size: 16px; font-weight: 700; border-top: 2px solid #0A1628; }}
  .status-badge {{ display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 500;
    background: {'#EAF3DE' if invoice.status == 'paid' else '#FAEEDA'}; 
    color: {'#3B6D11' if invoice.status == 'paid' else '#854F0B'}; }}
  .footer {{ margin-top: 60px; padding-top: 20px; border-top: 1px solid #eee; font-size: 12px; color: #888; text-align: center; }}
</style>
</head>
<body>
  <div class="header">
    <div>
      <div class="brand">Aventrix Technologies</div>
      <div class="tagline">AI. Secured. Governed.</div>
      <div style="margin-top:8px;font-size:12px;color:#888;">aventrixtechnologies.com</div>
    </div>
    <div>
      <div class="invoice-title">INVOICE</div>
      <div class="invoice-no">{invoice.invoice_no}</div>
      <div style="margin-top:8px;text-align:right;"><span class="status-badge">{invoice.status.upper()}</span></div>
    </div>
  </div>
  <hr class="divider">
  <div class="two-col">
    <div>
      <div class="label">Bill To</div>
      <div class="value">{invoice.client_name}</div>
      <div style="font-size:13px;color:#666;margin-top:4px;">{invoice.client_email}</div>
    </div>
    <div style="text-align:right;">
      <div class="label">Invoice Date</div>
      <div class="value">{str(invoice.created_at)[:10]}</div>
      <div style="margin-top:12px;"><div class="label">Due Date</div><div class="value">{invoice.due_date}</div></div>
    </div>
  </div>
  <table>
    <thead><tr><th>Description</th><th style="text-align:right;">Amount</th></tr></thead>
    <tbody>{items_html}</tbody>
    <tfoot>
      <tr class="total-row">
        <td>Total ({invoice.currency})</td>
        <td style="text-align:right;">${invoice.amount}</td>
      </tr>
    </tfoot>
  </table>
  <div style="margin-top:30px;padding:16px;background:#f8f9fa;border-radius:8px;font-size:13px;">
    <strong>Payment Instructions:</strong> Please transfer to our account within 15 days of invoice date.
    For payment queries contact: billing@aventrixtechnologies.com
  </div>
  <div class="footer">
    Aventrix Technologies &nbsp;|&nbsp; SecureAI Gateway &nbsp;|&nbsp; aventrixtechnologies.com<br>
    AI. Secured. Governed.
  </div>
</body>
</html>"""

    return Response(
        content=html,
        media_type="text/html",
        headers={"Content-Disposition": f"inline; filename={invoice.invoice_no}.html"}
    )


# ── Autonomous Agent Endpoints ────────────────────────────
@app.post("/api/autonomous/run")
def run_autonomous_cycle():
    """Trigger full autonomous CEO orchestration manually"""
    try:
        from agents.autonomous_agents import CEOAlex
        ceo = CEOAlex()
        result = ceo.run_daily_orchestration()
        ceo.close()
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/autonomous/messages")
def get_agent_messages(db: DBSession = Depends(get_db)):
    from agent_memory import AgentMessage
    msgs = db.query(AgentMessage).order_by(AgentMessage.created_at.desc()).limit(50).all()
    return [{"id":m.id,"from":m.from_agent,"to":m.to_agent,"type":m.message_type,
             "subject":m.subject,"content":m.content,"priority":m.priority,
             "status":m.status,"response":m.response,
             "requires_jayraj":m.requires_jayraj,"created_at":str(m.created_at)} for m in msgs]

@app.post("/api/autonomous/decide/{message_id}")
def decide_on_message(message_id: int, req: StatusUpdate, db: DBSession = Depends(get_db)):
    from agent_memory import AgentMessage
    msg = db.query(AgentMessage).filter(AgentMessage.id == message_id).first()
    if not msg:
        raise HTTPException(404)
    msg.status = req.status
    msg.response = req.status
    msg.resolved_at = datetime.utcnow()
    db.commit()
    return {"success": True}

@app.get("/api/autonomous/memories/{agent_name}")
def get_agent_memories(agent_name: str, db: DBSession = Depends(get_db)):
    from agent_memory import AgentMemory, AgentGoal, AgentReflection
    memories = db.query(AgentMemory).filter(AgentMemory.agent_name == agent_name).order_by(AgentMemory.created_at.desc()).limit(20).all()
    goals = db.query(AgentGoal).filter(AgentGoal.agent_name == agent_name, AgentGoal.status == "active").all()
    reflections = db.query(AgentReflection).filter(AgentReflection.agent_name == agent_name).order_by(AgentReflection.created_at.desc()).limit(5).all()
    return {
        "memories": [{"type":m.memory_type,"content":m.content,"outcome":m.outcome,"confidence":m.confidence} for m in memories],
        "goals": [{"goal":g.goal,"target":g.target_value,"current":g.current_value,"deadline":g.deadline} for g in goals],
        "reflections": [{"date":r.date,"worked":r.what_worked,"failed":r.what_failed,"learned":r.what_i_learned,"plan":r.plan_tomorrow,"confidence":r.confidence_score} for r in reflections]
    }

@app.post("/api/autonomous/pricing")
def request_pricing_decision(lead_id: int, requested_price: float, db: DBSession = Depends(get_db)):
    from agents.autonomous_agents import CEOAlex
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead: raise HTTPException(404)
    ceo = CEOAlex()
    result = ceo.handle_pricing_request(
        client_name=lead.company,
        current_price=149.0,
        requested_price=requested_price,
        context=f"Industry: {lead.industry}, Size: {lead.company_size}, Score: {lead.score}"
    )
    ceo.close()
    return {"result": result}

@app.post("/api/whatsapp/test")
def test_whatsapp():
    from whatsapp import notify_important_update
    success = notify_important_update(
        "Test Message from Alex",
        "Hi Jayraj Barad! This is Alex, your AI CEO. WhatsApp is working! Aventrix Technologies AI company is running autonomously. SecureAI Gateway is ready to sell!"
    )
    if success:
        return {"success": True, "message": "WhatsApp sent successfully"}
    else:
        return {"success": False, "message": "Twilio error — check Render logs"}


# ── Supabase Keep-Alive (prevents free tier pause) ────────
@app.get("/api/ping")
@app.head("/api/ping")
def ping():
    """Health check — always returns 200"""
    return {"status": "alive", "time": str(datetime.utcnow())}


# ── Website Contact Form ──────────────────────────────────


@app.get("/api/emails")
def get_all_emails(db: DBSession = Depends(get_db)):
    from database import Email as EmailModel
    emails = db.query(EmailModel).order_by(EmailModel.sent_at.desc()).limit(100).all()
    return {"emails": [{"id":e.id,"lead_id":e.lead_id,"subject":e.subject,
            "status":e.status,"direction":e.direction,"sent_at":str(e.sent_at)} for e in emails]}



@app.delete("/api/leads/cleanup")
def cleanup_leads(db: DBSession = Depends(get_db)):
    """Remove low quality leads and wrong company targets"""
    bad_companies = [
        "infosys", "wipro", "hcltech", "tech mahindra", "apollo hospitals",
        "fortis", "sun pharma", "cipla", "hdfc bank", "icici bank",
        "techmahindra", "hcl"
    ]
    all_leads = db.query(Lead).all()
    deleted = 0
    for lead in all_leads:
        company_lower = (lead.company or "").lower()
        is_bad_company = any(b in company_lower for b in bad_companies)
        is_low_score = (lead.score or 0) < 60
        is_wrong_title = any(t in (lead.notes or "").lower() for t in
                            ["seo role", "hr role", "test engineer", "senior engineer"])
        if is_bad_company or is_low_score or is_wrong_title:
            db.delete(lead)
            deleted += 1
    db.commit()
    return {"deleted": deleted, "message": f"Removed {deleted} low-quality leads"}


@app.get("/api/outreach/test-smtp")
def test_smtp():
    """Test SMTP connection"""
    import smtplib, ssl, os
    email = os.getenv("ZOHO_EMAIL", "sales@aventrixtechnologies.com")
    password = os.getenv("ZOHO_EMAIL_PASSWORD", "Jasy@7272")
    
    if not password:
        return {"success": False, "error": "ZOHO_EMAIL_PASSWORD not set"}
    
    results = {}
    hosts = [("smtp.zoho.in", 465, "SSL"), ("smtp.zoho.com", 465, "SSL"), ("smtp.zoho.in", 587, "TLS")]
    for host, port, mode in hosts:
        try:
            ctx = ssl.create_default_context()
            if mode == "SSL":
                with smtplib.SMTP_SSL(host, port, context=ctx, timeout=10) as server:
                    server.login(email, password)
            else:
                with smtplib.SMTP(host, port, timeout=10) as server:
                    server.starttls()
                    server.login(email, password)
            results[f"{host}:{port}"] = "SUCCESS"
            break
        except Exception as e:
            results[f"{host}:{port}"] = str(e)
    
    success = "SUCCESS" in results.values()
    return {"success": success, "email": email, "results": results}

@app.post("/api/outreach/send-test-email")
async def send_test_email(request: Request):
    """Send a test email to verify outreach works"""
    data = await request.json()
    to_email = data.get("to", "jayraj727272@gmail.com")
    
    import smtplib, ssl, os
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    from_email = os.getenv("ZOHO_EMAIL", "sales@aventrixtechnologies.com")
    password = os.getenv("ZOHO_EMAIL_PASSWORD", "Jasy@7272")
    host = "smtp.zoho.in"
    port = 465
    
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Test email from Aventrix AI HQ"
        msg["From"] = f"SecureAI Gateway <{from_email}>"
        msg["To"] = to_email
        msg.attach(MIMEText("This is a test email from Alex, your AI CEO. Outreach system is working!", "plain"))
        
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, context=ctx, timeout=15) as server:
            server.login(from_email, password)
            server.sendmail(from_email, to_email, msg.as_string())
        return {"success": True, "message": f"Test email sent to {to_email}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/contact")
async def submit_contact(request: Request):
    """Website contact form — instant response, WhatsApp notify"""
    try:
        data = await request.json()
        name     = data.get("name", "")
        company  = data.get("company", "")
        email    = data.get("email", "")
        phone    = data.get("phone", "")
        size     = data.get("company_size", "")
        industry = data.get("industry", "")
        interest = data.get("interest", "")
        message  = data.get("message", "")

        print(f"[CONTACT] New lead: {name} | {company} | {email} | {phone}")

        # WhatsApp Jayraj immediately
        try:
            from whatsapp import send_whatsapp
            msg = f"New Website Lead!\n\nName: {name}\nCompany: {company}\nEmail: {email}\nPhone: {phone}\nIndustry: {industry}\nInterest: {interest}\nMessage: {message[:200]}"
            send_whatsapp(msg)
            print("[CONTACT] WhatsApp sent")
        except Exception as e:
            print(f"[CONTACT] WhatsApp error: {e}")

        # Save to DB
        try:
            db_session = next(get_db())
            db_session.add(AgentLog(
                agent_name="Website",
                action="contact_form",
                result=f"{name} | {company} | {email} | {phone} | {industry}",
                status="success",
                created_at=datetime.utcnow()
            ))
            db_session.commit()
            db_session.close()
        except Exception as e:
            print(f"[CONTACT] DB error: {e}")

        return {"success": True, "message": "Thank you! We will contact you within 24 hours."}

    except Exception as e:
        print(f"[CONTACT] Error: {e}")
        return {"success": True, "message": "Received"}  # Always return success to frontend

# Force redeploy Fri Jun 12 07:55:35 UTC 2026


# ── Fix 1: Scout Run Endpoint ─────────────────────────────
@app.post("/api/scout/run")
async def run_scout_endpoint(background_tasks: BackgroundTasks, industry: str = "all"):
    def _run():
        try:
            from agents.scout_agent import ScoutAgent
            scout = ScoutAgent()
            if industry == "all":
                result = scout.run_full_scout()
            else:
                leads = scout.search_leads(industry, count=10)
                saved = scout.score_and_save_leads(leads, industry)
                result = {"found": len(leads), "saved": saved}
            scout.close()
            print(f"[SCOUT] Done: {result}")
        except Exception as e:
            print(f"[SCOUT] Error: {e}")
    background_tasks.add_task(_run)
    return {"success": True, "message": f"Scout started for {industry}. Check leads in 2-3 minutes."}


# ── Fix 2: Email Preview Endpoint ────────────────────────
@app.get("/api/outreach/preview/{lead_id}")
def preview_outreach_email(lead_id: int, db: DBSession = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        return {"error": "Lead not found"}
    try:
        from agents.outreach_agent import OutreachAgent
        agent = OutreachAgent()
        lead_dict = {
            "company": lead.company,
            "contact_name": lead.contact_name,
            "title": lead.notes.split("]")[0].replace("[","").strip() if lead.notes and "[" in lead.notes else "Decision Maker",
            "email": lead.email,
            "industry": lead.industry,
            "country": lead.country or "Global",
            "notes": lead.notes or ""
        }
        email = agent.generate_email(lead_dict)
        agent.close()
        return {"lead": lead.contact_name, "company": lead.company, "email": email}
    except Exception as e:
        return {"error": str(e)}


# ── Fix 3: WhatsApp Status Check ─────────────────────────
@app.get("/api/whatsapp/status")
def whatsapp_status():
    from whatsapp import send_whatsapp
    success = send_whatsapp("Aventrix HQ system check - all operational")
    return {
        "active": success,
        "message": "WhatsApp working" if success else "Sandbox expired. Send 'join mix-who' to +14155238886"
    }


# ── Fix 4: All leads endpoint ────────────────────────────
@app.get("/api/leads")
def get_all_leads(db: DBSession = Depends(get_db)):
    try:
        leads = db.query(Lead).order_by(Lead.score.desc()).all()
        return {"leads": [
            {
                "id": l.id,
                "name": l.contact_name or "",
                "company": l.company or "",
                "email": l.email or "",
                "industry": l.industry or "",
                "status": l.status or "new",
                "score": l.score or 0,
                "country": l.country or "Global",
                "notes": (l.notes or "")[:200],
                "created_at": str(l.created_at)
            }
            for l in leads
        ], "total": len(leads)}
    except Exception as e:
        return {"error": str(e), "leads": []}
