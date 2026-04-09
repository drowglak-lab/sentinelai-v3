from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional, Dict, List
import uuid

@dataclass
class Context:
    # Идентификация
    tx_id: str
    timestamp: datetime
    raw_payload: Dict[str, Any]
    
    # Доменные данные (то, что идет в Rust)
    domain_data: Dict[str, Any] = field(default_factory=dict)
    
    # Результаты работы
    decision: Optional[str] = None
    policy_id: Optional[str] = None
    version: str = "unknown"
    traces: List[Any] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    # ⚡ НОВОЕ: Сюда пишем человекочитаемые объяснения
    reasons: List[str] = field(default_factory=list)

class ContextFactory:
    @staticmethod
    def from_http(payload: Dict[str, Any]) -> Context:
        return Context(
            tx_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            raw_payload=payload,
            domain_data={
                "amount": float(payload.get("amount", 0.0)),
                "country": str(payload.get("country", "unknown")),
                "risk_score": float(payload.get("risk", 0.6)),
                "is_new": payload.get("user_tier") == "new"
            }
        )
