import json

from motor.exportador import exportar_json
from motor.tokenizador import Token
from validacao_documentos import validar_documentos


def test_json_agrupado_com_acentos_e_posicoes():
    tokens = [
        Token("HASHTAG", "#promoção", 0, 9),
        Token("MENCAO", "@loja", 10, 15),
        Token("HASHTAG", "#ação", 16, 21),
    ]
    resultado = exportar_json(tokens)
    assert "#promoção" in resultado
    assert json.loads(resultado) == {
        "HASHTAG": [{"texto": "#promoção", "inicio": 0, "fim": 9}, {"texto": "#ação", "inicio": 16, "fim": 21}],
        "MENCAO": [{"texto": "@loja", "inicio": 10, "fim": 15}],
    }


def test_validade_so_em_documentos():
    tokens = validar_documentos([
        Token("CPF", "123.456.789-09", 0, 14),
        Token("CNPJ", "12.345.678/0001-00", 15, 33),
        Token("EMAIL", "a@b.com", 34, 41),
    ])
    dados = json.loads(exportar_json(tokens))
    assert dados["CPF"][0]["digitos_validos"] is True
    assert dados["CNPJ"][0]["digitos_validos"] is False
    assert "digitos_validos" not in dados["EMAIL"][0]


def test_documento_nao_validado_e_exportado_com_null():
    dados = json.loads(exportar_json([Token("CPF", "12345678909", 0, 11)]))
    assert "digitos_validos" in dados["CPF"][0]
    assert dados["CPF"][0]["digitos_validos"] is None


def test_sem_tokens():
    assert json.loads(exportar_json([])) == {}
