import pytest
import yaml
import os
from execution.policy_engine import PolicyEngine

# Фикстура: создает временный YAML файл с политиками специально для тестов
@pytest.fixture
def test_policy_file(tmp_path):
    policy_data = {
        "version": "1.0.0",
        "description": "Test Policies",
        "actions": {
            "transfer_funds": {
                "allowed_roles": ["USER", "ADMIN"],
                "limits": {
                    "max_amount_usd": 5000.0
                },
                "restrictions": {
                    "blocked_prefixes": ["CRYPTO_"]
                }
            }
        }
    }
    file_path = tmp_path / "test_policies.yaml"
    with open(file_path, "w", encoding="utf-8") as f:
        yaml.dump(policy_data, f)
    return str(file_path)

def test_policy_engine_rbac(test_policy_file):
    engine = PolicyEngine(policy_path=test_policy_file)
    
    # Легитимная роль
    is_allowed, reason = engine.evaluate("transfer_funds", "USER", {"amount": 100, "target": "Bank"})
    assert is_allowed is True

    # Роль без доступа
    is_allowed, reason = engine.evaluate("transfer_funds", "HACKER", {"amount": 100, "target": "Bank"})
    assert is_allowed is False
    assert "ROLE_NOT_ALLOWED" in reason

def test_policy_engine_abac_limits(test_policy_file):
    engine = PolicyEngine(policy_path=test_policy_file)
    
    # В пределах лимита
    is_allowed, reason = engine.evaluate("transfer_funds", "USER", {"amount": 4999, "target": "Bank"})
    assert is_allowed is True

    # Превышение лимита
    is_allowed, reason = engine.evaluate("transfer_funds", "USER", {"amount": 6000, "target": "Bank"})
    assert is_allowed is False
    assert "LIMIT_EXCEEDED" in reason

def test_policy_engine_restrictions(test_policy_file):
    engine = PolicyEngine(policy_path=test_policy_file)
    
    # Запрещенный префикс
    is_allowed, reason = engine.evaluate("transfer_funds", "USER", {"amount": 100, "target": "CRYPTO_WALLET"})
    assert is_allowed is False
    assert "TARGET_BLOCKED" in reason
