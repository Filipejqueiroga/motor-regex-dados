"""Testes unitários da construção de subconjuntos (motor/subconjuntos.py)."""

import pytest

from motor.automatos import AFD, AFN, EPSILON, MAX_CODEPOINT
from motor.parser import parse
from motor.subconjuntos import construir_afd, epsilon_fecho, mover, particionar_intervalos
from motor.thompson import construir_afn


# -- epsilon_fecho -----------------------------------------------------------

def test_epsilon_fecho_vazio():
    afn = AFN(num_estados=2)
    assert epsilon_fecho(afn, []) == frozenset()
    assert epsilon_fecho([], afn) == frozenset()


def test_epsilon_fecho_sem_epsilon():
    afn = AFN(num_estados=2)
    afn.adicionar_transicao(0, (97, 97), 1)
    assert epsilon_fecho(afn, 0) == frozenset({0})
    assert epsilon_fecho(afn, [1]) == frozenset({1})


def test_epsilon_fecho_cadeia_e_ciclos():
    afn = AFN(num_estados=4)
    # Ciclo entre 0 e 1, 1 vai para 2, 2 vai para 3 por símbolo
    afn.adicionar_transicao(0, EPSILON, 1)
    afn.adicionar_transicao(1, EPSILON, 0)
    afn.adicionar_transicao(1, EPSILON, 2)
    afn.adicionar_transicao(2, (97, 97), 3)

    assert epsilon_fecho(afn, 0) == frozenset({0, 1, 2})
    assert epsilon_fecho(afn, [2]) == frozenset({2})
    # Ordem alternativa de argumentos
    assert epsilon_fecho([1], afn) == frozenset({0, 1, 2})


def test_epsilon_fecho_tipo_invalido():
    with pytest.raises(TypeError):
        epsilon_fecho(1, 2)


# -- mover -------------------------------------------------------------------

def test_mover_por_simbolo_caractere_e_codepoint():
    afn = AFN(num_estados=3)
    afn.adicionar_transicao(0, (97, 100), 1)  # 'a'-'d'
    afn.adicionar_transicao(0, (101, 105), 2)  # 'e'-'i'

    # Caractere
    assert mover(afn, 0, "a") == frozenset({1})
    assert mover(afn, [0], "e") == frozenset({2})
    assert mover(afn, 0, "z") == frozenset()

    # Code point
    assert mover(afn, 0, 97) == frozenset({1})
    assert mover(afn, [0], 102) == frozenset({2})

    # Intervalo contido
    assert mover(afn, 0, (97, 99)) == frozenset({1})

    # Ordem invertida de argumentos: mover(estados, intervalo, afn)
    assert mover([0], "b", afn) == frozenset({1})


def test_mover_ignora_epsilon():
    afn = AFN(num_estados=2)
    afn.adicionar_transicao(0, EPSILON, 1)
    assert mover(afn, 0, "a") == frozenset()


def test_mover_erros_de_tipo():
    afn = AFN(num_estados=1)
    with pytest.raises(TypeError):
        mover(1, 2, 3)
    with pytest.raises(ValueError):
        mover(afn, 0, "abc")
    with pytest.raises(ValueError):
        mover(afn, 0, (10, 20, 30))


# -- particionar_intervalos -------------------------------------------------

def test_particionar_intervalos_sobrepostos_exemplo_especificacao():
    # [a-m]|[h-z]
    # 'a'=97, 'm'=109, 'h'=104, 'z'=122
    intervalos = [(ord("a"), ord("m")), (ord("h"), ord("z"))]
    resultado = particionar_intervalos(intervalos)
    esperado = [
        (ord("a"), ord("g")),  # 97..103
        (ord("h"), ord("m")),  # 104..109
        (ord("n"), ord("z")),  # 110..122
    ]
    assert resultado == esperado


def test_particionar_intervalos_disjuntos_e_lacuna():
    intervalos = [(10, 20), (30, 40)]
    # A lacuna 21..29 não deve aparecer
    assert particionar_intervalos(intervalos) == [(10, 20), (30, 40)]


def test_particionar_intervalos_aninhados():
    intervalos = [(10, 50), (20, 30)]
    assert particionar_intervalos(intervalos) == [(10, 19), (20, 30), (31, 50)]


