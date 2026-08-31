"""Initial SQLite metadata schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-09-01 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'projects',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('display_name', sa.String(), nullable=False),
        sa.Column('project_type', sa.String(), nullable=False),
        sa.Column('owner_team', sa.String(), nullable=False),
        sa.Column('owner_email', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('log_prompts', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'project_source_mappings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('project_id', sa.String(), nullable=False),
        sa.Column('source_tool', sa.String(), nullable=False),
        sa.Column('source_identifier', sa.String(), nullable=False),
        sa.Column('display_label', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_tool', 'source_identifier', name='uq_source_mapping')
    )

    op.create_table(
        'experiments',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('slug', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='planned'),
        sa.Column('hypothesis', sa.Text(), nullable=False),
        sa.Column('objective', sa.Text(), nullable=False),
        sa.Column('owner_name', sa.String(), nullable=False),
        sa.Column('owner_team', sa.String(), nullable=False),
        sa.Column('owner_email', sa.String(), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('expected_end', sa.Date(), nullable=False),
        sa.Column('dataset_description', sa.Text(), nullable=True),
        sa.Column('baseline_description', sa.Text(), nullable=True),
        sa.Column('model_configurations', sa.Text(), nullable=True),
        sa.Column('actual_end', sa.Date(), nullable=True),
        sa.Column('outcome', sa.String(), nullable=True),
        sa.Column('result_summary', sa.Text(), nullable=True),
        sa.Column('metrics_json', sa.Text(), nullable=True),
        sa.Column('learnings', sa.Text(), nullable=True),
        sa.Column('recommendations', sa.Text(), nullable=True),
        sa.Column('artefacts_json', sa.Text(), nullable=True),
        sa.Column('tags_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )

    op.create_table(
        'alert_rules',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('project_id', sa.String(), nullable=False),
        sa.Column('detector_type', sa.String(), nullable=False),
        sa.Column('metric_name', sa.String(), nullable=False),
        sa.Column('warn_z', sa.Float(), nullable=False, server_default='2.0'),
        sa.Column('crit_z', sa.Float(), nullable=False, server_default='3.0'),
        sa.Column('absolute_threshold', sa.Float(), nullable=True),
        sa.Column('rate_change_factor', sa.Float(), nullable=False, server_default='1.5'),
        sa.Column('error_rate_pct', sa.Float(), nullable=False, server_default='5.0'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='1'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', 'detector_type', 'metric_name', name='uq_alert_rule_signal')
    )

    op.create_table(
        'alert_records',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('alert_uuid', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), nullable=False),
        sa.Column('detector_type', sa.String(), nullable=False),
        sa.Column('metric_name', sa.String(), nullable=False),
        sa.Column('severity', sa.String(), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('current_value', sa.Float(), nullable=False),
        sa.Column('baseline_value', sa.Float(), nullable=True),
        sa.Column('fired_at', sa.DateTime(), nullable=False),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('notified', sa.Boolean(), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('alert_uuid')
    )


def downgrade() -> None:
    op.drop_table('alert_records')
    op.drop_table('alert_rules')
    op.drop_table('experiments')
    op.drop_table('project_source_mappings')
    op.drop_table('projects')
