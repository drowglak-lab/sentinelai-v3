import yaml
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

# ==========================================
# 1. СТРОГИЕ СХЕМЫ (Pydantic Validation)
# ==========================================
class ActionLimits(BaseModel):
    max_amount_usd: Optional[float] = Field(None, description="Максимальная сумма операции")

class ActionRestrictions(BaseModel):
    blocked_prefixes: Optional[List[str]] = Field(default_factory=list)
    require_mfa_over: Optional[float] = Field(None)

class ActionPolicy(BaseModel):
    allowed_roles: List[str] = Field(..., description="Роли, которым разрешено действие")
    limits: ActionLimits = Field(default_factory=ActionLimits)
    restrictions: ActionRestrictions = Field(default_factory=ActionRestrictions)

class SecurityPolicy(BaseModel):
    version: str
    description: str
    actions: Dict[str, ActionPolicy]

# ==========================================
# 2. ДВИЖОК ОЦЕНКИ (Evaluation Engine)
# ==========================================
class PolicyEngine:
    def __init__(self, policy_path: str = "config/policies.yaml"):
        self.policy_path = policy_path
        self._policy: Optional[SecurityPolicy] = None
        self.reload_policies()

    def reload_policies(self):
        """Горячая перезагрузка политик из файла"""
        try:
            with open(self.policy_path, "r", encoding="utf-8") as f:
                raw_data = yaml.safe_load(f)
                # Pydantic автоматически проверит структуру YAML файла
                self._policy = SecurityPolicy(**raw_data)
                print(f"🛡️ [Policy Engine] Loaded policies v{self._policy.version}")
        except FileNotFoundError:
            print(f"❌ [Policy Engine] Policy file not found: {self.policy_path}")
            raise
        except Exception as e:
            print(f"❌ [Policy Engine] Invalid policy format: {e}")
            raise

    def evaluate(self, action: str, role: str, context: Dict[str, Any]) -> tuple[bool, str]:
        """
        Оценивает контекст запроса против загруженных политик.
        Возвращает (is_allowed, reason).
        """
        if not self._policy:
            return False, "POLICIES_NOT_LOADED"

        action_policy = self._policy.actions.get(action)
        if not action_policy:
            return False, f"ACTION_NOT_DEFINED: {action}"

        # 1. Проверка RBAC (Роли)
        if role not in action_policy.allowed_roles:
            return False, f"ROLE_NOT_ALLOWED: {role}"

        # 2. Проверка лимитов (ABAC)
        amount = context.get("amount")
        if amount is not None and action_policy.limits.max_amount_usd:
            if amount > action_policy.limits.max_amount_usd:
                return False, f"LIMIT_EXCEEDED: max {action_policy.limits.max_amount_usd}"

        # 3. Проверка ограничений (Специфичные правила)
        target = context.get("target", "")
        for prefix in action_policy.restrictions.blocked_prefixes:
            if str(target).startswith(prefix):
                return False, f"TARGET_BLOCKED: matches prefix '{prefix}'"

        return True, "ALLOWED"
