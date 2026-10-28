"""Library upgrades must preserve issued HS256 sessions and reject tampering."""
import base64
import hashlib
import hmac
import json
import time

import pytest
from fastapi.security import HTTPAuthorizationCredentials

from app.api.deps import _decode
from app.core.config import get_settings
from app.core.errors import ApiError


def _legacy_token(key, *, exp=None, algorithm='HS256'):
    # The compact HMAC format emitted by the previous python-jose library.
    def part(value):
        return base64.urlsafe_b64encode(json.dumps(value, separators=(',', ':')).encode()).rstrip(b'=')
    message = b'.'.join([part({'alg': algorithm, 'typ': 'JWT'}), part({'sub': '7', 'role': 'staff', 'exp': exp or int(time.time()) + 3600})])
    signature = base64.urlsafe_b64encode(hmac.new(key.encode(), message, hashlib.sha256).digest()).rstrip(b'=')
    return (message + b'.' + signature).decode()


def test_existing_hs256_format_remains_valid(monkeypatch):
    key = 'legacy-test-key-at-least-thirty-two-bytes'
    monkeypatch.setattr(get_settings(), 'secret_key', key)
    payload = _decode(HTTPAuthorizationCredentials(scheme='Bearer', credentials=_legacy_token(key)))
    assert payload['sub'] == '7' and payload['role'] == 'staff'


@pytest.mark.parametrize('failure', ['wrong-key', 'expired', 'wrong-algorithm'])
def test_invalid_legacy_sessions_are_still_401(monkeypatch, failure):
    key = 'legacy-test-key-at-least-thirty-two-bytes'
    monkeypatch.setattr(get_settings(), 'secret_key', key)
    token = _legacy_token('other-test-key-at-least-thirty-two-bytes' if failure == 'wrong-key' else key,
                          exp=int(time.time()) - 60 if failure == 'expired' else None,
                          algorithm='HS384' if failure == 'wrong-algorithm' else 'HS256')
    with pytest.raises(ApiError) as error:
        _decode(HTTPAuthorizationCredentials(scheme='Bearer', credentials=token))
    assert error.value.status_code == 401
