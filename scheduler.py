from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from agents.ceo_agent import CEOAgent
from agents.scout_agent import ScoutAgent
from agents.outreach_agent import OutreachAgent
from agents.all_agents import QualifierAgent, BlogWriterAgent, RnDAgent
from agents.new_agents import FollowUpAgent, SocialCalendarAgent
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scheduler")
scheduler = BackgroundScheduler()

def morning_briefing_job():
    logger.info("CEO: Morning briefing...")
    try:
        from agents.autonomous_agents import CEOAlex
        ceo = CEOAlex()
        result = ceo.run_daily_orchestration()
        ceo.close()
        logger.info(f"CEO orchestration done. Escalated to Jayraj: {result.get('escalated_to_jayraj',0)}")
    except Exception as e:
        logger.error(f"CEO orchestration error: {e}")
        # Fallback to basic briefing
        try:
            ceo = CEOAgent()
            ceo.generate_briefing()
            ceo.close()
        except: pass

def lead_generation_job():
    logger.info("Scout: Finding leads...")
    try:
        scout = ScoutAgent()
        for industry in ["IT", "Healthcare", "Finance", "R&D"]:
            scout.search_leads(industry, count=5)
        scout.close()
        logger.info("Lead generation done")
    except Exception as e:
        logger.error(f"Lead generation error: {e}")

def outreach_job():
    logger.info("Outreach: Sending emails...")
    try:
        outreach = OutreachAgent()
        result = outreach.run_daily_outreach(limit=20)
        outreach.close()
        logger.info(f"Outreach done: {result}")
    except Exception as e:
        logger.error(f"Outreach error: {e}")

def qualification_job():
    logger.info("Qualifier: Scoring leads...")
    try:
        qualifier = QualifierAgent()
        result = qualifier.run_qualification()
        qualifier.close()
        logger.info(f"Qualification done: {result}")
    except Exception as e:
        logger.error(f"Qualification error: {e}")

def followup_job():
    logger.info("Follow-up: Running sequences...")
    try:
        agent = FollowUpAgent()
        result = agent.run_pending_followups()
        agent.close()
        logger.info(f"Follow-ups done: {result}")
    except Exception as e:
        logger.error(f"Follow-up error: {e}")

def blog_writing_job():
    logger.info("Blog Writer: Writing post...")
    try:
        writer = BlogWriterAgent()
        writer.write_blog_post()
        writer.close()
        logger.info("Blog post written")
    except Exception as e:
        logger.error(f"Blog error: {e}")

def rnd_job():
    logger.info("R&D: Researching...")
    try:
        rnd = RnDAgent()
        rnd.research_competitors()
        rnd.close()
        logger.info("R&D done")
    except Exception as e:
        logger.error(f"R&D error: {e}")

def sales_reflection_job():
    logger.info("Sales Manager: Self-reflecting...")
    try:
        from agents.autonomous_agents import AutonomousSalesManager
        mgr = AutonomousSalesManager()
        mgr.run_autonomous_cycle()
        mgr.close()
    except Exception as e:
        logger.error(f"Sales reflection error: {e}")

def start_scheduler():
    # CEO orchestration — 8 AM daily (runs all departments + WhatsApps Jayraj)
    scheduler.add_job(morning_briefing_job, CronTrigger(hour=8, minute=0), id="ceo_orchestration")
    # Lead generation — 9 AM daily
    scheduler.add_job(lead_generation_job, CronTrigger(hour=9, minute=0), id="lead_generation")
    # Outreach — 10 AM daily
    scheduler.add_job(outreach_job, CronTrigger(hour=10, minute=0), id="outreach")
    # Qualification — 11 AM daily
    scheduler.add_job(qualification_job, CronTrigger(hour=11, minute=0), id="qualification")
    # Follow-ups — 12 PM daily
    scheduler.add_job(followup_job, CronTrigger(hour=12, minute=0), id="followups")
    # Sales reflection — 6 PM daily
    scheduler.add_job(sales_reflection_job, CronTrigger(hour=18, minute=0), id="sales_reflection")
    # Blog writing — Mon & Thu 2 PM
    scheduler.add_job(blog_writing_job, CronTrigger(day_of_week="mon,thu", hour=14, minute=0), id="blog")
    # R&D — Sunday 10 AM
    scheduler.add_job(rnd_job, CronTrigger(day_of_week="sun", hour=10, minute=0), id="rnd")

    # Supabase keep-alive — ping every 5 days to prevent pause
    scheduler.add_job(
        lambda: __import__('requests').get('https://aventrix-api.onrender.com/api/ping', timeout=10),
        'interval', days=5, id="supabase_keepalive"
    )
    scheduler.start()
    logger.info("✅ Scheduler started — all autonomous agents on schedule")
    return scheduler
