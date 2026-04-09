from enum import Enum
from typing import List, Set

class AgentScope(str, Enum):
    """Granular permissions (Scopes) for AI Agents."""
    READ_BALANCE = "account:read_balance"
    READ_HISTORY = "account:read_history"
    TRANSFER_FUNDS = "payment:transfer_funds"

class AgentRole(str, Enum):
    """Predefined roles grouping multiple scopes."""
    BASIC_ASSISTANT = "role:basic_assistant"
    WEALTH_MANAGER = "role:wealth_manager"

ROLE_PERMISSIONS = {
    AgentRole.BASIC_ASSISTANT: {AgentScope.READ_BALANCE, AgentScope.READ_HISTORY},
    AgentRole.WEALTH_MANAGER: {AgentScope.READ_BALANCE, AgentScope.READ_HISTORY, AgentScope.TRANSFER_FUNDS},
}

def resolve_agent_scopes(roles: List[str]) -> Set[str]:
    """Compiles a final set of allowed scopes."""
    allowed_scopes = set()
    for role_str in roles:
        try:
            role = AgentRole(role_str)
            allowed_scopes.update(ROLE_PERMISSIONS.get(role, set()))
        except ValueError:
            pass
    return {scope.value for scope in allowed_scopes}
