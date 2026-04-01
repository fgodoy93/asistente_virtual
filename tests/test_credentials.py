"""
Tests para el módulo de credenciales.
Verifica el fallback a variables de entorno cuando keyring no está disponible.
"""
import os
import pytest
from unittest.mock import patch

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestGetEmailPassword:

    @patch.dict(os.environ, {"EMAIL_PASS": "mi_password"})
    @patch("modules.credentials.KEYRING_AVAILABLE", False)
    def test_fallback_a_env(self):
        from modules.credentials import get_email_password
        result = get_email_password("user@test.com")
        assert result == "mi_password"

    @patch.dict(os.environ, {}, clear=True)
    @patch("modules.credentials.KEYRING_AVAILABLE", False)
    def test_sin_credenciales_lanza_error(self):
        # Limpiar EMAIL_PASS del entorno
        os.environ.pop("EMAIL_PASS", None)
        from modules.credentials import get_email_password
        with pytest.raises(RuntimeError, match="credentials"):
            get_email_password("user@test.com")

    @patch("modules.credentials.KEYRING_AVAILABLE", True)
    @patch("modules.credentials.keyring")
    def test_keyring_disponible(self, mock_keyring):
        mock_keyring.get_password.return_value = "pwd_desde_keyring"
        from modules.credentials import get_email_password
        result = get_email_password("user@test.com")
        assert result == "pwd_desde_keyring"

    @patch("modules.credentials.KEYRING_AVAILABLE", True)
    @patch("modules.credentials.keyring")
    @patch.dict(os.environ, {"EMAIL_PASS": "pwd_env"})
    def test_keyring_vacio_usa_env(self, mock_keyring):
        mock_keyring.get_password.return_value = None
        from modules.credentials import get_email_password
        result = get_email_password("user@test.com")
        assert result == "pwd_env"
