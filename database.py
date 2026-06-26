import os
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# PostgreSQL — Supabase
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise Exception("DATABASE_URL not set in .env")

# Fix for SQLAlchemy + Supabase
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={"sslmode": "require"}
)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Lead(Base):
    __tablename__ = "leads"
    id           = Column(Integer, primary_key=True, index=True)
    company      = Column(String(200))
    contact_name = Column(String(200))
    email        = Column(String(200))
    industry     = Column(String(100))
    company_size = Column(String(50))
    country      = Column(String(100))
    source       = Column(String(100))
    score        = Column(Integer, default=0)
    status       = Column(String(50), default="new")
    notes        = Column(Text)
    website      = Column(String(200))
    linkedin     = Column(String(200))
    phone        = Column(String(50))
    created_at   = Column(DateTime, default=datetime.utcnow)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class LeadNote(Base):
    __tablename__ = "lead_notes"
    id         = Column(Integer, primary_key=True)
    lead_id    = Column(Integer)
    note       = Column(Text)
    created_by = Column(String(100), default="Jayraj Barad")
    created_at = Column(DateTime, default=datetime.utcnow)

class LeadActivity(Base):
    __tablename__ = "lead_activities"
    id          = Column(Integer, primary_key=True)
    lead_id     = Column(Integer)
    activity    = Column(String(200))
    description = Column(Text)
    created_at  = Column(DateTime, default=datetime.utcnow)

class Email(Base):
    __tablename__ = "emails"
    id           = Column(Integer, primary_key=True, index=True)
    lead_id      = Column(Integer)
    subject      = Column(String(300))
    body         = Column(Text)
    direction    = Column(String(20), default="outbound")
    status       = Column(String(50), default="pending")
    opened       = Column(Boolean, default=False)
    opened_at    = Column(DateTime)
    sent_at      = Column(DateTime)
    sequence_day = Column(Integer, default=1)
    created_at   = Column(DateTime, default=datetime.utcnow)

class FollowUp(Base):
    __tablename__ = "followups"
    id           = Column(Integer, primary_key=True)
    lead_id      = Column(Integer)
    scheduled_at = Column(DateTime)
    day_number   = Column(Integer)
    status       = Column(String(50), default="pending")
    created_at   = Column(DateTime, default=datetime.utcnow)

class AgentLog(Base):
    __tablename__ = "agent_logs"
    id         = Column(Integer, primary_key=True, index=True)
    agent_name = Column(String(100))
    action     = Column(String(200))
    result     = Column(Text)
    status     = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)

class BlogPost(Base):
    __tablename__ = "blog_posts"
    id         = Column(Integer, primary_key=True, index=True)
    title      = Column(String(300))
    content    = Column(Text)
    keywords   = Column(String(300))
    meta_description = Column(String(320), default="")
    status     = Column(String(50), default="draft")
    created_at = Column(DateTime, default=datetime.utcnow)

class Invoice(Base):
    __tablename__ = "invoices"
    id           = Column(Integer, primary_key=True)
    invoice_no   = Column(String(50))
    client_name  = Column(String(200))
    client_email = Column(String(200))
    amount       = Column(Float)
    currency     = Column(String(10), default="USD")
    status       = Column(String(50), default="draft")
    due_date     = Column(String(20))
    items        = Column(Text)
    created_at   = Column(DateTime, default=datetime.utcnow)

class Expense(Base):
    __tablename__ = "expenses"
    id         = Column(Integer, primary_key=True)
    name       = Column(String(200))
    amount     = Column(Float)
    currency   = Column(String(10), default="USD")
    category   = Column(String(100))
    date       = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)

class DailyReport(Base):
    __tablename__ = "daily_reports"
    id           = Column(Integer, primary_key=True, index=True)
    date         = Column(String(20))
    briefing     = Column(Text)
    priorities   = Column(Text)
    leads_found  = Column(Integer, default=0)
    emails_sent  = Column(Integer, default=0)
    demos_booked = Column(Integer, default=0)
    created_at   = Column(DateTime, default=datetime.utcnow)

class Metric(Base):
    __tablename__ = "metrics"
    id             = Column(Integer, primary_key=True, index=True)
    total_leads    = Column(Integer, default=0)
    emails_sent    = Column(Integer, default=0)
    demos_booked   = Column(Integer, default=0)
    pipeline_value = Column(Float, default=0.0)
    mrr            = Column(Float, default=0.0)
    updated_at     = Column(DateTime, default=datetime.utcnow)

class User(Base):
    __tablename__ = "users"
    id         = Column(Integer, primary_key=True)
    username   = Column(String(100), unique=True)
    password   = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)

class Session(Base):
    __tablename__ = "sessions"
    id         = Column(Integer, primary_key=True)
    token      = Column(String(200), unique=True)
    username   = Column(String(100))
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

class SocialPost(Base):
    __tablename__ = "social_posts"
    id           = Column(Integer, primary_key=True)
    platform     = Column(String(50))
    content      = Column(Text)
    hashtags     = Column(String(300))
    scheduled_at = Column(String(50))
    status       = Column(String(50), default="draft")
    created_at   = Column(DateTime, default=datetime.utcnow)

class Competitor(Base):
    __tablename__ = "competitors"
    id         = Column(Integer, primary_key=True)
    name       = Column(String(200))
    features   = Column(Text)
    pricing    = Column(Text)
    weakness   = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow)

def init_db():
    try:
        from agent_memory import AgentMemory, AgentGoal, AgentMessage, AgentReflection
    except: pass
    Base.metadata.create_all(bind=engine)
    # Safe migration: add meta_description to blog_posts if it doesn't exist yet
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE blog_posts ADD COLUMN IF NOT EXISTS meta_description VARCHAR(320) DEFAULT ''"))
            conn.commit()
    except Exception as e:
        print(f"[init_db] meta_description migration skipped: {e}")
    db = SessionLocal()
    if not db.query(Metric).first():
        db.add(Metric())
        db.commit()
    if not db.query(User).first():
        import hashlib, os
        pwd = hashlib.sha256(os.getenv("ADMIN_PASSWORD","aventrix2024").encode()).hexdigest()
        db.add(User(username="admin", password=pwd))
        db.commit()
    db.close()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
