from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
import pytz

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scheduler")
scheduler = BackgroundScheduler()
ist = pytz.timezone("Asia/Kolkata")

def ceo_brain_cycle():
    """Full CEO brain cycle — runs at 8 AM IST (2:30 AM UTC)"""
    logger.info("CEO Brain: Starting full autonomous cycle...")
    try:
        from agents.ceo_brain import CEOBrain
        ceo = CEOBrain()
        result = ceo.run_full_brain_cycle()
        ceo.close()
        logger.info(f"CEO Brain complete. Escalated to Jayraj: {result.get('escalated_to_jayraj',0)}")
    except Exception as e:
        logger.error(f"CEO Brain error: {e}")
        # Fallback — send basic WhatsApp
        try:
            from whatsapp import notify_important_update
            notify_important_update("CEO Morning Update",
                f"Good morning Jayraj! Alex here. Running company operations. Will update you shortly.")
        except: pass

def twilio_reminder_job():
    """Every 60 hours remind Jayraj to rejoin Twilio sandbox"""
    try:
        from whatsapp import send_whatsapp
        send_whatsapp("Reminder: Twilio sandbox expires every 72 hours.\nSend: join mix-who\nTo: +14155238886 on WhatsApp to keep Alex connected.")
        logger.info("Twilio reminder sent")
    except Exception as e:
        logger.error(f"Twilio reminder error: {e}")

def lead_generation_job():
    logger.info("Scout: Finding global decision-maker leads...")
    try:
        from agents.scout_agent import ScoutAgent
        scout = ScoutAgent()
        result = scout.run_full_scout()
        scout.close()
        logger.info(f"Scout complete: {result.get('total_saved', 0)} leads saved")
    except Exception as e:
        logger.error(f"Scout error: {e}")

def outreach_job():
    logger.info("Outreach: Sending emails...")
    try:
        from agents.outreach_agent import OutreachAgent
        outreach = OutreachAgent()
        result = outreach.run_daily_outreach(limit=20)
        outreach.close()
        logger.info(f"Outreach done: {result}")
    except Exception as e:
        logger.error(f"Outreach error: {e}")

def qualification_job():
    logger.info("Qualifier: Scoring leads...")
    try:
        from agents.all_agents import QualifierAgent
        qualifier = QualifierAgent()
        qualifier.run_qualification()
        qualifier.close()
    except Exception as e:
        logger.error(f"Qualification error: {e}")

def followup_job():
    logger.info("Follow-up: Running sequences...")
    try:
        from agents.new_agents import FollowUpAgent
        agent = FollowUpAgent()
        agent.run_pending_followups()
        agent.close()
    except Exception as e:
        logger.error(f"Follow-up error: {e}")

def blog_writing_job():
    logger.info("Blog Writer: Writing post...")
    try:
        from agents.all_agents import BlogWriterAgent
        writer = BlogWriterAgent()
        writer.write_blog_post()
        writer.close()
    except Exception as e:
        logger.error(f"Blog error: {e}")

def sales_reflection_job():
    """Sales self-reflection — 6 PM IST"""
    logger.info("Sales: Self-reflecting...")
    try:
        from agents.autonomous_agents import AutonomousSalesManager
        mgr = AutonomousSalesManager()
        mgr.run_autonomous_cycle()
        mgr.close()
    except Exception as e:
        logger.error(f"Sales reflection error: {e}")

def keepalive_job():
    """Keep Supabase alive"""
    try:
        from database import SessionLocal
        from sqlalchemy import text
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        logger.info("Supabase keepalive OK")
    except Exception as e:
        logger.error(f"Keepalive error: {e}")

def inbox_check_job():
    """Read inbox every 30 min — auto-reply to leads"""
    logger.info("Inbox: Checking emails...")
    try:
        from agents.inbox_agent import InboxAgent
        agent = InboxAgent()
        result = agent.run_inbox_cycle()
        agent.close()
        logger.info(f"Inbox done: {result}")
    except Exception as e:
        logger.error(f"Inbox error: {e}")

def cross_agent_job():
    """Cross-agent coordination — agents share intelligence"""
    logger.info("Coordinator: Running cross-agent coordination...")
    try:
        from agents.cross_agent_coordinator import CrossAgentCoordinator
        coord = CrossAgentCoordinator()
        actions = coord.coordinate_daily()
        coord.close()
        logger.info(f"Coordination done: {len(actions)} actions")
    except Exception as e:
        logger.error(f"Coordinator error: {e}")

def start_scheduler():
    # CEO Full Brain — 8 AM IST = 2:30 AM UTC
    scheduler.add_job(ceo_brain_cycle, CronTrigger(hour=2, minute=30), id="ceo_brain")
    # Lead Generation — 9 AM IST = 3:30 AM UTC
    scheduler.add_job(lead_generation_job, CronTrigger(hour=3, minute=30), id="leads")
    # Outreach — 10 AM IST = 4:30 AM UTC
    scheduler.add_job(outreach_job, CronTrigger(hour=4, minute=30), id="outreach")
    # Qualification — 11 AM IST = 5:30 AM UTC
    scheduler.add_job(qualification_job, CronTrigger(hour=5, minute=30), id="qualify")
    # Follow-ups — 12 PM IST = 6:30 AM UTC
    scheduler.add_job(followup_job, CronTrigger(hour=6, minute=30), id="followup")
    # Sales Reflection — 6 PM IST = 12:30 PM UTC
    scheduler.add_job(sales_reflection_job, CronTrigger(hour=12, minute=30), id="reflection")
    # Blog — Mon & Thu 2 PM IST = 8:30 AM UTC
    scheduler.add_job(blog_writing_job, CronTrigger(day_of_week="mon,thu", hour=8, minute=30), id="blog")
    # Inbox check — every 30 minutes
    scheduler.add_job(inbox_check_job, "interval", minutes=30, id="inbox")
    # Cross-agent coordination — 7:30 AM IST (2 AM UTC) — before CEO briefing
    scheduler.add_job(cross_agent_job, CronTrigger(hour=2, minute=0), id="coordinator")
    # Supabase keepalive — every 5 days
    scheduler.add_job(twilio_reminder_job, 'interval', hours=60, id='twilio_reminder_job', timezone=ist)
    scheduler.add_job(keepalive_job, "interval", days=5, id="keepalive")

    scheduler.start()
    logger.info("✅ All agents scheduled on IST timezone")
    return scheduler
