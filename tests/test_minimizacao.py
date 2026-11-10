"""Testes unitários da minimização de AFD (motor/minimizacao.py)."""

import pytest

from motor.automatos import AFD
from motor.minimizacao import minimizar
from motor.parser import parse
from motor.simulador import aceita
from motor.subconjuntos import construir_afd
from motor.thompson import construir_afn


def test_remover_estados_inalcancaveis():
    afd = AFD()
    q0 = afd.novo_estado({0})
    q1 = afd.novo_estado({1})
    q_inalcancavel = afd.novo_estado({99})

    afd.inicial = q0
    afd.adicionar_transicao(q0, (ord("a"), ord("a")), q1)
    afd.adicionar_transicao(q_inalcancavel, (ord("b"), ord("b")), q1)
    afd.aceitacao[q1] = 0
    afd.aceitacao[q_inalcancavel] = 0
    afd.validar()

    min_afd = minimizar(afd)
    min_afd.validar()
    assert min_afd.num_estados == 2
    assert aceita(min_afd, "a")
    assert not aceita(min_afd, "b")


def test_remover_estados_nao_produtivos():
    # q0 -> q1 (aceitação), q0 -> q_morto (sem saída, não aceita)
    afd = AFD()
    q0 = afd.novo_estado({0})
    q1 = afd.novo_estado({1})
    q_morto = afd.novo_estado({2})

    afd.inicial = q0
    afd.adicionar_transicao(q0, (ord("a"), ord("a")), q1)
    afd.adicionar_transicao(q0, (ord("b"), ord("b")), q_morto)
    afd.aceitacao[q1] = 0
    afd.validar()

    min_afd = minimizar(afd)
    min_afd.validar()
    assert min_afd.num_estados == 2
    # Transição para q_morto foi eliminada no AFD parcial
    assert min_afd.saidas(min_afd.inicial) == [((ord("a"), ord("a")), 1)]


def test_particao_inicial_separa_por_id_token():
    # Dois estados equivalentes em transições (nenhuma saída),
    # mas com id_token diferente (0 e 1).
    afd = AFD()
    q0 = afd.novo_estado({0})
    q1 = afd.novo_estado({1})
    q2 = afd.novo_estado({2})

    afd.inicial = q0
    afd.adicionar_transicao(q0, (ord("a"), ord("a")), q1)
    afd.adicionar_transicao(q0, (ord("b"), ord("b")), q2)
    afd.aceitacao[q1] = 0
    afd.aceitacao[q2] = 1  # tokens diferentes!
    afd.validar()

    min_afd = minimizar(afd)
    min_afd.validar()
    # Não podem ser fundidos: o autômato resultante deve manter 3 estados
    assert min_afd.num_estados == 3
    # Cada estado mantém seu token respectivo
    dest_a = [dest for inter, dest in min_afd.saidas(min_afd.inicial) if inter == (ord("a"), ord("a"))][0]
    dest_b = [dest for inter, dest in min_afd.saidas(min_afd.inicial) if inter == (ord("b"), ord("b"))][0]
    assert dest_a != dest_b
    assert min_afd.aceitacao[dest_a] == 0
    assert min_afd.aceitacao[dest_b] == 1


def test_fusao_de_estados_equivalentes():
    # Dois estados com o mesmo token e mesmas transições devem ser fundidos.
    afd = AFD()
    q0 = afd.novo_estado({0})
    q1 = afd.novo_estado({1})
    q2 = afd.novo_estado({2})

    afd.inicial = q0
    afd.adicionar_transicao(q0, (ord("a"), ord("a")), q1)
    afd.adicionar_transicao(q0, (ord("b"), ord("b")), q2)
    afd.aceitacao[q1] = 0
    afd.aceitacao[q2] = 0  # mesmo token!
    afd.validar()

    min_afd = minimizar(afd)
    min_afd.validar()
    # q1 e q2 devem ser fundidos em um único estado de aceitação
    assert min_afd.num_estados == 2
    saidas = min_afd.saidas(min_afd.inicial)
    # Como 'a' e 'b' são adjacentes (97 e 98) e agora levam ao mesmo estado, fundem-se em 'a-b'!
    assert saidas == [((ord("a"), ord("b")), 1)]
    assert min_afd.aceitacao[1] == 0


def test_automato_ja_minimo_nao_altera_numero_de_estados():
    arvore = parse("ab")
    afd = construir_afd(construir_afn(arvore))
    min_afd = minimizar(afd)
    min_afd.validar()
    assert min_afd.num_estados == afd.num_estados


def test_afd_minimo_nunca_tem_mais_estados_que_original():
    padroes = ["a|b", "(a|b)*abb", "a{2,4}", "[a-z]+[0-9]*"]
    for p in padroes:
        arvore = parse(p)
        afd = construir_afd(construir_afn(arvore))
        min_afd = minimizar(afd)
        assert min_afd.num_estados <= afd.num_estados


def test_linguagem_vazia_retorna_afd_com_um_estado():
    # AFD sem estados de aceitação
    afd = AFD(num_estados=2, inicial=0, transicoes={0: [((97, 97), 1)]})
    afd.validar()
    min_afd = minimizar(afd)
    min_afd.validar()
    assert min_afd.num_estados == 1
    assert min_afd.inicial == 0
    assert min_afd.aceitacao == {}
    assert min_afd.saidas(0) == []
    assert not aceita(min_afd, "")
    assert not aceita(min_afd, "a")


def test_preserva_estados_afn():
    afd = AFD()
    q0 = afd.novo_estado({1, 2})
    q1 = afd.novo_estado({3})
    q2 = afd.novo_estado({4})

    afd.inicial = q0
    afd.adicionar_transicao(q0, (97, 97), q1)
    afd.adicionar_transicao(q0, (98, 98), q2)
    afd.aceitacao[q1] = 0
    afd.aceitacao[q2] = 0
    afd.validar()

    min_afd = minimizar(afd)
    min_afd.validar()
    # O estado fundido deve conter a união {3, 4}
    assert min_afd.estados_afn[0] == frozenset({1, 2})
    assert min_afd.estados_afn[1] == frozenset({3, 4})
