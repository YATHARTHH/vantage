import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from vantage.domain.alerts import AlertRecord, AlertRule, AlertSeverity, DetectorType
from vantage.domain.experiments import (
    Artefact,
    Experiment,
    ExperimentOutcome,
    ExperimentResult,
    ExperimentStatus,
    ModelConfiguration,
)
from vantage.domain.projects import Project, ProjectType, SourceToolMapping
from vantage.storage.base import AbstractMetadataRepository
from vantage.storage.sqlalchemy.models import (
    AlertRecordModel,
    AlertRuleModel,
    AlertSuppressionRuleModel,
    ExperimentModel,
    ProjectModel,
    ProjectSourceMappingModel,
)


class SQLiteMetadataRepository(AbstractMetadataRepository):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    # ── Projects & Mappings ───────────────────────────────────────────────────

    async def get_project(self, project_id: str) -> Project | None:
        async with self._session_factory() as session:
            stmt = (
                sa.select(ProjectModel)
                .options(sa.orm.selectinload(ProjectModel.source_mappings))
                .where(ProjectModel.id == project_id)
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if not model:
                return None
            return self._project_model_to_domain(model)

    async def save_project(self, project: Project) -> Project:
        async with self._session_factory() as session:
            async with session.begin():
                stmt = sa.select(ProjectModel).where(ProjectModel.id == project.id)
                res = await session.execute(stmt)
                model = res.scalar_one_or_none()
                if not model:
                    model = ProjectModel(id=project.id)
                    session.add(model)

                model.display_name = project.display_name
                model.project_type = (
                    project.project_type.value
                    if isinstance(project.project_type, ProjectType)
                    else str(project.project_type)
                )
                model.owner_team = project.owner_team
                model.owner_email = project.owner_email
                model.description = project.description
                model.log_prompts = project.log_prompts
                model.active = project.active
                if project.created_at:
                    model.created_at = project.created_at

            return (await self.get_project(project.id)) or project

    async def list_projects(self) -> list[Project]:
        async with self._session_factory() as session:
            stmt = (
                sa.select(ProjectModel)
                .options(sa.orm.selectinload(ProjectModel.source_mappings))
                .order_by(ProjectModel.created_at.desc())
            )
            result = await session.execute(stmt)
            models = result.scalars().all()
            return [self._project_model_to_domain(m) for m in models]

    async def get_source_mapping(
        self, source_tool: str, source_identifier: str
    ) -> SourceToolMapping | None:
        async with self._session_factory() as session:
            stmt = sa.select(ProjectSourceMappingModel).where(
                ProjectSourceMappingModel.source_tool == source_tool,
                ProjectSourceMappingModel.source_identifier == source_identifier,
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if not model:
                return None
            return SourceToolMapping(
                id=model.id,
                project_id=model.project_id,
                source_tool=model.source_tool,
                source_identifier=model.source_identifier,
                display_label=model.display_label,
                created_at=model.created_at,
            )

    async def save_source_mapping(
        self, mapping: SourceToolMapping
    ) -> SourceToolMapping:
        async with self._session_factory() as session:
            async with session.begin():
                stmt = sa.select(ProjectSourceMappingModel).where(
                    ProjectSourceMappingModel.source_tool == mapping.source_tool,
                    ProjectSourceMappingModel.source_identifier == mapping.source_identifier,
                )
                res = await session.execute(stmt)
                model = res.scalar_one_or_none()
                if not model:
                    model = ProjectSourceMappingModel(
                        project_id=mapping.project_id,
                        source_tool=mapping.source_tool,
                        source_identifier=mapping.source_identifier,
                    )
                    session.add(model)

                model.display_label = mapping.display_label
                if mapping.created_at:
                    model.created_at = mapping.created_at

            saved = await self.get_source_mapping(
                mapping.source_tool, mapping.source_identifier
            )
            return saved or mapping

    def _project_model_to_domain(self, model: ProjectModel) -> Project:
        mappings = [
            SourceToolMapping(
                id=m.id,
                project_id=m.project_id,
                source_tool=m.source_tool,
                source_identifier=m.source_identifier,
                display_label=m.display_label,
                created_at=m.created_at,
            )
            for m in model.source_mappings
        ]
        return Project(
            id=model.id,
            display_name=model.display_name,
            project_type=ProjectType(model.project_type),
            owner_team=model.owner_team,
            owner_email=model.owner_email,
            description=model.description,
            log_prompts=model.log_prompts,
            active=model.active,
            source_mappings=mappings,
            created_at=model.created_at,
        )

    # ── Experiments ───────────────────────────────────────────────────────────

    async def get_experiment(self, experiment_id: str) -> Experiment | None:
        async with self._session_factory() as session:
            stmt = sa.select(ExperimentModel).where(ExperimentModel.id == experiment_id)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if not model:
                return None
            return self._experiment_model_to_domain(model)

    async def save_experiment(self, experiment: Experiment) -> Experiment:
        async with self._session_factory() as session:
            async with session.begin():
                stmt = sa.select(ExperimentModel).where(
                    ExperimentModel.id == experiment.id
                )
                res = await session.execute(stmt)
                model = res.scalar_one_or_none()
                if not model:
                    model = ExperimentModel(id=experiment.id, slug=experiment.slug)
                    session.add(model)

                model.title = experiment.title
                model.slug = experiment.slug
                model.project_id = experiment.project_id
                model.status = (
                    experiment.status.value
                    if isinstance(experiment.status, ExperimentStatus)
                    else str(experiment.status)
                )
                model.hypothesis = experiment.hypothesis
                model.objective = experiment.objective
                model.owner_name = experiment.owner_name
                model.owner_team = experiment.owner_team
                model.owner_email = experiment.owner_email
                model.start_date = experiment.start_date
                model.expected_end = experiment.expected_end
                model.dataset_description = experiment.dataset_description
                model.baseline_description = experiment.baseline_description

                if experiment.model_configurations:
                    model.model_configurations = json.dumps(
                        [mc.model_dump() for mc in experiment.model_configurations]
                    )

                if experiment.actual_end:
                    model.actual_end = experiment.actual_end

                if experiment.result:
                    res_obj = experiment.result
                    model.outcome = (
                        res_obj.outcome.value
                        if isinstance(res_obj.outcome, ExperimentOutcome)
                        else str(res_obj.outcome)
                    )
                    model.result_summary = res_obj.summary
                    model.metrics_json = json.dumps(res_obj.metrics)
                    model.learnings = res_obj.learnings
                    model.recommendations = res_obj.recommendations

                if experiment.artefacts:
                    model.artefacts_json = json.dumps(
                        [a.model_dump() for a in experiment.artefacts]
                    )

                if experiment.tags:
                    model.tags_json = json.dumps(experiment.tags)

            return (await self.get_experiment(experiment.id)) or experiment

    async def list_experiments(
        self, project_id: str | None = None, status: str | None = None
    ) -> list[Experiment]:
        async with self._session_factory() as session:
            stmt = sa.select(ExperimentModel)
            if project_id:
                stmt = stmt.where(ExperimentModel.project_id == project_id)
            if status:
                stmt = stmt.where(ExperimentModel.status == status)
            stmt = stmt.order_by(ExperimentModel.created_at.desc())
            res = await session.execute(stmt)
            models = res.scalars().all()
            return [self._experiment_model_to_domain(m) for m in models]

    def _experiment_model_to_domain(self, model: ExperimentModel) -> Experiment:
        configs = []
        if model.model_configurations:
            raw = json.loads(model.model_configurations)
            configs = [ModelConfiguration(**item) for item in raw]

        artefacts = []
        if model.artefacts_json:
            raw = json.loads(model.artefacts_json)
            artefacts = [Artefact(**item) for item in raw]

        result = None
        if model.result_summary or model.learnings:
            metrics = json.loads(model.metrics_json) if model.metrics_json else {}
            result = ExperimentResult(
                outcome=ExperimentOutcome(model.outcome)
                if model.outcome
                else ExperimentOutcome.INCONCLUSIVE,
                summary=model.result_summary or "",
                metrics=metrics,
                learnings=model.learnings or "",
                recommendations=model.recommendations,
            )

        tags = json.loads(model.tags_json) if model.tags_json else []

        return Experiment(
            id=model.id,
            title=model.title,
            slug=model.slug,
            project_id=model.project_id,
            status=ExperimentStatus(model.status),
            hypothesis=model.hypothesis,
            objective=model.objective,
            owner_name=model.owner_name,
            owner_team=model.owner_team,
            owner_email=model.owner_email,
            start_date=model.start_date,
            expected_end=model.expected_end,
            dataset_description=model.dataset_description,
            baseline_description=model.baseline_description,
            model_configurations=configs,
            actual_end=model.actual_end,
            result=result,
            artefacts=artefacts,
            tags=tags,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    # ── Alerts & Rules ────────────────────────────────────────────────────────

    async def get_alert_rule(
        self,
        project_id: str,
        detector_type: str | None = None,
        metric_name: str | None = None,
    ) -> AlertRule | None:
        async with self._session_factory() as session:
            stmt = sa.select(AlertRuleModel).where(
                AlertRuleModel.project_id == project_id
            )
            if detector_type:
                stmt = stmt.where(AlertRuleModel.detector_type == detector_type)
            if metric_name:
                stmt = stmt.where(AlertRuleModel.metric_name == metric_name)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if not model:
                return None
            return AlertRule(
                id=model.id,
                project_id=model.project_id,
                detector_type=DetectorType(model.detector_type),
                metric_name=model.metric_name,
                warn_z=model.warn_z,
                crit_z=model.crit_z,
                absolute_threshold=model.absolute_threshold,
                rate_change_factor=model.rate_change_factor,
                error_rate_pct=model.error_rate_pct,
                enabled=model.enabled,
            )

    async def save_alert_rule(self, rule: AlertRule) -> AlertRule:
        async with self._session_factory() as session:
            async with session.begin():
                d_type = (
                    rule.detector_type.value
                    if isinstance(rule.detector_type, DetectorType)
                    else str(rule.detector_type)
                )
                stmt = sa.select(AlertRuleModel).where(
                    AlertRuleModel.project_id == rule.project_id,
                    AlertRuleModel.detector_type == d_type,
                    AlertRuleModel.metric_name == rule.metric_name,
                )
                res = await session.execute(stmt)
                model = res.scalar_one_or_none()
                if not model:
                    model = AlertRuleModel(
                        project_id=rule.project_id,
                        detector_type=d_type,
                        metric_name=rule.metric_name,
                    )
                    session.add(model)

                model.warn_z = rule.warn_z
                model.crit_z = rule.crit_z
                model.absolute_threshold = rule.absolute_threshold
                model.rate_change_factor = rule.rate_change_factor
                model.error_rate_pct = rule.error_rate_pct
                model.enabled = rule.enabled

            saved = await self.get_alert_rule(
                rule.project_id, d_type, rule.metric_name
            )
            return saved or rule

    async def has_active_alert(self, incident_key: str) -> bool:
        if incident_key.startswith("security:"):
            async with self._session_factory() as session:
                stmt = sa.select(AlertRecordModel.id).where(
                    AlertRecordModel.security_incident_key == incident_key,
                    AlertRecordModel.resolved_at == None,  # noqa: E711
                )
                res = await session.execute(stmt)
                return res.scalar_one_or_none() is not None

        parts = incident_key.split(":", 2)
        if len(parts) != 3:
            return False
        project_id, detector_type, metric_name = parts

        async with self._session_factory() as session:
            stmt = sa.select(AlertRecordModel.id).where(
                AlertRecordModel.project_id == project_id,
                AlertRecordModel.detector_type == detector_type,
                AlertRecordModel.metric_name == metric_name,
                AlertRecordModel.resolved_at == None,  # noqa: E711
            )
            res = await session.execute(stmt)
            return res.scalar_one_or_none() is not None

    async def insert_alert(self, alert: AlertRecord) -> AlertRecord:
        async with self._session_factory() as session:
            async with session.begin():
                d_type = (
                    alert.detector_type.value
                    if isinstance(alert.detector_type, DetectorType)
                    else str(alert.detector_type)
                )
                sev = (
                    alert.severity.value
                    if isinstance(alert.severity, AlertSeverity)
                    else str(alert.severity)
                )
                cat = (
                    alert.category.value
                    if hasattr(alert, "category") and alert.category
                    else "observability"
                )
                threats_json = (
                    json.dumps(alert.threat_types)
                    if hasattr(alert, "threat_types") and alert.threat_types
                    else None
                )

                model = AlertRecordModel(
                    alert_uuid=str(alert.alert_id),
                    project_id=alert.project_id,
                    detector_type=d_type,
                    metric_name=alert.metric_name,
                    severity=sev,
                    message=alert.message,
                    current_value=alert.current_value,
                    baseline_value=alert.baseline_value,
                    fired_at=alert.fired_at,
                    resolved_at=alert.resolved_at,
                    notified=alert.notified,
                    category=cat,
                    security_incident_key=alert.security_incident_key,
                    trace_id=alert.trace_id,
                    span_id=alert.span_id,
                    threat_types_json=threats_json,
                )
                session.add(model)
            return alert

    async def resolve_alert(
        self,
        alert_id: str,
        reason: str | None = None,
        note: str | None = None,
        ttl_hours: int | None = None,
        scope: str = "project",
        export_format: str = "dpo"
    ) -> bool:
        async with self._session_factory() as session:
            async with session.begin():
                stmt = sa.select(AlertRecordModel).where(
                    AlertRecordModel.alert_uuid == alert_id
                )
                res = await session.execute(stmt)
                model = res.scalar_one_or_none()
                if not model:
                    return False
                model.resolved_at = datetime.now(timezone.utc)

                # Option 1: False Positive -> Create Time-Bound Suppression Rule (TTL)
                if reason and "False Positive" in reason:
                    expires_at = datetime.utcnow() + timedelta(hours=ttl_hours) if ttl_hours else None
                    supp_model = AlertSuppressionRuleModel(
                        rule_id=str(uuid4()),
                        project_id=model.project_id if scope == "project" else "*",
                        detector_type=model.detector_type,
                        incident_key=model.security_incident_key or f"security:{model.project_id}:{model.trace_id}:{model.span_id}:false_positive",
                        pattern_text=model.message,
                        expires_at=expires_at,
                        scope=scope,
                        created_at=datetime.utcnow()
                    )
                    session.add(supp_model)

                # Option 2: Threat Mitigated & Closed -> Export DPO Fine-Tuning Pair Dataset
                if reason and ("Threat Mitigated" in reason or "Sanitized" in reason or "Policy Updated" in reason):
                    export_dir = Path("export")
                    export_dir.mkdir(exist_ok=True)
                    export_file = export_dir / "adversarial_dataset.jsonl"
                    threats = json.loads(model.threat_types_json) if model.threat_types_json else []

                    if export_format == "dpo":
                        entry = {
                            "id": model.alert_uuid,
                            "project_id": model.project_id,
                            "disposition": reason,
                            "prompt": model.message,
                            "chosen": "I cannot fulfill this request. Security policy violation.",
                            "rejected": "Raw execution output: Request granted.",
                            "metadata": {
                                "detector_type": model.detector_type,
                                "threat_types": threats,
                                "threat_score": model.current_value,
                                "exported_at": datetime.now(timezone.utc).isoformat()
                            }
                        }
                    else:
                        entry = {
                            "id": model.alert_uuid,
                            "project_id": model.project_id,
                            "trace_id": model.trace_id,
                            "span_id": model.span_id,
                            "disposition": reason,
                            "notes": note or "",
                            "messages": [
                                {"role": "user", "content": model.message},
                                {"role": "assistant", "content": "I cannot fulfill this request. Security policy violation."}
                            ],
                            "metadata": {
                                "detector_type": model.detector_type,
                                "threat_types": threats,
                                "threat_score": model.current_value,
                                "exported_at": datetime.now(timezone.utc).isoformat()
                            }
                        }

                    with open(export_file, "a", encoding="utf-8") as f:
                        f.write(json.dumps(entry) + "\n")

                # Option 3 & 4: Upstream Input Sanitized / Policy Updated -> Update Project Policy
                if reason and ("Sanitized" in reason or "Policy Updated" in reason):
                    p_stmt = sa.select(ProjectModel).where(ProjectModel.id == model.project_id)
                    p_res = await session.execute(p_stmt)
                    p_model = p_res.scalar_one_or_none()
                    if p_model:
                        p_model.log_prompts = False

                return True

    async def is_suppressed(self, project_id: str, incident_key: str, threat_type: str | None = None) -> bool:
        async with self._session_factory() as session:
            now = datetime.utcnow()
            stmt = sa.select(AlertSuppressionRuleModel.id).where(
                sa.or_(
                    AlertSuppressionRuleModel.project_id == project_id,
                    AlertSuppressionRuleModel.project_id == "*",
                    AlertSuppressionRuleModel.project_id == "__unmapped__",
                    AlertSuppressionRuleModel.scope == "global"
                ),
                sa.or_(
                    AlertSuppressionRuleModel.expires_at == None,
                    AlertSuppressionRuleModel.expires_at > now
                )
            )
            if threat_type:
                stmt = stmt.where(
                    sa.or_(
                        AlertSuppressionRuleModel.incident_key == incident_key,
                        AlertSuppressionRuleModel.incident_key == f"security:{project_id}:suppress:{threat_type}",
                        AlertSuppressionRuleModel.incident_key == f"security:*:suppress:{threat_type}",
                        AlertSuppressionRuleModel.incident_key == f"security:__unmapped__:suppress:{threat_type}"
                    )
                )
            else:
                stmt = stmt.where(AlertSuppressionRuleModel.incident_key == incident_key)

            res = await session.execute(stmt)
            return res.scalar_one_or_none() is not None

    async def list_alerts(
        self, project_id: str | None = None, unresolved_only: bool = False
    ) -> list[AlertRecord]:
        async with self._session_factory() as session:
            stmt = sa.select(AlertRecordModel)
            if project_id:
                stmt = stmt.where(AlertRecordModel.project_id == project_id)
            if unresolved_only:
                stmt = stmt.where(AlertRecordModel.resolved_at == None)  # noqa: E711
            stmt = stmt.order_by(AlertRecordModel.fired_at.desc())

            res = await session.execute(stmt)
            models = res.scalars().all()
            return [
                AlertRecord(
                    alert_id=m.alert_uuid,
                    project_id=m.project_id,
                    detector_type=DetectorType(m.detector_type),
                    metric_name=m.metric_name,
                    severity=AlertSeverity(m.severity),
                    message=m.message,
                    current_value=m.current_value,
                    baseline_value=m.baseline_value,
                    fired_at=m.fired_at,
                    resolved_at=m.resolved_at,
                    notified=m.notified,
                    category=m.category or "observability",
                    security_incident_key=m.security_incident_key,
                    trace_id=m.trace_id,
                    span_id=m.span_id,
                    threat_types=json.loads(m.threat_types_json) if m.threat_types_json else [],
                )
                for m in models
            ]
