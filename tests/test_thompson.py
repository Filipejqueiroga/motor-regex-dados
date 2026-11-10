"""Testes unitários da construção de Thompson (motor/thompson.py)."""

import pytest

from motor.arvore import Classe, Concat, Estrela, No, Uniao, Vazio
from motor.automatos import AFN, EPSILON
from motor.parser import parse
from motor.thompson import construir_afn


def test_construir_afn_vazio():
    afn = construir_afn(Vazio(), id_token=42)
    afn.validar()
    assert afn.num_estados == 2
    assert afn.inicial == 0
    assert afn.aceitacao == {1: 42}
    assert afn.saidas(0) == [(EPSILON, 1)]
    assert afn.saidas(1) == []


def test_construir_afn_classe_literal():
    arvore = Classe.literal("x")
    afn = construir_afn(arvore, id_token=5)
    afn.validar()
    assert afn.num_estados == 2
    assert afn.inicial == 0
    assert afn.aceitacao == {1: 5}
    assert afn.saidas(0) == [((ord("x"), ord("x")), 1)]
    assert afn.saidas(1) == []


def test_construir_afn_classe_multiplos_intervalos():
    arvore = parse("[a-c0-1]")
    afn = construir_afn(arvore)
    afn.validar()
    assert afn.num_estados == 2
    assert afn.inicial == 0
    saidas = afn.saidas(0)
    # Espera intervalos ordenados pelas regras de Classe
    assert ( (ord("0"), ord("1")), 1 ) in saidas
    assert ( (ord("a"), ord("c")), 1 ) in saidas


def test_construir_afn_classe_vazia():
    arvore = Classe(())
    afn = construir_afn(arvore)
    afn.validar()
    assert afn.num_estados == 2
    assert afn.inicial == 0
    assert afn.saidas(0) == []
    assert afn.aceitacao == {1: 0}


def test_construir_afn_concat():
    arvore = Concat(Classe.literal("a"), Classe.literal("b"))
    afn = construir_afn(arvore, id_token=1)
    afn.validar()
    assert afn.num_estados == 4
    assert afn.inicial == 0
    assert afn.aceitacao == {3: 1}
    # esq: 0 -> 1 por 'a'
    # dir: 2 -> 3 por 'b'
    # concat: 1 -> 2 por ε
    assert afn.saidas(0) == [((ord("a"), ord("a")), 1)]
    assert afn.saidas(1) == [(EPSILON, 2)]
    assert afn.saidas(2) == [((ord("b"), ord("b")), 3)]
    assert afn.saidas(3) == []


def test_construir_afn_uniao():
    arvore = Uniao(Classe.literal("a"), Classe.literal("b"))
    afn = construir_afn(arvore, id_token=2)
    afn.validar()
    assert afn.num_estados == 6
    assert afn.inicial == 0
    assert afn.aceitacao == {5: 2}
    # novo_inicio: 0 -> esq_inicio(1) e dir_inicio(3)
    saidas_0 = afn.saidas(0)
    assert (EPSILON, 1) in saidas_0
    assert (EPSILON, 3) in saidas_0
    # esq_fim(2) e dir_fim(4) -> novo_fim(5)
    assert afn.saidas(2) == [(EPSILON, 5)]
    assert afn.saidas(4) == [(EPSILON, 5)]


def test_construir_afn_estrela():
    arvore = Estrela(Classe.literal("a"))
    afn = construir_afn(arvore, id_token=3)
    afn.validar()
    assert afn.num_estados == 4
    assert afn.inicial == 0
    assert afn.aceitacao == {3: 3}
    # novo_inicio(0) -> entrar(1) e pular(3)
    saidas_0 = afn.saidas(0)
    assert (EPSILON, 1) in saidas_0
    assert (EPSILON, 3) in saidas_0
    # sub_fim(2) -> repetir(1) e sair(3)
    saidas_2 = afn.saidas(2)
    assert (EPSILON, 1) in saidas_2
    assert (EPSILON, 3) in saidas_2


def test_estados_unicos_e_sequenciais():
    arvore = parse("(a|b)*c")
    afn = construir_afn(arvore)
    afn.validar()
    estados_usados = {afn.inicial} | set(afn.aceitacao.keys())
    for origem, saidas in afn.transicoes.items():
        estados_usados.add(origem)
        for _, destino in saidas:
            estados_usados.add(destino)
    assert estados_usados == set(range(afn.num_estados))


def test_arvore_profunda_desbalanceada_nao_estoura_recursao():
    # Monta uma árvore desbalanceada com profundidade 2500
    no = Classe.literal("a")
    for _ in range(2500):
        no = Concat(no, Classe.literal("a"))
    afn = construir_afn(no)
    afn.validar()
    assert afn.num_estados == 2501 * 2


def test_padrao_repeticao_longo():
    arvore = parse("a{1000}")
    afn = construir_afn(arvore)
    afn.validar()
    assert len(afn.aceitacao) == 1


def test_no_invalido_levanta_type_error():
    class NoInvalido(No):
        pass

    with pytest.raises(TypeError, match="Nó da AST não suportado"):
        construir_afn(NoInvalido())