def test_particionar_intervalos_identicos_e_vazios():
    assert particionar_intervalos([]) == []
    assert particionar_intervalos([(10, 20), (10, 20)]) == [(10, 20)]


def test_particionar_intervalos_limites_extremos():
    intervalos = [(0, 5), (MAX_CODEPOINT - 3, MAX_CODEPOINT)]
    resultado = particionar_intervalos(intervalos)
    assert resultado == [(0, 5), (MAX_CODEPOINT - 3, MAX_CODEPOINT)]


# -- construir_afd -----------------------------------------------------------

def test_construir_afd_arvore_simples():
    arvore = parse("ab")
    afn = construir_afn(arvore, id_token=0)
    afd = construir_afd(afn)
    afd.validar()
    assert afd.num_estados >= 3
    # Verifica que estados_afn foi preenchido
    assert len(afd.estados_afn) == afd.num_estados
    assert all(isinstance(s, frozenset) for s in afd.estados_afn.values())


def test_construir_afd_fusao_de_intervalos_adjacentes():
    # AFN com duas transições adjacentes que levam ao mesmo destino
    afn = AFN(num_estados=3, inicial=0, aceitacao={2: 0})
    afn.adicionar_transicao(0, (ord("0"), ord("4")), 2)
    afn.adicionar_transicao(0, (ord("5"), ord("9")), 2)
    afn.validar()

    afd = construir_afd(afn)
    afd.validar()
    # No AFD, (48, 52) e (53, 57) devem ser fundidos em (48, 57) '0-9'
    saidas = afd.saidas(afd.inicial)
    assert len(saidas) == 1
    assert saidas[0][0] == (ord("0"), ord("9"))


def test_construir_afd_prioridade_menor_id_token():
    # Dois caminhos aceitando a mesma cadeia "a", com id_token 1 e 0
    afn = AFN(num_estados=3, inicial=0)
    afn.adicionar_transicao(0, (ord("a"), ord("a")), 1)
    afn.adicionar_transicao(0, (ord("a"), ord("a")), 2)
    afn.aceitacao[1] = 10
    afn.aceitacao[2] = 2  # menor id_token vence
    afn.validar()

    afd = construir_afd(afn)
    afd.validar()
    destino = afd.saidas(afd.inicial)[0][1]
    assert afd.aceitacao[destino] == 2


def test_construir_afd_parcial_sem_estado_morto():
    # Padrão "a": qualquer caractere != 'a' não tem transição
    arvore = parse("a")
    afn = construir_afn(arvore)
    afd = construir_afd(afn)
    afd.validar()
    # Estado inicial só tem transição para 'a'
    saidas_0 = afd.saidas(afd.inicial)
    assert len(saidas_0) == 1
    assert saidas_0[0][0] == (ord("a"), ord("a"))
    # Estado de aceitação não tem transição (não há estado de erro)
    estado_aceitacao = saidas_0[0][1]
    assert afd.saidas(estado_aceitacao) == []


def test_construir_afd_com_intervalos_sobrepostos():
    arvore = parse("[a-m]|[h-z]")
    afn = construir_afn(arvore)
    afd = construir_afd(afn)
    afd.validar()
    # No AFD (antes da minimização), os destinos são subconjuntos distintos:
    # 'a'-'g' leva ao fim do ramo esquerdo
    # 'h'-'m' leva a ambos os fins (interseção)
    # 'n'-'z' leva ao fim do ramo direito
    saidas = afd.saidas(afd.inicial)
    assert len(saidas) == 3
    assert saidas[0][0] == (ord("a"), ord("g"))
    assert saidas[1][0] == (ord("h"), ord("m"))
    assert saidas[2][0] == (ord("n"), ord("z"))
    d1, d2, d3 = saidas[0][1], saidas[1][1], saidas[2][1]
    assert len({d1, d2, d3}) == 3  # 3 estados distintos no AFD

    # E na minimização, como os três estados são de aceitação equivalentes,
    # os três intervalos adjacentes são fundidos em um único [a-z]!
    from motor.minimizacao import minimizar
    min_afd = minimizar(afd)
    min_saidas = min_afd.saidas(min_afd.inicial)
    assert min_saidas == [((ord("a"), ord("z")), min_saidas[0][1])]
