"""
Database models and operations
"""

from datetime import datetime
from typing import Optional, List
from enum import Enum

from sqlalchemy import create_engine, Column, String, DateTime, Integer, JSON, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.pool import NullPool

from app.config import settings

# Create database engine
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=NullPool,  # No connection pooling for Cloud SQL
    echo=settings.DEBUG,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database models
class User(Base):
    __tablename__ = "users"
    
    id = Column(String(255), primary_key=True)
    email = Column(String(255), unique=True, index=True)
    name = Column(String(255))
    picture_url = Column(String(512), nullable=True)
    workspace_id = Column(String(255), index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    
    projects = relationship("ProjectAccess", back_populates="user")
    jobs = relationship("Job", back_populates="user")

class Project(Base):
    __tablename__ = "projects"
    
    id = Column(String(255), primary_key=True)
    name = Column(String(255), index=True)
    owner_id = Column(String(255), ForeignKey("users.id"))
    description = Column(String(1000), nullable=True)
    billing_tier = Column(String(50), default="free")  # free, pro, enterprise
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    connectors = relationship("Connector", back_populates="project")
    jobs = relationship("Job", back_populates="project")
    access = relationship("ProjectAccess", back_populates="project")

class ProjectAccess(Base):
    __tablename__ = "project_access"
    
    id = Column(String(255), primary_key=True)
    project_id = Column(String(255), ForeignKey("projects.id"), index=True)
    user_id = Column(String(255), ForeignKey("users.id"), index=True)
    role = Column(String(50), default="viewer")  # viewer, editor, admin
    created_at = Column(DateTime, default=datetime.utcnow)
    
    project = relationship("Project", back_populates="access")
    user = relationship("User", back_populates="projects")

class Connector(Base):
    __tablename__ = "connectors"
    
    id = Column(String(255), primary_key=True)
    project_id = Column(String(255), ForeignKey("projects.id"), index=True)
    name = Column(String(255))
    type = Column(String(50), index=True)  # bigquery, gcs, postgres, snowflake
    config = Column(JSON)  # Encrypted in production
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    project = relationship("Project", back_populates="connectors")

class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(String(255), primary_key=True)
    project_id = Column(String(255), ForeignKey("projects.id"), index=True)
    user_id = Column(String(255), ForeignKey("users.id"), index=True)
    question = Column(String(2000))
    status = Column(String(50), default="pending", index=True)  # pending, running, succeeded, failed
    plan_json = Column(JSON, nullable=True)
    result_json = Column(JSON, nullable=True)
    error_message = Column(String(1000), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    
    project = relationship("Project", back_populates="jobs")
    user = relationship("User", back_populates="jobs")
    artifacts = relationship("Artifact", back_populates="job")

class Artifact(Base):
    __tablename__ = "artifacts"
    
    id = Column(String(255), primary_key=True)
    job_id = Column(String(255), ForeignKey("jobs.id"), index=True)
    type = Column(String(50))  # csv, json, png, html, notebook
    gcs_path = Column(String(512), unique=True)
    size_bytes = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    job = relationship("Job", back_populates="artifacts")

class AccessLog(Base):
    __tablename__ = "access_logs"
    
    id = Column(String(255), primary_key=True)
    user_id = Column(String(255), index=True)
    action = Column(String(100))  # query_submitted, job_created, artifact_downloaded
    target = Column(String(255))  # resource being accessed
    ip_address = Column(String(45))
    user_agent = Column(String(512))
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

# Database operations
async def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
    print("Database tables initialized")

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_user_role(user_id: str, project_id: str) -> Optional[str]:
    """Get user's role in a project"""
    db = SessionLocal()
    try:
        access = db.query(ProjectAccess).filter(
            ProjectAccess.user_id == user_id,
            ProjectAccess.project_id == project_id,
        ).first()
        return access.role if access else None
    finally:
        db.close()
