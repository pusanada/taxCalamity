import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, JSON, Text
from sqlalchemy.orm import relationship
from backend.app.db.database import Base

class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=True)
    email = Column(String, unique=True, index=True, nullable=True)
    phone = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    profiles = relationship("FinancialProfile", back_populates="client")
    recommendations = relationship("Recommendation", back_populates="client")


class FinancialProfile(Base):
    __tablename__ = "financial_profiles"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    age = Column(Integer, nullable=False)
    monthly_income = Column(Float, nullable=False)
    bonus_months = Column(Integer, default=0)
    existing_rmf = Column(Float, default=0.0)
    existing_ssf = Column(Float, default=0.0)
    life_insurance = Column(Float, default=0.0)
    goal = Column(String, nullable=True)
    risk_profile = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    client = relationship("Client", back_populates="profiles")


class Fund(Base):
    __tablename__ = "funds"

    id = Column(Integer, primary_key=True, index=True)
    proj_id = Column(String, unique=True, index=True, nullable=True) # SEC Project ID (e.g. M0045_2565)
    name = Column(String, index=True, nullable=False)
    asset_class = Column(String, index=True, nullable=False) # e.g. Equity, Fixed Income
    risk_level = Column(Integer, nullable=False)            # 1 to 8
    tax_type = Column(String, index=True, nullable=False)     # SSF, RMF, ThaiESG, or General
    expense_ratio = Column(Float, nullable=False)           # Percentage
    aum = Column(Float, nullable=False)                     # Total Assets in THB
    objective = Column(Text, nullable=True)


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    recommended_funds = Column(JSON, nullable=False)       # JSON List of recommended fund details
    reasoning = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    client = relationship("Client", back_populates="recommendations")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True, nullable=False)
    agent_name = Column(String, index=True, nullable=False)
    action = Column(String, nullable=False)
    detail = Column(Text, nullable=True)
    is_compliant = Column(Boolean, default=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True, nullable=False)
    agent_role = Column(String, index=True, nullable=False)
    input_payload = Column(JSON, nullable=True)
    output_payload = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)


class WorkflowState(Base):
    __tablename__ = "workflow_states"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True, nullable=False)
    current_node = Column(String, nullable=False)
    state_data = Column(JSON, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class ComplianceFlag(Base):
    __tablename__ = "compliance_flags"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True, nullable=False)
    rule_name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String, default="WARNING") # WARNING or VIOLATION
    status = Column(String, default="FLAGGED")    # FLAGGED, IGNORED, RESOLVED
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class CrewExecution(Base):
    __tablename__ = "crew_executions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True, nullable=False)
    status = Column(String, nullable=False)       # PENDING, RUNNING, COMPLETED, FAILED
    run_by = Column(String, nullable=True)
    tokens_used = Column(Integer, default=0)
    cost = Column(Float, default=0.0)
    full_trace = Column(JSON, nullable=True)      # Detailed trace logs
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
