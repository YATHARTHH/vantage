import pytest
import time
from vantage.security.context import SecurityContext
from vantage.security.policy_gate import MultiSignalPolicyGate
from vantage.security.tool_authorizer import ToolAuthorizer
from vantage.security.approval_workflow import HumanApprovalWorkflow
from vantage.security.output_inspector import OutputInspector, DataClassification, DestinationTrust
from vantage.security.execution_controller import ExecutionController


def dummy_tool(args):
    return {"status": "success", "result": f"Executed with {args}"}


class TestAdversarialSecurityArchitecture:

    def test_stale_approval_policy_version_blocked(self):
        """
        Test 1: Verification that changing policy version between approval creation
        and execution invalidates approval and blocks execution (reason_code = APPROVAL_POLICY_STALE).
        """
        controller = ExecutionController()
        ctx = SecurityContext(
            request_id="req_001",
            trace_id="tr_001",
            span_id="sp_001",
            principal_id="prn_dev",
            agent_id="agent_order_service",
            project_id="proj_alpha",
            environment="staging",
            tool_name="database.write",
            action="database.write",
            resource="orders",
            tool_risk="HIGH",
            policy_version="v1.2.0",
        )
        args = {"order_id": 1234, "amount": 99.9}

        # 1. Request execution -> returns PENDING_APPROVAL
        res1 = controller.execute(ctx, dummy_tool, args)
        assert res1.status == "PENDING_APPROVAL"
        appr_id = res1.approval_id
        assert appr_id is not None

        # 2. Human approves the request
        controller.approval_workflow.approve(appr_id, approved_by="admin@company.com")

        # 3. Policy is updated to v1.3.0
        controller.policy_gate.policy_version = "v1.3.0"

        # 4. Agent attempts execution -> must be BLOCKED due to stale policy version
        res2 = controller.execute(ctx, dummy_tool, args, approval_id=appr_id)
        assert res2.status == "BLOCKED"
        assert res2.reason_code == "APPROVAL_POLICY_STALE"

    def test_modified_environment_after_approval_blocked(self):
        """
        Test 2: Verification that changing target environment (staging -> production)
        after approval invalidates TOCTOU fingerprint and blocks execution (APPROVAL_FINGERPRINT_MISMATCH).
        """
        controller = ExecutionController()
        # Grant capability for both staging and production to test TOCTOU fingerprint check
        controller.authorizer.grant_capability("prn_dev", "agent_order_service", "database.write", "orders", "production")

        ctx_staging = SecurityContext(
            request_id="req_002",
            trace_id="tr_002",
            span_id="sp_002",
            principal_id="prn_dev",
            agent_id="agent_order_service",
            project_id="proj_alpha",
            environment="staging",
            tool_name="database.write",
            action="database.write",
            resource="orders",
            tool_risk="HIGH",
        )
        args = {"order_id": 1234, "amount": 99.9}

        # Request execution in staging
        res1 = controller.execute(ctx_staging, dummy_tool, args)
        assert res1.status == "PENDING_APPROVAL"
        appr_id = res1.approval_id

        # Human approves
        controller.approval_workflow.approve(appr_id, approved_by="admin@company.com")

        # Attacker attempts to reuse approval in production environment
        ctx_prod = SecurityContext(
            request_id="req_002",
            trace_id="tr_002",
            span_id="sp_002",
            principal_id="prn_dev",
            agent_id="agent_order_service",
            project_id="proj_alpha",
            environment="production",  # Environment changed!
            tool_name="database.write",
            action="database.write",
            resource="orders",
            tool_risk="HIGH",
        )

        res2 = controller.execute(ctx_prod, dummy_tool, args, approval_id=appr_id)
        assert res2.status == "BLOCKED"
        assert res2.reason_code == "APPROVAL_FINGERPRINT_MISMATCH"

    def test_unauthorized_agent_identity_spoof_blocked(self):
        """
        Test 3: Verification that an agent claiming another agent's capability
        is denied (reason_code = TOOL_CAPABILITY_DENIED).
        """
        controller = ExecutionController()
        ctx = SecurityContext(
            request_id="req_003",
            trace_id="tr_003",
            span_id="sp_003",
            principal_id="prn_dev",
            agent_id="agent_customer_support",  # Support agent trying admin action
            project_id="proj_alpha",
            environment="production",
            tool_name="database.delete",
            action="database.delete",
            resource="customers",
            tool_risk="CRITICAL",
        )
        args = {"customer_id": 99}

        # Context claims prn_dev / agent_customer_support, but attempts database.delete
        res = controller.execute(ctx, dummy_tool, args, authenticated_principal_id="prn_dev", authenticated_agent_id="agent_customer_support")
        assert res.status == "BLOCKED"
        assert res.reason_code == "TOOL_CAPABILITY_DENIED"

    def test_data_exfiltration_sensitive_to_external_blocked(self):
        """
        Test 4: Verification that routing RESTRICTED data payload to UNKNOWN_EXTERNAL endpoint
        is blocked (reason_code = DATA_EXFILTRATION_PREVENTED).
        """
        controller = ExecutionController()
        controller.authorizer.grant_capability("prn_dev", "agent_order_service", "http.post", "external_endpoint", "staging")

        ctx = SecurityContext(
            request_id="req_004",
            trace_id="tr_004",
            span_id="sp_004",
            principal_id="prn_dev",
            agent_id="agent_order_service",
            project_id="proj_alpha",
            environment="staging",
            tool_name="http.post",
            action="http.post",
            resource="external_endpoint",
            tool_risk="MEDIUM",
        )
        args = {"payload": "RESTRICTED top_secret data private_key"}

        res = controller.execute(ctx, dummy_tool, args, destination="untrusted.external.com")
        assert res.status == "BLOCKED"
        assert res.reason_code == "DATA_EXFILTRATION_PREVENTED"

    def test_policy_engine_failure_blocks_critical_tool_but_not_telemetry(self):
        """
        Test 5: Verification of Fail-Closed tool enforcement path when policy engine throws
        an internal error (returns BLOCK with SECURITY_ENGINE_FAILURE).
        """
        faulty_gate = MultiSignalPolicyGate()

        # Monkeypatch evaluate to raise an exception
        def broken_eval(*args, **kwargs):
            raise RuntimeError("Scanner backend crash")

        faulty_gate.evaluate = broken_eval

        controller = ExecutionController(policy_gate=faulty_gate)
        ctx = SecurityContext(
            request_id="req_005",
            trace_id="tr_005",
            span_id="sp_005",
            principal_id="prn_dev",
            agent_id="agent_order_service",
            project_id="proj_alpha",
            environment="staging",
            tool_name="database.write",
            action="database.write",
            resource="orders",
            tool_risk="HIGH",
        )
        args = {"order_id": 42}

        # Tool execution must fail-closed
        res = controller.execute(ctx, dummy_tool, args)
        assert res.status == "BLOCKED"
        assert res.reason_code == "SECURITY_ENGINE_FAILURE"
