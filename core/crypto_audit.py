import hashlib
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

class MerkleManager:
    def __init__(self, private_key_path="private.pem"):
        self.prev_root = "0" * 64
        with open(private_key_path, "rb") as k:
            self.private_key = serialization.load_pem_private_key(k.read(), password=None)

    def build_merkle_root(self, leaf_hashes: list[str]) -> str:
        if not leaf_hashes: return "0" * 64
        if len(leaf_hashes) == 1: return leaf_hashes[0]

        new_level = []
        for i in range(0, len(leaf_hashes), 2):
            left = leaf_hashes[i]
            right = leaf_hashes[i+1] if i+1 < len(leaf_hashes) else left
            new_level.append(hashlib.sha256((left + right).encode()).hexdigest())
        return self.build_merkle_root(new_level)

    def sign_hash(self, payload: str) -> str:
        signature = self.private_key.sign(
            payload.encode(),
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256()
        )
        return signature.hex()
