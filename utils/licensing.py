from __future__ import annotations

import base64
import json
import time
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature

# Paste the Public Key printed by admin_keygen.py here:
PUBLIC_KEY_B64 = "nAzbeTvYChM8amhz1SCJxULUMoaD-YkMb6YPVWSVDS0"


class LicenseError(ValueError):
    pass


def _b64d(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


def verify_key(license_key: str, expected_user_id: int | str | None = None) -> dict:
    if not license_key or not isinstance(license_key, str):
        raise LicenseError("No license key provided in config.json.")

    parts = license_key.strip().split(".")
    if len(parts) != 3 or parts[0] != "NOVA1":
        raise LicenseError("Invalid license key format.")

    _, payload_b64, sig_b64 = parts

    try:
        pub = Ed25519PublicKey.from_public_bytes(_b64d(PUBLIC_KEY_B64))
        pub.verify(_b64d(sig_b64), payload_b64.encode("ascii"))
        claims = json.loads(_b64d(payload_b64).decode("utf-8"))
    except (InvalidSignature, Exception):
        raise LicenseError("License signature verification failed.")

    if claims.get("product") != "nova-selfbot":
        raise LicenseError("License key is not valid for this bot.")

    now = int(time.time())
    exp = claims.get("exp")
    if exp is not None and now > int(exp):
        raise LicenseError("Your license key has expired.")

    if expected_user_id is not None and str(claims.get("sub")) != str(expected_user_id):
        raise LicenseError(
            f"License is bound to Discord ID {claims.get('sub')}, not {expected_user_id}."
        )

    return claims