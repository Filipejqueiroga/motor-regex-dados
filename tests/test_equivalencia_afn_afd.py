"""Testes de equivalência AFN × AFD (Seção 10 do projeto) e casos de borda."""

import itertools

import pytest

from motor.automatos import AFN
from motor.minimizacao import minimizar
from motor.parser import parse
from motor.simulador import aceita
from motor.subconjuntos import construir_afd, epsilon_fecho, mover
from motor.thompson import construir_afn
from tests.referencia import casa


def simular_afn(afn: AFN, cadeia: str) -> bool:
    """Simulador de AFN-ε baseado em fecho-ε e mover."""
    estados = epsilon_fecho(afn, [afn.inicial])
    for simbolo in cadeia:
        destinos = mover(afn, estados, simbolo)
        estados = epsilon_fecho(afn, destinos)
        if not estados:
            return False
    return any(q in afn.aceitacao for q in estados)


PADROES_EQUIVALENCIA = [
    "",
    "a",
    "b",
    "ab",
    "a|b",
    "a*",
    "a+",
    "a?",
    "(a*)*",
    "(a|b)*abb",
    "(a|)b",
    "a{0,3}",
    "(ab)*",
    "((a|b)c)*|c",
    "[ab]+c?",
    "[a-m]|[h-z]",
]


@pytest.mark.parametrize("padrao", PADROES_EQUIVALENCIA)
def test_equivalencia_afn_afd_minimo(padrao):
    """Equivalência exata entre AST (referência), AFN, AFD e AFD mínimo.

    Para todas as cadeias até tamanho 3 sobre o alfabeto {'a', 'b', 'c'}.
    """
    arvore = parse(padrao)
    afn = construir_afn(arvore)
    afd = construir_afd(afn)
    min_afd = minimizar(afd)

    for tamanho in range(4):
        for letras in itertools.product("abc", repeat=tamanho):
            cadeia = "".join(letras)
            res_ast = casa(arvore, cadeia)
            res_afn = simular_afn(afn, cadeia)
            res_afd = aceita(afd, cadeia)
            res_min = aceita(min_afd, cadeia)

            assert res_afn == res_ast, f"AFN diverge para '{padrao}' em '{cadeia}'"
            assert res_afd == res_ast, f"AFD diverge para '{padrao}' em '{cadeia}'"
            assert res_min == res_ast, f"Min AFD diverge para '{padrao}' em '{cadeia}'"


# -- Casos de borda ----------------------------------------------------------

def test_caso_borda_padrao_vazio():
    arvore = parse("")
    afn = construir_afn(arvore)
    afd = construir_afd(afn)
    min_afd = minimizar(afd)

    for aut in (afd, min_afd):
        assert aceita(aut, "")
        assert not aceita(aut, "a")
    assert simular_afn(afn, "")
    assert not simular_afn(afn, "a")


def test_caso_borda_estrela_aninhada():
    # (a*)* aceita cadeia vazia e qualquer quantidade de 'a's
    arvore = parse("(a*)*")
    afn = construir_afn(arvore)
    afd = construir_afd(afn)
    min_afd = minimizar(afd)

    for aut in (afd, min_afd):
        assert aceita(aut, "")
        assert aceita(aut, "a")
        assert aceita(aut, "aaaa")
        assert not aceita(aut, "b")
        assert not aceita(aut, "ab")


def test_caso_borda_classes_negadas():
    arvore = parse("[^a-c]")
    afn = construir_afn(arvore)
    afd = construir_afd(afn)
    min_afd = minimizar(afd)

    for cadeia in ("d", "x", "ç", "\n"):
        assert aceita(afd, cadeia)
        assert aceita(min_afd, cadeia)
        assert simular_afn(afn, cadeia)

    for cadeia in ("a", "b", "c", ""):
        assert not aceita(afd, cadeia)
        assert not aceita(min_afd, cadeia)
        assert not simular_afn(afn, cadeia)


def test_caso_borda_acentos():
    arvore = parse("promoção")
    afn = construir_afn(arvore)
    afd = construir_afd(afn)
    min_afd = minimizar(afd)

    assert aceita(afd, "promoção")
    assert aceita(min_afd, "promoção")
    assert not aceita(afd, "promocao")
    assert not aceita(min_afd, "promocao")

    arvore_faixa = parse("[à-ü]")
    afd_faixa = minimizar(construir_afd(construir_afn(arvore_faixa)))
    for c in ("à", "é", "ç", "ü"):
        assert aceita(afd_faixa, c)
    for c in ("a", "z", "A"):
        assert not aceita(afd_faixa, c)


def test_prioridade_dois_tokens_aceitando_mesma_cadeia():
    """Quando dois tokens aceitam a mesma cadeia, vence o de menor id_token."""
    afn = AFN(num_estados=1)
    # Token 1 (maior id): aceita "abc"
    afn1 = construir_afn(parse("abc"), id_token=1)
    # Token 0 (menor id): aceita "abc"
    afn0 = construir_afn(parse("abc"), id_token=0)

    # Conectar ambos ao estado inicial do AFN global
    d1 = afn.num_estados
    afn.num_estados += afn1.num_estados
    afn.adicionar_transicao(afn.inicial, None, afn1.inicial + d1)
    for o, s in afn1.transicoes.items():
        for i, d in s:
            afn.adicionar_transicao(o + d1, i, d + d1)
    for q, tok in afn1.aceitacao.items():
        afn.aceitacao[q + d1] = tok

    d0 = afn.num_estados
    afn.num_estados += afn0.num_estados
    afn.adicionar_transicao(afn.inicial, None, afn0.inicial + d0)
    for o, s in afn0.transicoes.items():
        for i, d in s:
            afn.adicionar_transicao(o + d0, i, d + d0)
    for q, tok in afn0.aceitacao.items():
        afn.aceitacao[q + d0] = tok

    afn.validar()
    afd = construir_afd(afn)
    min_afd = minimizar(afd)

    # Simular "abc" no AFD e no AFD mínimo e verificar qual id_token é aceito
    def obter_token_aceito(automato, cadeia):
        s = automato.inicial
        for ch in cadeia:
            c = ord(ch)
            prox = None
            for (ini, fim), dest in automato.saidas(s):
                if ini <= c <= fim:
                    prox = dest
                    break
            if prox is None:
                return None
            s = prox
        return automato.aceitacao.get(s)

    assert obter_token_aceito(afd, "abc") == 0
    assert obter_token_aceito(min_afd, "abc") == 0
