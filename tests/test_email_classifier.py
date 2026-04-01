"""
Tests unitarios para el clasificador de correos.
Usa mocks para no depender de Ollama ni de la BD real.
"""
import json
import pytest
from unittest.mock import patch, MagicMock

# Ajustar path para importar desde la raíz del proyecto
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.email_classifier import (
    _parse_batch_response,
    CATEGORIES,
)


class TestParseBatchResponse:

    def test_respuesta_valida(self):
        response = json.dumps({
            "resultados": [
                {"id": "id1", "categoria": "urgente"},
                {"id": "id2", "categoria": "spam"},
            ]
        })
        result = _parse_batch_response(response, ["id1", "id2"])
        assert result["id1"] == "urgente"
        assert result["id2"] == "spam"

    def test_categoria_invalida_fallback_informativo(self):
        response = json.dumps({
            "resultados": [
                {"id": "id1", "categoria": "desconocida"},
            ]
        })
        result = _parse_batch_response(response, ["id1"])
        assert result["id1"] == "informativo"

    def test_id_faltante_recibe_fallback(self):
        response = json.dumps({
            "resultados": [
                {"id": "id1", "categoria": "urgente"},
            ]
        })
        # id2 no viene en la respuesta
        result = _parse_batch_response(response, ["id1", "id2"])
        assert result["id1"] == "urgente"
        assert result["id2"] == "informativo"

    def test_json_con_texto_extra(self):
        # El LLM a veces agrega texto antes/después del JSON
        response = 'Aqui esta el resultado: {"resultados": [{"id": "id1", "categoria": "importante"}]} fin.'
        result = _parse_batch_response(response, ["id1"])
        assert result["id1"] == "importante"

    def test_sin_json_lanza_error(self):
        with pytest.raises(ValueError):
            _parse_batch_response("sin json aqui", ["id1"])

    def test_categoria_en_mayusculas_normalizada(self):
        response = json.dumps({
            "resultados": [
                {"id": "id1", "categoria": "URGENTE"},
            ]
        })
        result = _parse_batch_response(response, ["id1"])
        assert result["id1"] == "urgente"

    def test_todas_las_categorias_validas(self):
        resultados = [{"id": f"id{i}", "categoria": cat} for i, cat in enumerate(CATEGORIES)]
        response = json.dumps({"resultados": resultados})
        ids = [f"id{i}" for i in range(len(CATEGORIES))]
        result = _parse_batch_response(response, ids)
        for i, cat in enumerate(CATEGORIES):
            assert result[f"id{i}"] == cat
