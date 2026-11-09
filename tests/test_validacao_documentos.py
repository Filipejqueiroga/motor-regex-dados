import pytest

from motor.tokenizador import Token
from validacao_documentos import validar_documentos


@pytest.mark.parametrize("tipo, texto, esperado", [
    ("CPF", "123.456.789-09", True),
    ("CPF", "12345678909", True),
    ("CPF", "123.456.789-00", False),
    ("CPF", "111.111.111-11", False),
    ("CPF", "00000000000", False),
    ("CPF", "123", False),
    ("CNPJ", "12.345.678/0001-95", True),
    ("CNPJ", "04.252.011/0001-10", True),
    ("CNPJ", "12.345.678/0001-00", False),
    ("CNPJ", "00.000.000/0000-00", False),
    ("CNPJ", "11.111.111/1111-11", False),
    ("CNPJ", "123", False),
    ("EMAIL", "a@b.com", None),
])
def test_validacao_preserva_tokens(tipo, texto, esperado):
    token = Token(tipo, texto, 0, len(texto))
    tokens = [token]
    assert validar_documentos(tokens) is tokens
    assert tokens == [Token(tipo, texto, 0, len(texto), esperado)]
    assert tokens[0] is token


def test_lista_vazia():
    assert validar_documentos([]) == []
