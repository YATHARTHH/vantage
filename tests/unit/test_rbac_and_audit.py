"""Unit & Integration Tests for Enterprise RBAC and Tamper-Evident Audit Logging."""
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from vantage.api.app import app
from vantage.services.audit_service import AuditService
from vantage.storage.sqlalchemy.models import AuditLogModel
from vantage.storage.sqlalchemy.session import init_db, get_session_factory


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db()


@pytest.fixture
async def db_session():
    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session


@pytest.mark.asyncio
async def test_api_key_creation_bearer_auth_and_audit(async_client: AsyncClient):
    # Step 1: Create key using dev-local-key (admin)
    headers = {"Authorization": "Bearer dev-local-key"}
    payload = {
        "display_name": "Test Dev Key",
        "role": "developer",
        "project_id": "test-project-1",
        "expires_in_days": 30,
    }
    res = await async_client.post("/api/v1/api-keys", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "plaintext_key" in data
    assert data["plaintext_key"].startswith("vg_live_")
    key_id = data["key_id"]
    raw_key = data["plaintext_key"]

    # Step 2: Use new developer key to access DAG traces (developer permission: dag.read)
    dev_headers = {"Authorization": f"Bearer {raw_key}"}
    res_traces = await async_client.get("/api/v1/analytics/dag/traces", headers=dev_headers)
    assert res_traces.status_code == 200


@pytest.mark.asyncio
async def test_permission_hierarchy_and_role_escalation(async_client: AsyncClient):
    # Create viewer key
    admin_headers = {"Authorization": "Bearer dev-local-key"}
    payload = {"display_name": "Viewer Key", "role": "viewer"}
    res = await async_client.post("/api/v1/api-keys", json=payload, headers=admin_headers)
    assert res.status_code == 200
    viewer_key = res.json()["plaintext_key"]

    viewer_headers = {"Authorization": f"Bearer {viewer_key}"}

    # Viewer can read projects
    res_proj = await async_client.get("/api/v1/projects", headers=viewer_headers)
    assert res_proj.status_code == 200

    # Viewer CANNOT create API keys (Requires api_key.manage) -> 403 Forbidden
    res_forbidden = await async_client.post(
        "/api/v1/api-keys",
        json={"display_name": "Hack", "role": "admin"},
        headers=viewer_headers,
    )
    assert res_forbidden.status_code == 403
    assert "lacks required permission" in res_forbidden.json()["detail"]


@pytest.mark.asyncio
async def test_project_scope_isolation(async_client: AsyncClient):
    # Create key restricted to 'proj-alpha'
    admin_headers = {"Authorization": "Bearer dev-local-key"}
    payload = {"display_name": "Alpha Scoped Key", "role": "developer", "project_id": "proj-alpha"}
    res = await async_client.post("/api/v1/api-keys", json=payload, headers=admin_headers)
    scoped_key = res.json()["plaintext_key"]

    scoped_headers = {"Authorization": f"Bearer {scoped_key}"}

    # Query proj-alpha -> Allowed
    res_alpha = await async_client.get("/api/v1/analytics/dag/traces?project_id=proj-alpha", headers=scoped_headers)
    assert res_alpha.status_code == 200

    # Query proj-beta -> 403 Forbidden
    res_beta = await async_client.get("/api/v1/analytics/dag/traces?project_id=proj-beta", headers=scoped_headers)
    assert res_beta.status_code == 403
    assert "restricted to project scope" in res_beta.json()["detail"]


@pytest.mark.asyncio
async def test_soft_key_revocation(async_client: AsyncClient):
    admin_headers = {"Authorization": "Bearer dev-local-key"}

    # Create key
    res = await async_client.post(
        "/api/v1/api-keys",
        json={"display_name": "To Be Revoked", "role": "developer"},
        headers=admin_headers,
    )
    key_id = res.json()["key_id"]
    raw_key = res.json()["plaintext_key"]

    # Revoke key
    res_del = await async_client.delete(f"/api/v1/api-keys/{key_id}", headers=admin_headers)
    assert res_del.status_code == 200
    assert res_del.json()["status"] == "revoked"

    # Try to use revoked key -> 401 Unauthorized
    rev_headers = {"Authorization": f"Bearer {raw_key}"}
    res_unauth = await async_client.get("/api/v1/projects", headers=rev_headers)
    assert res_unauth.status_code == 401


import uuid

@pytest.mark.asyncio
async def test_hash_chained_audit_log_and_tampering_detection(db_session):
    audit_svc = AuditService(db_session)
    test_proj = f"test-audit-proj-{uuid.uuid4().hex[:8]}"

    # Append 3 audit records
    log1 = await audit_svc.append_event("key-1", "ACTION_1", "resource_a", project_id=test_proj, details={"val": 1})
    log2 = await audit_svc.append_event("key-1", "ACTION_2", "resource_b", project_id=test_proj, details={"val": 2})
    log3 = await audit_svc.append_event("key-2", "ACTION_3", "resource_c", project_id=test_proj, details={"val": 3})

    assert isinstance(log1.previous_hash, str) and len(log1.previous_hash) > 0
    assert log2.previous_hash == log1.record_hash
    assert log3.previous_hash == log2.record_hash

    # Verify integrity (valid)
    valid, errors = await audit_svc.verify_integrity(project_id=test_proj)
    print("VERIFY ERRORS:", errors)
    assert valid is True
    assert len(errors) == 0

    # Intentionally corrupt log2 details in SQL database
    stmt = select(AuditLogModel).where(AuditLogModel.id == log2.id)
    res = await db_session.execute(stmt)
    corrupt_target = res.scalar_one()
    corrupt_target.details_json = '{"val": 9999}'  # Tampered!
    await db_session.commit()

    # Re-verify integrity (detects tampering!)
    valid_after_tamper, errors_after_tamper = await audit_svc.verify_integrity(project_id=test_proj)
    assert valid_after_tamper is False
    assert len(errors_after_tamper) > 0
    assert "Hash corruption at record ID" in errors_after_tamper[0]
