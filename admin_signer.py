import os
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives import serialization

POLICY_PATH = "core/policies.yaml"
SIG_PATH = "core/policies.sig"
PRIVATE_KEY_PATH = "private.pem"
PUBLIC_KEY_PATH = "core/public.pem" # Этот ключ мы отдадим серверу

def generate_keys():
    print("🔑 Генерация RSA ключей (2048 бит)...")
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    
    with open(PRIVATE_KEY_PATH, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
        
    with open(PUBLIC_KEY_PATH, "wb") as f:
        f.write(private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ))
    print("✅ Ключи созданы. private.pem НЕ ДОЛЖЕН попасть в продакшен!")

def sign_policy():
    if not os.path.exists(PRIVATE_KEY_PATH):
        generate_keys()

    with open(PRIVATE_KEY_PATH, "rb") as key_file:
        private_key = serialization.load_pem_private_key(key_file.read(), password=None)

    with open(POLICY_PATH, "rb") as f:
        payload = f.read()

    # Создаем криптографическую подпись (RSA-PSS)
    signature = private_key.sign(
        payload,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256()
    )

    with open(SIG_PATH, "wb") as f:
        f.write(signature)
    
    print(f"✅ Файл {POLICY_PATH} успешно подписан. Подпись: {SIG_PATH}")

if __name__ == "__main__":
    sign_policy()
