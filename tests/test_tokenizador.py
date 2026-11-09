"""Contratos da Task 2 e busca em texto, sem substituir seus algoritmos."""

import sys
from types import ModuleType

import pytest

from motor.automatos import AFD, AFN, EPSILON
from motor.padroes import PADROES, Padrao
from motor.parser import parse
from motor.tokenizador import Token, Tokenizador
from tests.referencia import _fins


TEXTO = (
    "Oi, sou a Maria. Meu CPF é 123.456.789-09 e meu email é maria.silva@gmail.com. "
    "Me liga: (83) 98765-4321. Paguei R$ 1.234,56 no dia 03/11/2026. "
    "Veja https://exemplo.com.br #promoção @loja_oficial"
)
ESPERADOS = [
    Token("CPF", "123.456.789-09", 27, 41),
    Token("EMAIL", "maria.silva@gmail.com", 56, 77),
    Token("TELEFONE", "(83) 98765-4321", 88, 103),
    Token("VALOR", "R$ 1.234,56", 112, 123),
    Token("DATA", "03/11/2026", 131, 141),
    Token("URL", "https://exemplo.com.br", 148, 170),
    Token("HASHTAG", "#promoção", 171, 180),
    Token("MENCAO", "@loja_oficial", 181, 194),
]


@pytest.fixture
def tokenizador_ast(monkeypatch):
    """Isola a varredura usando o oráculo de AST já existente nos testes."""
    def criar(padroes=PADROES):
        tokenizador = Tokenizador.__new__(Tokenizador)
        tokenizador.padroes = tuple(padroes)
        tokenizador.afd = AFD()
        arvores = [parse(p.expressao) for p in tokenizador.padroes]

        def casamento(afd, texto, inicio):
            candidatos = [
                (fim, id_token)
                for id_token, arvore in enumerate(arvores)
                for fim in _fins(arvore, texto, frozenset([inicio]))
            ]
            return max(candidatos, key=lambda c: (c[0], -c[1]), default=None)

        monkeypatch.setattr("motor.tokenizador.maior_casamento", casamento)
        return tokenizador
    return criar


def test_tokens_exatos_do_exemplo_com_oraculo_ast(tokenizador_ast):
    tokens = tokenizador_ast().tokenizar(TEXTO)
    assert tokens == ESPERADOS
    assert all(TEXTO[t.inicio:t.fim] == t.texto for t in tokens)


@pytest.mark.parametrize("texto, esperado", [
    ("83987654321", [("CPF", "83987654321")]),
    ("8332211234", [("TELEFONE", "8332211234")]),
    ("98765-4321", []),
    ("58000-000", [("CEP", "58000-000")]),
    ("123456789012", []),
    ("R$ 10,505", []),
    ("a@b.com.", [("EMAIL", "a@b.com")]),
    ("(https://a.com)", [("URL", "https://a.com")]),
    ("158000-000", []),
    ("58000-000²", []),
    ("", []),
    ("sem dados", []),
])
def test_comportamentos_da_busca_com_oraculo_ast(tokenizador_ast, texto, esperado):
    assert [(t.tipo, t.texto) for t in tokenizador_ast().tokenizar(texto)] == esperado


def test_personalizado_prioridade_vazio_e_maior_comprimento(tokenizador_ast):
    padroes = [Padrao("PERSONALIZADO", r"a*|\d{11}"), *PADROES]
    tokens = tokenizador_ast(padroes).tokenizar("!83987654321 a@b.com")
    assert [(t.tipo, t.texto) for t in tokens] == [
        ("PERSONALIZADO", "83987654321"), ("EMAIL", "a@b.com"),
    ]
    assert tokenizador_ast([Padrao("PERSONALIZADO", "a*")]).tokenizar("!?aa!") == [
        Token("PERSONALIZADO", "aa", 2, 4),
    ]


def test_candidato_sem_fronteira_nao_tenta_outro_padrao(tokenizador_ast):
    padroes = [Padrao("CPF", "ab", True), Padrao("PERSONALIZADO", "a")]
    assert tokenizador_ast(padroes).tokenizar("ab1") == []


def test_uniao_dos_afns_e_execucao_do_afd_minimo(monkeypatch):
    chamadas = []
    combinado = []
    afd = AFD(num_estados=1)
    minimo = AFD(num_estados=3, transicoes={0: [((97, 97), 1)], 1: [((98, 98), 2)]}, aceitacao={1: 0, 2: 1})

    def construir_afn(arvore, id_token):
        chamadas.append((arvore, id_token))
        return AFN(num_estados=3, inicial=1, transicoes={1: [(EPSILON, 0)], 0: [((97 + id_token, 97 + id_token), 2)]}, aceitacao={2: id_token})

    def construir_afd(afn):
        afn.validar()
        combinado.append(afn)
        return afd

    def minimizar(entrada):
        assert entrada is afd
        return minimo

    for nome, funcao in [("thompson", construir_afn), ("subconjuntos", construir_afd), ("minimizacao", minimizar)]:
        modulo = ModuleType(f"motor.{nome}")
        setattr(modulo, funcao.__name__, funcao)
        monkeypatch.setitem(sys.modules, modulo.__name__, modulo)

    tokenizador = Tokenizador([Padrao("A", "a"), Padrao("AB", "ab")])
    assert chamadas == [(parse("a"), 0), (parse("ab"), 1)]
    afn = combinado[0]
    assert afn.num_estados == 7
    assert afn.saidas(0) == [(EPSILON, 2), (EPSILON, 5)]
    assert afn.saidas(2) == [(EPSILON, 1)]
    assert afn.saidas(5) == [(EPSILON, 4)]
    assert afn.saidas(1) == [((97, 97), 3)]
    assert afn.saidas(4) == [((98, 98), 6)]
    assert afn.aceitacao == {3: 0, 6: 1}
    assert tokenizador.afd is minimo
    assert tokenizador.tokenizar("!ab!a") == [Token("AB", "ab", 1, 3), Token("A", "a", 4, 5)]


@pytest.fixture
def pipeline_real():
    for modulo in ("motor.thompson", "motor.subconjuntos", "motor.minimizacao"):
        pytest.importorskip(modulo, reason="Integração depende da entrega da Task 2")


def test_exemplo_com_pipeline_real(pipeline_real):
    assert Tokenizador(PADROES).tokenizar(TEXTO) == ESPERADOS


def test_personalizado_e_lista_vazia_com_pipeline_real(pipeline_real):
    assert Tokenizador([]).tokenizar(TEXTO) == []
    tokenizador = Tokenizador([Padrao("PERSONALIZADO", r"a*|\d{11}"), *PADROES])
    assert tokenizador.tokenizar("!83987654321!") == [Token("PERSONALIZADO", "83987654321", 1, 12)]
