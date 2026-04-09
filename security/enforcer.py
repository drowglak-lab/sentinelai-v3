import uuid
from typing import Dict, Any, Tuple
from core.database import get_db_connection

class DeterministicEnforcer:
    def __init__(self, db_conn):
        self.db = db_conn

    async def _get_trusted_beneficiary(self, user_id: str, beneficiary_uuid: str) -> dict:
        """
        Берет данные получателя ТОЛЬКО из защищенной БД, а не из того, что сгенерировала LLM.
        """
        cursor = await self.db.execute("""
            SELECT account_iban, is_active, aml_risk_score, country_code 
            FROM approved_beneficiaries 
            WHERE id = ? AND owner_user_id = ?
        """, (beneficiary_uuid, user_id))
        return await cursor.fetchone()

    async def validate_transfer_intent(self, user_id: str, ai_payload: Dict[str, Any]) -> Tuple[bool, str, dict]:
        """
        Жесткая проверка намерений ИИ. Возвращает: (Успех, Причина_отказа, Безопасный_Payload)
        """
        # 1. Схема данных: ИИ должен прислать UUID получателя, а не сам IBAN!
        target_uuid = ai_payload.get("target_beneficiary_id")
        amount = ai_payload.get("amount")

        if not target_uuid or not amount:
            return False, "MALFORMED_INTENT: Missing required fields", {}

        try:
            amount = float(amount)
            if amount <= 0 or amount > 50000: # Жесткий хардкод лимитов
                return False, "HARD_LIMIT_EXCEEDED: Amount out of bounds", {}
        except ValueError:
            return False, "MALFORMED_INTENT: Invalid amount format", {}

        # 2. Semantic Check: Проверяем получателя по нашей БД
        beneficiary = await self._get_trusted_beneficiary(user_id, target_uuid)
        
        if not beneficiary:
            # Сработала защита! ИИ попытался подсунуть левый счет, которого нет в белом списке пользователя.
            return False, "SEMANTIC_VIOLATION: Unknown or unauthorized beneficiary ID", {}

        # 3. Compliance Check (Имитация AML/KYC)
        if beneficiary["is_active"] != 1:
            return False, "COMPLIANCE_BLOCK: Beneficiary account is frozen", {}
            
        if beneficiary["aml_risk_score"] > 80:
            return False, "COMPLIANCE_BLOCK: Beneficiary flagged for High AML Risk", {}
            
        if beneficiary["country_code"] in ["NK", "IR", "SY"]: # Санкционные списки
            return False, "COMPLIANCE_BLOCK: Beneficiary in sanctioned region", {}

        # 4. Сборка БЕЗОПАСНОГО payload для Transaction Manager
        # Мы игнорируем любые метки (labels) или комментарии, которые сгенерировала LLM.
        safe_execution_context = {
            "user_id": user_id,
            "amount": amount,
            "target_iban": beneficiary["account_iban"], # Берем настоящий IBAN из базы!
            "internal_label": "USER_INITIATED_TRANSFER" # Перезаписываем label
        }

        return True, "INTENT_APPROVED", safe_execution_context
