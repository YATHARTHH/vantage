from typing import Dict, Set, Tuple, Optional
from vantage.security.context import SecurityContext


class ToolAuthorizer:
    """
    Deny-by-default Tool Capability Matrix and Environment Authorizer.
    Capabilities are strictly scoped by Action + Resource + Environment.
    Authorization is bound to authenticated Principal identity (Principal -> Agent -> Capability).
    """

    def __init__(self):
        # Default capability grants matrix:
        # key: (principal_id, agent_id) -> set of granted capability patterns "action:resource:environment"
        self._grant_matrix: Dict[Tuple[str, str], Set[str]] = {
            ("prn_admin", "agent_admin"): {"*:*:*"},
            ("prn_dev", "agent_order_service"): {
                "database.write:orders:staging",
                "database.read:orders:staging",
                "database.read:orders:production",
                "analytics.send:metrics:production",
                "analytics.send:metrics:staging",
            },
            ("prn_dev", "agent_customer_support"): {
                "database.read:customers:staging",
                "database.read:customers:production",
                "email.send:support:staging",
            },
        }

    def grant_capability(
        self, principal_id: str, agent_id: str, action: str, resource: str, environment: str
    ) -> None:
        key = (principal_id, agent_id)
        if key not in self._grant_matrix:
            self._grant_matrix[key] = set()
        pattern = f"{action}:{resource}:{environment}"
        self._grant_matrix[key].add(pattern)

    def is_authorized(
        self,
        ctx: SecurityContext,
        authenticated_principal_id: Optional[str] = None,
        authenticated_agent_id: Optional[str] = None
    ) -> bool:
        """
        Evaluates whether the action:resource:environment requested in SecurityContext
        is explicitly authorized for the authenticated principal and agent identity.
        Deny-by-default: returns False if ungranted or if identity spoofing is detected.
        """
        eff_principal = authenticated_principal_id or ctx.principal_id
        eff_agent = authenticated_agent_id or ctx.agent_id

        # Identity spoofing check: context identity must match authenticated identity
        if ctx.principal_id != eff_principal or ctx.agent_id != eff_agent:
            return False

        key = (eff_principal, eff_agent)
        granted_patterns = self._grant_matrix.get(key, set())

        target_capability = f"{ctx.action}:{ctx.resource}:{ctx.environment}"

        for pattern in granted_patterns:
            if pattern == "*:*:*" or pattern == target_capability:
                return True
            
            # Wildcard matching (e.g., "database.read:*:staging")
            p_parts = pattern.split(":")
            t_parts = target_capability.split(":")
            if len(p_parts) == 3 and len(t_parts) == 3:
                match_action = (p_parts[0] == "*" or p_parts[0] == t_parts[0])
                match_resource = (p_parts[1] == "*" or p_parts[1] == t_parts[1])
                match_env = (p_parts[2] == "*" or p_parts[2] == t_parts[2])
                if match_action and match_resource and match_env:
                    return True

        return False
