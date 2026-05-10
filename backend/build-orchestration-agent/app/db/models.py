"""
Database Models
----------------
SQLAlchemy ORM models for builds, logs, and HITL approval history.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float
from datetime import datetime

from app.db.database import Base


class Build(Base):
    __tablename__ = "builds"

    id = Column(String, primary_key=True)
    project_path = Column(String)
    github_url = Column(String, nullable=True)
    project_type = Column(String, nullable=True)
    status = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class Log(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, index=True)
    build_id = Column(String, ForeignKey("builds.id"))
    message = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)


class ApprovalLog(Base):
    __tablename__ = "approval_logs"

    id = Column(Integer, primary_key=True, index=True)
    build_id = Column(String, ForeignKey("builds.id"))
    iteration = Column(Integer)
    error_type = Column(String, nullable=True)
    proposed_action = Column(String, nullable=True)
    proposed_command = Column(Text, nullable=True)
    decision = Column(String)  # approve, reject, modify, timeout
    modified_command = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    risk = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)