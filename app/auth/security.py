import hashlib
import hmac
import secrets

_ALGORITMO = "sha256"
_ITERACOES = 200_000


def hash_senha(senha: str) -> str:
    """Deriva um hash de senha com PBKDF2-HMAC-SHA256 (stdlib, sem dependência nova de
    hashing) — formato armazenado `"{salt_hex}${hash_hex}"`."""
    salt = secrets.token_bytes(16)
    derivado = hashlib.pbkdf2_hmac(_ALGORITMO, senha.encode("utf-8"), salt, _ITERACOES)
    return f"{salt.hex()}${derivado.hex()}"


def verificar_senha(senha: str, senha_hash: str) -> bool:
    salt_hex, _, hash_hex = senha_hash.partition("$")
    if not salt_hex or not hash_hex:
        return False
    salt = bytes.fromhex(salt_hex)
    derivado = hashlib.pbkdf2_hmac(_ALGORITMO, senha.encode("utf-8"), salt, _ITERACOES)
    return hmac.compare_digest(derivado.hex(), hash_hex)
