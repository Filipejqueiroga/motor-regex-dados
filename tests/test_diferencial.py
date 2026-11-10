"""Teste diferencial contra o módulo ``re``, usado aqui apenas como oráculo.

Compara somente ``fullmatch``: ``re.search`` e ``re.match`` usam a primeira
alternativa que casa, e o motor usa o casamento mais longo.
"""

import random
import re

from motor.minimizacao import minimizar
from motor.parser import parse
from motor.simulador import aceita
from motor.subconjuntos import construir_afd
from motor.thompson import construir_afn

SEMENTE = 20261110
QUANTIDADE_PADROES = 500
CADEIAS_POR_PADRAO = 30
PROFUNDIDADE_MAXIMA = 2
TAMANHO_MAXIMO_PADRAO = 40

LITERAIS = "abc0é_"
ALFABETO = "abc019_ .-\táéçÃZ\n"
CLASSES = ["[abc]", "[a-c0-9]", "[^abc]", "[^\\d]", "[é_]", r"\d", r"\w", r"\s", r"\D", r"\W", r"\S", "."]
QUANTIFICADORES = ["*", "+", "?", "{2}", "{1,3}", "{0,2}", "{2,}"]


def _atomo(rng, profundidade):
    if profundidade > 0 and rng.random() < 0.35:
        return f"({_uniao(rng, profundidade - 1)})"
    if rng.random() < 0.55:
        return rng.choice(LITERAIS)
    return rng.choice(CLASSES)


def _repeticao(rng, profundidade):
    atomo = _atomo(rng, profundidade)
    return atomo + rng.choice(QUANTIFICADORES) if rng.random() < 0.4 else atomo


def _concat(rng, profundidade):
    return "".join(_repeticao(rng, profundidade) for _ in range(rng.randint(0 if profundidade < 2 else 1, 3)))


def _uniao(rng, profundidade):
    return "|".join(_concat(rng, profundidade) for _ in range(rng.choice((1, 1, 2, 3))))


def gerar_padrao(rng):
    """Sorteia até obter um padrão pequeno, evitando a explosão de subconjuntos."""
    while True:
        padrao = _uniao(rng, PROFUNDIDADE_MAXIMA)
        if len(padrao) <= TAMANHO_MAXIMO_PADRAO:
            return padrao


def gerar_cadeia(rng):
    return "".join(rng.choice(ALFABETO) for _ in range(rng.randint(0, 8)))


def test_motor_coincide_com_re_fullmatch():
    rng = random.Random(SEMENTE)
    aceitas = 0
    for indice in range(QUANTIDADE_PADROES):
        padrao = gerar_padrao(rng)
        oraculo = re.compile(padrao)
        afd = construir_afd(construir_afn(parse(padrao)))
        afd_minimo = minimizar(afd)
        for _ in range(CADEIAS_POR_PADRAO):
            cadeia = gerar_cadeia(rng)
            esperado = oraculo.fullmatch(cadeia) is not None
            aceitas += esperado
            contexto = f"semente={SEMENTE} indice={indice} padrao={padrao!r} cadeia={cadeia!r}"
            assert aceita(afd, cadeia) == esperado, f"AFD divergiu: {contexto}"
            assert aceita(afd_minimo, cadeia) == esperado, f"AFD mínimo divergiu: {contexto}"
    assert aceitas > 0, f"semente={SEMENTE}: nenhuma cadeia aceita, o teste não exercitou o motor"


def test_casamento_mais_longo_difere_do_search_propositalmente():
    afd = construir_afd(construir_afn(parse("a|ab")))
    assert aceita(afd, "ab")
    assert re.match("a|ab", "ab").group() == "a"
