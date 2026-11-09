"""Contratos da Task 2 e busca em texto, sem substituir seus algoritmos."""

import json
import sys
from importlib import import_module
from importlib.util import find_spec
from types import ModuleType

import pytest

from motor.automatos import AFD, AFN, EPSILON
from motor.exportador import exportar_json
from motor.padroes import PADROES, Padrao
from motor.parser import parse
from motor.sanitizador import sanitizar
from motor.tokenizador import Token, Tokenizador
from tests.referencia import _fins
from validacao_documentos import validar_documentos


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


@pytest.fixture(params=["ast", "afd"])
def criar_tokenizador(request, monkeypatch):
    """Executa os mesmos casos com o oráculo e com o pipeline real disponível."""
    if request.param == "afd":
        request.getfixturevalue("pipeline_real")
        return lambda padroes=PADROES: Tokenizador(padroes)

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


def test_tokens_exatos_do_exemplo(criar_tokenizador):
    tokens = criar_tokenizador().tokenizar(TEXTO)
    assert tokens == ESPERADOS
    assert all(TEXTO[t.inicio:t.fim] == t.texto for t in tokens)


def test_resultados_consumidos_pela_interface(criar_tokenizador):
    tokens = validar_documentos(criar_tokenizador().tokenizar(TEXTO))
    assert tokens[0].digitos_validos is True
    assert all(t.digitos_validos is None for t in tokens[1:])
    assert sanitizar(TEXTO, tokens, {}) == (
        "Oi, sou a Maria. Meu CPF é [CPF] e meu email é [EMAIL]. "
        "Me liga: [TELEFONE]. Paguei [VALOR] no dia [DATA]. "
        "Veja [URL] [HASHTAG] [MENCAO]"
    )
    dados = json.loads(exportar_json(tokens))
    assert dados["CPF"] == [{
        "texto": "123.456.789-09", "inicio": 27, "fim": 41, "digitos_validos": True,
    }]
    assert dados["HASHTAG"] == [{"texto": "#promoção", "inicio": 171, "fim": 180}]
    assert len(dados) == 8


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
def test_comportamentos_da_busca(criar_tokenizador, texto, esperado):
    assert [(t.tipo, t.texto) for t in criar_tokenizador().tokenizar(texto)] == esperado


def test_personalizado_prioridade_vazio_e_maior_comprimento(criar_tokenizador):
    padroes = [Padrao("PERSONALIZADO", r"a*|\d{11}"), *PADROES]
    tokens = criar_tokenizador(padroes).tokenizar("!83987654321 a@b.com")
    assert [(t.tipo, t.texto) for t in tokens] == [
        ("PERSONALIZADO", "83987654321"), ("EMAIL", "a@b.com"),
    ]
    assert criar_tokenizador([Padrao("PERSONALIZADO", "a*")]).tokenizar("!?aa!") == [
        Token("PERSONALIZADO", "aa", 2, 4),
    ]


def test_candidato_sem_fronteira_nao_tenta_outro_padrao(criar_tokenizador):
    padroes = [Padrao("CPF", "ab", True), Padrao("PERSONALIZADO", "a")]
    assert criar_tokenizador(padroes).tokenizar("ab1") == []


@pytest.mark.parametrize("texto, esperado", [
    ("!83987654321!", [Token("CPF", "83987654321", 1, 12)]),
    ("8332211234", [Token("TELEFONE", "8332211234", 0, 10)]),
    ("123456789012", []),
    ("98765-4321", []),
    ("158000-000", []),
    ("58000-000²", []),
    ("!58000-000!", [Token("CEP", "58000-000", 1, 10)]),
    ("58000-000 8332211234", [
        Token("CEP", "58000-000", 0, 9),
        Token("TELEFONE", "8332211234", 10, 20),
    ]),
])
def test_busca_com_simulador_e_afd_manual(texto, esperado):
    """AFD parcial para telefone sem pontuação, CPF sem pontuação e CEP."""
    afd = AFD(num_estados=16, aceitacao={10: 4, 11: 1, 15: 5})
    for estado in range(11):
        afd.adicionar_transicao(estado, (48, 57), estado + 1)
    afd.adicionar_transicao(5, (45, 45), 12)
    for estado in range(12, 15):
        afd.adicionar_transicao(estado, (48, 57), estado + 1)
    afd.validar()
    tokenizador = Tokenizador.__new__(Tokenizador)
    tokenizador.padroes = PADROES
    tokenizador.afd = afd
    assert tokenizador.tokenizar(texto) == esperado


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

    personalizado = Padrao("PERSONALIZADO", "a", True)
    primeiro = Padrao("A", "b", True)
    segundo = Padrao("B", "c")
    tokenizador = Tokenizador(iter([primeiro, segundo, personalizado]))
    assert tokenizador.padroes == (Padrao("PERSONALIZADO", "a"), primeiro, segundo)
    assert tokenizador.tokenizar("1a2") == [Token("PERSONALIZADO", "a", 1, 2)]
    assert personalizado.fronteira_numerica is True


@pytest.fixture
def pipeline_real():
    modulos = ("motor.thompson", "motor.subconjuntos", "motor.minimizacao")
    ausentes = [modulo for modulo in modulos if find_spec(modulo) is None]
    if ausentes:
        pytest.skip("Integração depende da Task 2: " + ", ".join(ausentes))
    for modulo in modulos:
        import_module(modulo)


def test_personalizado_e_lista_vazia_com_pipeline_real(pipeline_real):
    assert Tokenizador([]).tokenizar(TEXTO) == []
    tokenizador = Tokenizador([*PADROES, Padrao("PERSONALIZADO", r"a*|\d{11}", True)])
    assert tokenizador.tokenizar("!83987654321!") == [Token("PERSONALIZADO", "83987654321", 1, 12)]
    assert tokenizador.tokenizar("1a2") == [Token("PERSONALIZADO", "a", 1, 2)]
