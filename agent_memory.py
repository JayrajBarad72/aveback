"""
Agent Memory System
Each agent stores learnings, strategies, outcomes in DB
Loads memory on startup to inform decisions
"""
import json
import os
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, DateTime
from database import Base, SessionLocal, engine, init_db

class AgentMemory(Base):
    __tablename__ = "agent_memories"
    id         = Column(Integer, primary_key=True)
    agent_name = Column(String(100))
    memory_type= Column(String(50))  # learning, strategy, outcome, goal
    content    = Column(Text)
    confidence = Column(Float, default=1.0)
    times_used = Column(Integer, default=0)
    outcome    = Column(String(50))  # success, failure, unknown
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class AgentGoal(Base):
    __tablename__ = "agent_goals"
    id          = Column(Integer, primary_key=True)
    agent_name  = Column(String(100))
    goal        = Column(Text)
    target_value= Column(Float)
    current_value=Column(Float, default=0)
    deadline    = Column(String(50))
    status      = Column(String(50), default="active")
    created_at  = Column(DateTime, default=datetime.utcnow)

class AgentMessage(Base):
    __tablename__ = "agent_messages"
    id          = Column(Integer, primary_key=True)
    from_agent  = Column(String(100))
    to_agent    = Column(String(100))
    message_type= Column(String(50))  # approval_request, decision, report, alert, question
    subject     = Column(String(300))
    content     = Column(Text)
    priority    = Column(String(20), default="normal")  # low, normal, high, urgent
    status      = Column(String(50), default="pending")  # pending, approved, rejected, answered
    response    = Column(Text)
    requires_jayraj = Column(Integer, default=0)
    created_at  = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime)

class AgentReflection(Base):
    __tablename__ = "agent_reflections"
    id           = Column(Integer, primary_key=True)
    agent_name   = Column(String(100))
    date         = Column(String(20))
    what_i_did   = Column(Text)
    what_worked  = Column(Text)
    what_failed  = Column(Text)
    what_i_learned = Column(Text)
    plan_tomorrow= Column(Text)
    confidence_score = Column(Float, default=0.7)
    created_at   = Column(DateTime, default=datetime.utcnow)

def init_memory_db():
    Base.metadata.create_all(bind=engine)

class MemoryManager:
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.db = SessionLocal()

    def remember(self, memory_type: str, content: str, outcome: str = "unknown", confidence: float = 1.0):
        memory = AgentMemory(
            agent_name=self.agent_name,
            memory_type=memory_type,
            content=content,
            outcome=outcome,
            confidence=confidence
        )
        self.db.add(memory)
        self.db.commit()

    def recall(self, memory_type: str = None, limit: int = 10) -> list:
        query = self.db.query(AgentMemory).filter(AgentMemory.agent_name == self.agent_name)
        if memory_type:
            query = query.filter(AgentMemory.memory_type == memory_type)
        memories = query.order_by(AgentMemory.updated_at.desc()).limit(limit).all()
        return [{"type": m.memory_type, "content": m.content, "outcome": m.outcome,
                 "confidence": m.confidence} for m in memories]

    def get_goals(self) -> list:
        goals = self.db.query(AgentGoal).filter(
            AgentGoal.agent_name == self.agent_name,
            AgentGoal.status == "active"
        ).all()
        return [{"goal": g.goal, "target": g.target_value,
                 "current": g.current_value, "deadline": g.deadline} for g in goals]

    def set_goal(self, goal: str, target: float, deadline: str):
        existing = self.db.query(AgentGoal).filter(
            AgentGoal.agent_name == self.agent_name,
            AgentGoal.goal == goal
        ).first()
        if existing:
            existing.target_value = target
            existing.deadline = deadline
        else:
            self.db.add(AgentGoal(agent_name=self.agent_name, goal=goal,
                                   target_value=target, deadline=deadline))
        self.db.commit()

    def update_goal_progress(self, goal_keyword: str, value: float):
        goal = self.db.query(AgentGoal).filter(
            AgentGoal.agent_name == self.agent_name,
            AgentGoal.goal.contains(goal_keyword)
        ).first()
        if goal:
            goal.current_value = value
            if value >= goal.target_value:
                goal.status = "achieved"
            self.db.commit()

    def send_message(self, to_agent: str, message_type: str, subject: str,
                     content: str, priority: str = "normal", requires_jayraj: bool = False) -> int:
        msg = AgentMessage(
            from_agent=self.agent_name,
            to_agent=to_agent,
            message_type=message_type,
            subject=subject,
            content=content,
            priority=priority,
            requires_jayraj=1 if requires_jayraj else 0
        )
        self.db.add(msg)
        self.db.commit()
        return msg.id

    def get_messages(self, status: str = "pending") -> list:
        msgs = self.db.query(AgentMessage).filter(
            AgentMessage.to_agent == self.agent_name,
            AgentMessage.status == status
        ).order_by(AgentMessage.created_at.desc()).all()
        return [{"id": m.id, "from": m.from_agent, "type": m.message_type,
                 "subject": m.subject, "content": m.content, "priority": m.priority,
                 "requires_jayraj": m.requires_jayraj, "created_at": str(m.created_at)} for m in msgs]

    def resolve_message(self, message_id: int, response: str, status: str = "approved"):
        msg = self.db.query(AgentMessage).filter(AgentMessage.id == message_id).first()
        if msg:
            msg.status = status
            msg.response = response
            msg.resolved_at = datetime.utcnow()
            self.db.commit()

    def save_reflection(self, date: str, what_did: str, worked: str,
                        failed: str, learned: str, plan: str, confidence: float):
        ref = AgentReflection(
            agent_name=self.agent_name, date=date,
            what_i_did=what_did, what_worked=worked,
            what_failed=failed, what_i_learned=learned,
            plan_tomorrow=plan, confidence_score=confidence
        )
        self.db.add(ref)
        self.db.commit()

    def get_last_reflection(self) -> dict:
        ref = self.db.query(AgentReflection).filter(
            AgentReflection.agent_name == self.agent_name
        ).order_by(AgentReflection.created_at.desc()).first()
        if not ref:
            return {}
        return {"date": ref.date, "what_worked": ref.what_worked,
                "what_failed": ref.what_failed, "learned": ref.what_i_learned,
                "plan": ref.plan_tomorrow, "confidence": ref.confidence_score}

    def close(self):
        self.db.close()
