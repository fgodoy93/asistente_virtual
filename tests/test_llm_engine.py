"""
Tests unitarios para el motor LLM (llm_engine.py).
Verifica reintentos, backoff y manejo de errores sin llamar a Ollama real.
"""
import pytest
from unittest.mock import patch, MagicMock, call
import requests

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.llm_engine import ask_llm, check_ollama_available, MAX_RETRIES


class TestAskLlm:

    @patch("modules.llm_engine.requests.post")
    def test_respuesta_exitosa(self, mock_post):
        mock_post.return_value.json.return_value = {"response": "  respuesta  "}
        mock_post.return_value.raise_for_status = MagicMock()
        result = ask_llm("hola")
        assert result == "respuesta"
        mock_post.assert_called_once()

    @patch("modules.llm_engine.time.sleep")
    @patch("modules.llm_engine.requests.post")
    def test_reintenta_en_timeout(self, mock_post, mock_sleep):
        # Los primeros 2 intentos fallan con Timeout, el 3ro tiene éxito
        mock_post.side_effect = [
            requests.exceptions.Timeout,
            requests.exceptions.Timeout,
            MagicMock(**{
                "json.return_value": {"response": "ok"},
                "raise_for_status": MagicMock()
            })
        ]
        result = ask_llm("hola")
        assert result == "ok"
        assert mock_post.call_count == 3
        assert mock_sleep.call_count == 2

    @patch("modules.llm_engine.time.sleep")
    @patch("modules.llm_engine.requests.post")
    def test_falla_tras_max_reintentos(self, mock_post, mock_sleep):
        mock_post.side_effect = requests.exceptions.Timeout
        with pytest.raises(RuntimeError, match="intentos"):
            ask_llm("hola")
        assert mock_post.call_count == MAX_RETRIES

    @patch("modules.llm_engine.requests.post")
    def test_error_conexion_no_reintenta(self, mock_post):
        mock_post.side_effect = requests.exceptions.ConnectionError
        with pytest.raises(RuntimeError, match="ollama serve"):
            ask_llm("hola")
        # No debe reintentar en error de conexión
        assert mock_post.call_count == 1

    @patch("modules.llm_engine.requests.post")
    def test_respuesta_limpia_espacios(self, mock_post):
        mock_post.return_value.json.return_value = {"response": "\n\n  texto  \n"}
        mock_post.return_value.raise_for_status = MagicMock()
        result = ask_llm("prompt")
        assert result == "texto"


class TestCheckOllamaAvailable:

    @patch("modules.llm_engine.requests.get")
    def test_disponible(self, mock_get):
        mock_get.return_value.status_code = 200
        assert check_ollama_available() is True

    @patch("modules.llm_engine.requests.get")
    def test_no_disponible_por_conexion(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError
        assert check_ollama_available() is False

    @patch("modules.llm_engine.requests.get")
    def test_no_disponible_por_status(self, mock_get):
        mock_get.return_value.status_code = 500
        assert check_ollama_available() is False
