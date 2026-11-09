import pytest

from motor.automatos import AFD
from motor.simulador import aceita, maior_casamento, passos


@pytest.fixture
def afd():
    return AFD(
        num_estados=4,
        transicoes={0: [((97, 97), 1)], 1: [((98, 98), 2)], 2: [((99, 99), 3)]},
        aceitacao={1: 0, 3: 1},
    )


@pytest.mark.parametrize("cadeia, esperado", [("a", True), ("abc", True), ("ab", False), ("", False), ("abcd", False)])
def test_aceita_cadeia_inteira(afd, cadeia, esperado):
    assert aceita(afd, cadeia) is esperado


def test_maior_casamento_volta_a_ultima_aceitacao(afd):
    assert maior_casamento(afd, "xab!", 1) == (2, 0)
    assert maior_casamento(afd, "xabc!", 1) == (4, 1)
    assert maior_casamento(afd, "ab", 0) == (1, 0)
    assert maior_casamento(afd, "x", 0) is None
    assert maior_casamento(afd, "", 0) is None


def test_aceitacao_vazia_e_estado_zero():
    afd = AFD(num_estados=1, transicoes={0: [((48, 57), 0)]}, aceitacao={0: 0})
    assert aceita(afd, "")
    assert aceita(afd, "0129")
    assert not aceita(afd, "/")
    assert not aceita(afd, ":")
    assert maior_casamento(afd, "x", 0) == (0, 0)
    assert maior_casamento(afd, "", 0) == (0, 0)


def test_passos_incluem_travamento(afd):
    assert passos(afd, "abxresto") == [(0, "a", 1), (1, "b", 2), (2, "x", None)]
    assert passos(afd, "abc") == [(0, "a", 1), (1, "b", 2), (2, "c", 3)]
    assert passos(afd, "") == []


def test_busca_em_intervalos_disjuntos_unicode():
    afd = AFD(num_estados=2, transicoes={0: [((48, 57), 1), ((97, 122), 1), ((231, 231), 1)]}, aceitacao={1: 0})
    for simbolo in "09azç":
        assert aceita(afd, simbolo)
    for simbolo in "/:Z{æè":
        assert not aceita(afd, simbolo)


@pytest.mark.parametrize("inicio", [-1, 2])
def test_inicio_fora_do_texto(afd, inicio):
    with pytest.raises(ValueError):
        maior_casamento(afd, "a", inicio)
