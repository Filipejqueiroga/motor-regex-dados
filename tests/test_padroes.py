import pytest

from motor.padroes import PADROES
from motor.parser import parse
from tests.referencia import casa


@pytest.mark.parametrize("nome, aceitos, rejeitados", [
    ("CNPJ", ["12.345.678/0001-95"], ["12345678000195", "12.345.678/0001-9"]),
    ("CPF", ["123.456.789-09", "12345678909"], ["123456789012", "123.456.789-0"]),
    ("EMAIL", ["a@b.com", "maria.silva@gmail.com"], ["a@b", "a@b.com."]),
    ("URL", ["http://a.com", "https://exemplo.com.br"], ["ftp://a.com", "https://a.com)"]),
    ("TELEFONE", ["(83) 98765-4321", "83 3221-1234", "8332211234"], ["98765-4321", "(83) 87654-3210"]),
    ("CEP", ["58000-000"], ["58000000", "58000-0000"]),
    ("DATA", ["03/11/2026", "99/99/0000"], ["3/11/2026", "2026-11-03"]),
    ("VALOR", ["R$ 1.234,56", "R$10", "R$ 1234,56"], ["10,50", "R$ 10,505"]),
    ("HASHTAG", ["#promoção", "#ação_123"], ["#", "#duas palavras"]),
    ("MENCAO", ["@loja_oficial", "@ação"], ["@", "@loja-oficial"]),
])
def test_formatos(nome, aceitos, rejeitados):
    padrao = next(p for p in PADROES if p.nome == nome)
    arvore = parse(padrao.expressao)
    for texto in aceitos:
        assert casa(arvore, texto), texto
    for texto in rejeitados:
        assert not casa(arvore, texto), texto


def test_prioridade_e_fronteiras():
    assert [p.nome for p in PADROES] == [
        "CNPJ", "CPF", "EMAIL", "URL", "TELEFONE", "CEP", "DATA", "VALOR", "HASHTAG", "MENCAO",
    ]
    assert {p.nome for p in PADROES if p.fronteira_numerica} == {
        "CNPJ", "CPF", "TELEFONE", "CEP", "DATA", "VALOR",
    }
