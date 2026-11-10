"""Casos de borda de ponta a ponta e garantia de que o motor não usa ``re``."""

import ast
from pathlib import Path

import pytest

from motor.minimizacao import minimizar
from motor.padroes import PADROES, Padrao
from motor.parser import parse
from motor.simulador import aceita, maior_casamento
from motor.subconjuntos import construir_afd
from motor.thompson import construir_afn
from motor.tokenizador import Tokenizador

RAIZ = Path(__file__).resolve().parent.parent
MODULOS_PROIBIDOS = {"re", "regex", "sre_compile", "sre_parse", "sre_constants", "_sre"}


def compilar(padrao):
    return minimizar(construir_afd(construir_afn(parse(padrao))))


@pytest.mark.parametrize("arquivo", sorted((RAIZ / "motor").glob("*.py")), ids=lambda p: p.name)
def test_motor_nao_importa_bibliotecas_de_regex(arquivo):
    arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            nomes = [alias.name for alias in no.names]
        elif isinstance(no, ast.ImportFrom):
            nomes = [no.module or ""]
        elif (
            isinstance(no, ast.Call)
            and getattr(no.func, "id", getattr(no.func, "attr", "")) in ("__import__", "import_module")
            and no.args
            and isinstance(no.args[0], ast.Constant)
        ):
            nomes = [str(no.args[0].value)]
        else:
            continue
        for nome in nomes:
            assert nome.split(".")[0] not in MODULOS_PROIBIDOS, f"{arquivo.name} importa {nome}"


@pytest.mark.parametrize(
    ("padrao", "cadeia", "esperado"),
    [
        ("", "", True),
        ("", "a", False),
        ("a*", "", True),
        ("a+", "", False),
        ("(a*)*", "", True),
        ("(a*)*", "aaaa", True),
        ("((a*)*|b*)*", "aabbab", True),
        ("(a+)+b", "aaab", True),
        ("[^abc]", "d", True),
        ("[^abc]", "a", False),
        ("[^abc]", "é", True),
        ("[^\\n]*", "linha\n", False),
        (r"\w+", "ação", True),
        (r"\w+", "ÃÉÇ", True),
        (r"\W", "é", False),
        ("[á-ú]+", "éíó", True),
        ("coração", "coração", True),
        ("coração", "coracao", False),
    ],
)
def test_casos_de_borda_no_afd_minimo(padrao, cadeia, esperado):
    assert aceita(compilar(padrao), cadeia) is esperado


def test_cadeia_vazia_nao_gera_tokens():
    assert Tokenizador(PADROES).tokenizar("") == []


def test_sem_padroes_ativos_nao_gera_tokens():
    assert Tokenizador(()).tokenizar("123.456.789-09") == []


def test_padrao_que_aceita_vazio_nao_gera_token_vazio():
    tokens = Tokenizador([Padrao("PERSONALIZADO", "a*")]).tokenizar("baab")
    assert [(t.texto, t.inicio, t.fim) for t in tokens] == [("aa", 1, 3)]


def test_token_com_acentos_mantem_indices_de_caracteres():
    texto = "ação #promoção café"
    tokens = Tokenizador(PADROES).tokenizar(texto)
    assert [(t.tipo, t.texto) for t in tokens] == [("HASHTAG", "#promoção")]
    assert texto[tokens[0].inicio:tokens[0].fim] == "#promoção"


def test_maior_casamento_em_texto_longo():
    afd = compilar("a*")
    assert maior_casamento(afd, "a" * 20_000, 0) == (20_000, 0)


def test_tokeniza_texto_longo_sem_perder_ocorrencias():
    trecho = "CPF 123.456.789-09 e #tag em 03/11/2026. "
    tokens = Tokenizador(PADROES).tokenizar(trecho * 500)
    assert len(tokens) == 1500
    assert all(trecho * 500 and t.fim - t.inicio > 0 for t in tokens)
