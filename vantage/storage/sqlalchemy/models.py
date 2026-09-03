from datetime import date, datetime
from typing import Optional
import sqlalchemy as sa
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class ProjectModel(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(sa.String, primary_key=True)
    display_name: Mapped[str] = mapped_column(sa.String, nullable=False)
    project_type: Mapped[str] = mapped_column(sa.String, nullable=False)
    owner_team: Mapped[str] = mapped_column(sa.String, nullable=False)
    owner_email: Mapped[str] = mapped_column(sa.String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(sa.Text)
    log_prompts: Mapped[bool] = mapped_column(sa.Boolean, default=False)
    active: Mapped[bool] = mapped_column(sa.Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=datetime.utcnow)

    source_mappings: Mapped[list["ProjectSourceMappingModel"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class ProjectSourceMappingModel(Base):
    __tablename__ = "project_source_mappings"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(
        sa.String, sa.ForeignKey("projects.id"), nullable=False
    )
    source_tool: Mapped[str] = mapped_column(sa.String, nullable=False)
    source_identifier: Mapped[str] = mapped_column(sa.String, nullable=False)
    display_label: Mapped[Optional[str]] = mapped_column(sa.String)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=datetime.utcnow)

    project: Mapped["ProjectModel"] = relationship(back_populates="source_mappings")

    __table_args__ = (
        sa.UniqueConstraint("source_tool", "source_identifier", name="uq_source_mapping"),
    )


class ExperimentModel(Base):
    __tablename__ = "experiments"

    id: Mapped[str] = mapped_column(sa.String, primary_key=True)
    title: Mapped[str] = mapped_column(sa.String, nullable=False)
    slug: Mapped[str] = mapped_column(sa.String, unique=True, nullable=False)
    project_id: Mapped[Optional[str]] = mapped_column(
        sa.String, sa.ForeignKey("projects.id")
    )
    status: Mapped[str] = mapped_column(sa.String, default="planned")

    hypothesis: Mapped[str] = mapped_column(sa.Text, nullable=False)
    objective: Mapped[str] = mapped_column(sa.Text, nullable=False)
    owner_name: Mapped[str] = mapped_column(sa.String, nullable=False)
    owner_team: Mapped[str] = mapped_column(sa.String, nullable=False)
    owner_email: Mapped[str] = mapped_column(sa.String, nullable=False)
    start_date: Mapped[date] = mapped_column(sa.Date, nullable=False)
    expected_end: Mapped[date] = mapped_column(sa.Date, nullable=False)

    dataset_description: Mapped[Optional[str]] = mapped_column(sa.Text)
    baseline_description: Mapped[Optional[str]] = mapped_column(sa.Text)
    model_configurations: Mapped[Optional[str]] = mapped_column(sa.Text)

    actual_end: Mapped[Optional[date]] = mapped_column(sa.Date)
    outcome: Mapped[Optional[str]] = mapped_column(sa.String)
    result_summary: Mapped[Optional[str]] = mapped_column(sa.Text)
    metrics_json: Mapped[Optional[str]] = mapped_column(sa.Text)
    learnings: Mapped[Optional[str]] = mapped_column(sa.Text)
    recommendations: Mapped[Optional[str]] = mapped_column(sa.Text)
    artefacts_json: Mapped[Optional[str]] = mapped_column(sa.Text)

    tags_json: Mapped[Optional[str]] = mapped_column(sa.Text)

    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class AlertRuleModel(Base):
    __tablename__ = "alert_rules"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(sa.String, nullable=False)
    detector_type: Mapped[str] = mapped_column(sa.String, nullable=False)
    metric_name: Mapped[str] = mapped_column(sa.String, nullable=False)
    warn_z: Mapped[float] = mapped_column(sa.Float, default=2.0)
    crit_z: Mapped[float] = mapped_column(sa.Float, default=3.0)
    absolute_threshold: Mapped[Optional[float]] = mapped_column(sa.Float)
    rate_change_factor: Mapped[float] = mapped_column(sa.Float, default=1.5)
    error_rate_pct: Mapped[float] = mapped_column(sa.Float, default=5.0)
    enabled: Mapped[bool] = mapped_column(sa.Boolean, default=True)

    __table_args__ = (
        sa.UniqueConstraint(
            "project_id", "detector_type", "metric_name", name="uq_alert_rule_signal"
        ),
    )


class AlertRecordModel(Base):
    __tablename__ = "alert_records"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, autoincrement=True)
    alert_uuid: Mapped[str] = mapped_column(sa.String, unique=True, nullable=False)
    project_id: Mapped[str] = mapped_column(sa.String, nullable=False)
    detector_type: Mapped[str] = mapped_column(sa.String, nullable=False)
    metric_name: Mapped[str] = mapped_column(sa.String, nullable=False)
    severity: Mapped[str] = mapped_column(sa.String, nullable=False)
    message: Mapped[str] = mapped_column(sa.Text, nullable=False)
    current_value: Mapped[float] = mapped_column(sa.Float, nullable=False)
    baseline_value: Mapped[Optional[float]] = mapped_column(sa.Float)
    fired_at: Mapped[datetime] = mapped_column(sa.DateTime, nullable=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime)
    notified: Mapped[bool] = mapped_column(sa.Boolean, default=False)

    category: Mapped[str] = mapped_column(sa.String, default="observability")
    security_incident_key: Mapped[Optional[str]] = mapped_column(sa.String)
    trace_id: Mapped[Optional[str]] = mapped_column(sa.String)
    span_id: Mapped[Optional[str]] = mapped_column(sa.String)
    threat_types_json: Mapped[Optional[str]] = mapped_column(sa.Text)

    __table_args__ = (
        sa.UniqueConstraint("category", "security_incident_key", name="uq_security_incident_key"),
    )


class AlertSuppressionRuleModel(Base):
    __tablename__ = "alert_suppression_rules"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, autoincrement=True)
    rule_id: Mapped[str] = mapped_column(sa.String, unique=True, nullable=False)
    project_id: Mapped[str] = mapped_column(sa.String, nullable=False)
    detector_type: Mapped[str] = mapped_column(sa.String, nullable=False)
    incident_key: Mapped[str] = mapped_column(sa.String, nullable=False)
    pattern_text: Mapped[Optional[str]] = mapped_column(sa.Text)
    expires_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime)
    scope: Mapped[str] = mapped_column(sa.String, default="project")
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=datetime.utcnow)

    __table_args__ = (
        sa.UniqueConstraint("project_id", "incident_key", name="uq_suppression_rule"),
    )


