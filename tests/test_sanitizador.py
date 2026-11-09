import pytest

from motor.sanitizador import sanitizar
from motor.tokenizador import Token
from validacao_documentos import validar_documentos


@pytest.mark.parametrize("regra, esperado", [
    ("rotulo", "CPF: [CPF]!"),
    ("mascarar", "CPF: **************!"),
    ("remover", "CPF: !"),
    ("manter", "CPF: 123.456.789-09!"),
])
def test_quatro_regras(regra, esperado):
    texto = "CPF: 123.456.789-09!"
    tokens = [Token("CPF", texto[5:19], 5, 19)]
    assert sanitizar(texto, tokens, {"CPF": regra}) == esperado


def test_regras_por_tipo_e_preservacao_dos_trechos():
    texto = "ação: #a\n@b fim"
    tokens = [Token("HASHTAG", "#a", 6, 8), Token("MENCAO", "@b", 9, 11)]
    assert sanitizar(texto, tokens, {"HASHTAG": "remover"}) == "ação: \n[MENCAO] fim"
    assert tokens == [Token("HASHTAG", "#a", 6, 8), Token("MENCAO", "@b", 9, 11)]


def test_tokens_adjacentes_e_nas_extremidades():
    tokens = [Token("HASHTAG", "#a", 0, 2), Token("MENCAO", "@b", 2, 4)]
    assert sanitizar("#a@b", tokens, {}) == "[HASHTAG][MENCAO]"


def test_documentos_invalidos_continuam_sanitizados():
    texto = "123.456.789-00 11.111.111/1111-11"
    tokens = validar_documentos([
        Token("CPF", texto[:14], 0, 14), Token("CNPJ", texto[15:], 15, len(texto)),
    ])
    assert all(t.digitos_validos is False for t in tokens)
    assert sanitizar(texto, tokens, {}) == "[CPF] [CNPJ]"


@pytest.mark.parametrize("texto", ["", "texto sem dados\n"])
def test_sem_tokens(texto):
    assert sanitizar(texto, [], {}) == texto


def test_regra_invalida():
    with pytest.raises(ValueError, match="regra de sanitização inválida"):
        sanitizar("#a", [Token("HASHTAG", "#a", 0, 2)], {"HASHTAG": "outra"})
