import pytest

from motor.automatos import (
    AFD,
    AFN,
    EPSILON,
    ID_TOKEN_PADRAO,
    MAX_CODEPOINT,
    complementar_intervalos,
    formatar_intervalo,
    formatar_intervalos,
    normalizar_intervalos,
)


# -- intervalos --------------------------------------------------------------

def test_normalizar_ordena_e_funde_sobrepostos_e_adjacentes():
    assert normalizar_intervalos([(100, 120), (97, 99), (110, 130)]) == ((97, 130),)
    assert normalizar_intervalos([(5, 5), (1, 2), (3, 3)]) == ((1, 3), (5, 5))
    assert normalizar_intervalos([]) == ()


@pytest.mark.parametrize("ruim", [(5, 4), (-1, 3), (0, MAX_CODEPOINT + 1)])
def test_normalizar_rejeita_intervalo_invalido(ruim):
    with pytest.raises(ValueError):
        normalizar_intervalos([ruim])


def test_complemento():
    assert complementar_intervalos([]) == ((0, MAX_CODEPOINT),)
    assert complementar_intervalos([(0, MAX_CODEPOINT)]) == ()
    assert complementar_intervalos([(10, 10)]) == ((0, 9), (11, MAX_CODEPOINT))
    assert complementar_intervalos([(0, 9), (20, MAX_CODEPOINT)]) == ((10, 19),)


def test_complemento_duplo_volta_ao_original():
    original = ((48, 57), (65, 90), (200, 300))
    assert complementar_intervalos(complementar_intervalos(original)) == original


def test_rotulos_legiveis():
    assert formatar_intervalo((48, 57)) == "0-9"
    assert formatar_intervalo((97, 97)) == "a"
    assert formatar_intervalo((10, 10)) == "\\n"
    assert formatar_intervalos([(48, 57), (65, 90)]) == "0-9A-Z"
    assert formatar_intervalos([(0, MAX_CODEPOINT)]) == "qualquer"
    assert formatar_intervalos(complementar_intervalos([(10, 10)])) == "^\\n"


# -- AFN ---------------------------------------------------------------------

def test_afn_montado_a_mao():
    afn = AFN()
    q0, q1 = afn.novo_estado(), afn.novo_estado()
    afn.inicial = q0
    afn.adicionar_transicao(q0, (97, 97), q1)
    afn.adicionar_transicao(q0, EPSILON, q1)
    afn.aceitacao[q1] = ID_TOKEN_PADRAO

    afn.validar()
    assert afn.num_estados == 2
    assert afn.saidas(q0) == [((97, 97), q1), (None, q1)]
    assert afn.saidas(q1) == []


def test_afn_invalido():
    afn = AFN(num_estados=1)
    afn.transicoes[0] = [(None, 7)]
    with pytest.raises(ValueError):
        afn.validar()


# -- AFD ---------------------------------------------------------------------

def test_afd_mantem_transicoes_ordenadas_e_guarda_estados_do_afn():
    afd = AFD()
    q0 = afd.novo_estado({0, 1})
    q1 = afd.novo_estado({2})
    afd.adicionar_transicao(q0, (97, 122), q1)
    afd.adicionar_transicao(q0, (48, 57), q1)
    afd.aceitacao[q1] = 3

    afd.validar()
    assert afd.saidas(q0) == [((48, 57), q1), ((97, 122), q1)]
    assert afd.estados_afn == {q0: frozenset({0, 1}), q1: frozenset({2})}
    assert afd.saidas(q1) == []  # parcial: sem transição = travou


def test_afd_recusa_intervalos_sobrepostos():
    afd = AFD()
    q0 = afd.novo_estado()
    afd.adicionar_transicao(q0, (97, 109), q0)
    with pytest.raises(ValueError):
        afd.adicionar_transicao(q0, (104, 122), q0)


def test_afd_validar_detecta_epsilon_e_desordem():
    afd = AFD(num_estados=1, transicoes={0: [(None, 0)]})
    with pytest.raises(ValueError):
        afd.validar()
    afd = AFD(num_estados=1, transicoes={0: [((50, 60), 0), ((10, 20), 0)]})
    with pytest.raises(ValueError):
        afd.validar()