class LocalCacheRecordModel(Base):
    __tablename__ = "local_cache_records"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, autoincrement=True)
    cache_id: Mapped[str] = mapped_column(sa.String, unique=True, nullable=False)
    project_id: Mapped[str] = mapped_column(sa.String, nullable=False)
    model_name: Mapped[str] = mapped_column(sa.String, nullable=False)
    exact_hash: Mapped[str] = mapped_column(sa.String, nullable=False, index=True)
    prompt_template_version: Mapped[str] = mapped_column(sa.String, default="v1")
    context_fingerprint: Mapped[str] = mapped_column(sa.String, default="")
    # prompt_text / response_text nullable — not stored when log_prompts=False
    prompt_text: Mapped[Optional[str]] = mapped_column(sa.Text)
    response_text: Mapped[Optional[str]] = mapped_column(sa.Text)
    tokens_input: Mapped[int] = mapped_column(sa.Integer, default=0)
    tokens_output: Mapped[int] = mapped_column(sa.Integer, default=0)
    original_cost_usd: Mapped[float] = mapped_column(sa.Float, default=0.0)
    hit_count: Mapped[int] = mapped_column(sa.Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=datetime.utcnow)
    last_hit_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime)
    expires_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime)


class ProjectPolicyModel(Base):
    __tablename__ = "project_policies"

    project_id: Mapped[str] = mapped_column(sa.String, primary_key=True)
    max_cost_per_trace_usd: Mapped[float] = mapped_column(sa.Float, default=0.50)
    max_tokens_per_trace: Mapped[int] = mapped_column(sa.Integer, default=30000)
    max_retry_loops: Mapped[int] = mapped_column(sa.Integer, default=3)
    enabled: Mapped[bool] = mapped_column(sa.Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime, default=datetime.utcnow)


class ApiKeyModel(Base):
    __tablename__ = "api_keys"

    key_id: Mapped[str] = mapped_column(sa.String, primary_key=True)
    key_hash: Mapped[str] = mapped_column(sa.String, unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(sa.String, nullable=False)
    role: Mapped[str] = mapped_column(sa.String, nullable=False, default="developer")  # admin | developer | viewer
    project_id: Mapped[Optional[str]] = mapped_column(sa.String)  # Optional scope
    status: Mapped[str] = mapped_column(sa.String, default="active")  # active | revoked
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=datetime.utcnow)
    expires_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime)


class AuditLogModel(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(sa.DateTime, default=datetime.utcnow, index=True)
    actor_key_id: Mapped[str] = mapped_column(sa.String, nullable=False)
    project_id: Mapped[Optional[str]] = mapped_column(sa.String, index=True)
    action: Mapped[str] = mapped_column(sa.String, nullable=False)
    resource_type: Mapped[str] = mapped_column(sa.String, nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(sa.String)
    details_json: Mapped[Optional[str]] = mapped_column(sa.Text)
    previous_hash: Mapped[str] = mapped_column(sa.String, nullable=False)
    record_hash: Mapped[str] = mapped_column(sa.String, nullable=False)
