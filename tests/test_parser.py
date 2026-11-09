import ast
import itertools
import re  # permitido apenas nos testes, como oráculo de comparação
from pathlib import Path

import pytest

from motor.arvore import Classe, Concat, Estrela, No, Uniao, Vazio
from motor.automatos import MAX_CODEPOINT
from motor.parser import ErroDeSintaxe, parse
from tests.referencia import casa


def L(caractere: str) -> Classe:
    return Classe.literal(caractere)


def C(*faixas: str) -> Classe:
    """``C("az", "09", "_")`` -> classe ``[a-z0-9_]``."""
    return Classe(tuple((ord(f[0]), ord(f[-1])) for f in faixas))


def partes(no: No) -> list[No]:
    """Achata uma cadeia de ``Concat`` na lista de fatores, em ordem."""
    if isinstance(no, Concat):
        return partes(no.esq) + partes(no.dir)
    return [no]


def nos_usados(no: No) -> set[type]:
    tipos, pilha = set(), [no]
    while pilha:
        atual = pilha.pop()
        tipos.add(type(atual))
        if isinstance(atual, (Concat, Uniao)):
            pilha += [atual.esq, atual.dir]
        elif isinstance(atual, Estrela):
            pilha.append(atual.filho)
    return tipos


# ---------------------------------------------------------------------------
# Núcleo e precedência
# ---------------------------------------------------------------------------

def test_literal_e_concatenacao():
    assert parse("a") == L("a")
    assert partes(parse("abc")) == [L("a"), L("b"), L("c")]


def test_precedencia_uniao_concat_estrela():
    # ab|c* = (ab)|(c*)
    assert parse("ab|c*") == Uniao(Concat(L("a"), L("b")), Estrela(L("c")))
    # ab* = a(b*)
    assert parse("ab*") == Concat(L("a"), Estrela(L("b")))
    # (ab)* agrupa
    assert parse("(ab)*") == Estrela(Concat(L("a"), L("b")))


def test_uniao_de_varios_ramos():
    arvore = parse("a|b|c")
    assert all(casa(arvore, s) for s in "abc")
    assert not casa(arvore, "ab")


@pytest.mark.parametrize("padrao", ["", "()", "(())", "a{0}"])
def test_vazio(padrao):
    assert parse(padrao) == Vazio()


def test_alternativa_vazia():
    assert parse("a|") == Uniao(L("a"), Vazio())
    assert parse("|a") == Uniao(Vazio(), L("a"))


def test_estrela_aninhada_com_grupo_e_permitida():
    assert parse("(a*)*") == Estrela(Estrela(L("a")))


# ---------------------------------------------------------------------------
# Quantificadores
# ---------------------------------------------------------------------------

def test_mais():
    assert parse("a+") == Concat(L("a"), Estrela(L("a")))


def test_interrogacao():
    assert parse("a?") == Uniao(L("a"), Vazio())


def test_repeticao_exata():
    assert partes(parse("a{3}")) == [L("a")] * 3


def test_repeticao_com_minimo():
    assert partes(parse("a{2,}")) == [L("a"), L("a"), Estrela(L("a"))]
    assert parse("a{0,}") == Estrela(L("a"))


def test_repeticao_com_intervalo():
    opcional = Uniao(L("a"), Vazio())
    assert partes(parse("a{1,3}")) == [L("a"), opcional, opcional]
    assert partes(parse("a{0,2}")) == [opcional, opcional]


def test_repeticao_de_grupo():
    arvore = parse("(ab){2}")
    assert partes(arvore) == [L("a"), L("b"), L("a"), L("b")]


def test_repeticao_no_limite_nao_estoura_recursao():
    # A issue fixa o limite em 1000: a{1000} é aceito, a{1001} não.
    arvore = parse("a{1000}")
    assert len(partes(arvore)) == 1000
    assert len(partes(parse("a{0,1000}"))) == 1000
    assert casa(parse("a{2,4}"), "aaa")


# ---------------------------------------------------------------------------
# Classes e atalhos
# ---------------------------------------------------------------------------

def test_classe_com_intervalos():
    assert parse("[a-z0-9_]") == C("az", "09", "_")


def test_classe_negada():
    arvore = parse("[^a-c]")
    assert arvore == Classe(((0, ord("a") - 1), (ord("c") + 1, MAX_CODEPOINT)))
    assert casa(arvore, "d") and casa(arvore, "ç") and casa(arvore, "\n")
    assert not casa(arvore, "b")


def test_ponto_aceita_tudo_menos_quebra_de_linha():
    arvore = parse(".")
    assert casa(arvore, "x") and casa(arvore, "ç") and casa(arvore, "😀")
    assert not casa(arvore, "\n")


def test_atalhos():
    assert parse("\\d") == C("09")
    assert parse("\\s") == Classe(tuple((ord(c), ord(c)) for c in " \t\n\r\f\v"))
    palavra = parse("\\w")
    for caractere in "aZ09_çãÀÖØöøÿé":
        assert palavra.contem(caractere), caractere
    for caractere in " -.×÷@":
        assert not palavra.contem(caractere), caractere


def test_atalhos_negados():
    assert casa(parse("\\D"), "a") and not casa(parse("\\D"), "5")
    assert casa(parse("\\S"), "a") and not casa(parse("\\S"), " ")
    assert casa(parse("\\W"), "-") and not casa(parse("\\W"), "ç")


def test_atalho_dentro_de_classe():
    arvore = parse("[^\\s.,]")
    assert casa(arvore, "a")
    for caractere in " \n.,":
        assert not casa(arvore, caractere)
    assert parse("[\\d_]") == C("09", "_")


def test_hifen_no_inicio_ou_fim_e_literal():
    assert parse("[-a]") == C("-", "a")
    assert parse("[a-]") == C("-", "a")
    assert parse("[^-]") == Classe(((0, ord("-") - 1), (ord("-") + 1, MAX_CODEPOINT)))


def test_metacaracteres_sao_literais_dentro_de_classe():
    arvore = parse("[.+%()*?|{]")
    for caractere in ".+%()*?|{":
        assert casa(arvore, caractere), caractere
    assert not casa(arvore, "a")


def test_colchete_de_fechamento_logo_no_inicio_e_literal():
    assert parse("[]a]") == C("]", "a")


# ---------------------------------------------------------------------------
# Escapes e acentos
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("meta", list(".$()[]{}*+?|\\^-/"))
def test_escape_de_metacaracteres(meta):
    assert parse("\\" + meta) == L(meta)


def test_escapes_de_controle():
    assert parse("\\n") == L("\n")
    assert parse("\\t") == L("\t")
    assert parse("[\\n\\t]") == Classe(((9, 10),))


def test_caracteres_acentuados():
    arvore = parse("promoção")
    assert casa(arvore, "promoção")
    assert not casa(arvore, "promocao")
    assert parse("[à-ü]") == C("àü")
    assert casa(parse("#\\w+"), "#promoção")


def test_chave_de_fechamento_sozinha_e_literal():
    assert parse("a}") == Concat(L("a"), L("}"))


# ---------------------------------------------------------------------------
# A árvore só tem os cinco nós básicos
# ---------------------------------------------------------------------------

PADROES_DO_PROJETO = {
    "CNPJ": r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}",
    "CPF": r"\d{3}\.\d{3}\.\d{3}-\d{2}|\d{11}",
    "EMAIL": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+",
    "URL": r"https?://[^\s]*[^\s.,;:!?)]",
    "TELEFONE": r"(\(\d{2}\) ?|\d{2}[ -]?)(9\d{4}|\d{4})-?\d{4}",
    "CEP": r"\d{5}-\d{3}",
    "DATA": r"\d{2}/\d{2}/\d{4}",
    "VALOR": r"R\$ ?(\d{1,3}(\.\d{3})+|\d+)(,\d{2})?",
    "HASHTAG": r"#\w+",
    "MENCAO": r"@\w+",
}

EXEMPLOS_DO_PROJETO = {
    "CNPJ": (["12.345.678/0001-95"], ["12.345.678/0001-9", "12345678000195"]),
    "CPF": (["123.456.789-09", "12345678909"], ["123.456.789-0", "1234567890"]),
    "EMAIL": (["maria.silva@gmail.com", "a@b.com"], ["a@b", "@b.com", "a@b.com."]),
    "URL": (["https://exemplo.com.br", "http://a.com/x?y=1"], ["https://a.com.", "ftp://a.com"]),
    "TELEFONE": (["(83) 98765-4321", "83 3221-1234", "83987654321", "8332211234"], ["98765-4321"]),
    "CEP": (["58000-000"], ["58000000", "5800-000"]),
    "DATA": (["03/11/2026"], ["3/11/2026", "03-11-2026"]),
    "VALOR": (["R$ 1.234,56", "R$10", "R$ 1.000.000"], ["R$ 1.23", "R$ ,50", "1.234,56"]),
    "HASHTAG": (["#promoção", "#a1_b"], ["#", "#a-b"]),
    "MENCAO": (["@loja_oficial"], ["@", "@loja.oficial"]),
}


@pytest.mark.parametrize("nome", PADROES_DO_PROJETO)
def test_padroes_do_projeto(nome):
    arvore = parse(PADROES_DO_PROJETO[nome])
    assert nos_usados(arvore) <= {Vazio, Classe, Concat, Uniao, Estrela}
    aceitos, rejeitados = EXEMPLOS_DO_PROJETO[nome]
    for cadeia in aceitos:
        assert casa(arvore, cadeia), cadeia
    for cadeia in rejeitados:
        assert not casa(arvore, cadeia), cadeia


# ---------------------------------------------------------------------------
# Comparação com o re do Python (usado só como referência)
# ---------------------------------------------------------------------------

PADROES_PEQUENOS = [
    "", "a", "ab", "a|b", "ab|c*", "a*", "a+", "a?", "(ab)*", "(a|b)*abb",
    "(a*)*", "(a|)b", "a{2}", "a{1,3}", "a{2,}", "(a|b){0,2}c?", "[ab]+c",
    "[^a]*", "a.c", "[a-c]{2}", "(a+b?)+", "((a|b)c)*|c", "\\.a*",
]


@pytest.mark.parametrize("padrao", PADROES_PEQUENOS)
def test_equivale_ao_re_em_todas_as_cadeias_curtas(padrao):
    arvore = parse(padrao)
    assert nos_usados(arvore) <= {Vazio, Classe, Concat, Uniao, Estrela}
    for tamanho in range(5):
        for letras in itertools.product("abc.", repeat=tamanho):
            cadeia = "".join(letras)
            esperado = re.fullmatch(padrao, cadeia) is not None
            assert casa(arvore, cadeia) == esperado, (padrao, cadeia)


# ---------------------------------------------------------------------------
# Erros com posição
# ---------------------------------------------------------------------------

ERROS = [
    # (padrão, posição, trecho da mensagem)
    ("(ab", 0, "'(' sem ')'"),
    ("a(b(c)", 1, "'(' sem ')'"),
    ("ab)", 2, "')' sem '('"),
    ("[abc", 0, "'[' sem ']'"),
    ("a[^", 1, "'[' sem ']'"),
    ("*a", 0, "sem operando"),
    ("a|+b", 2, "sem operando"),
    ("(?a)", 0, "lookahead"),
    ("{3}", 0, "sem operando"),
    ("a{3,2}", 1, "mínimo maior que máximo"),
    ("[z-a]", 1, "intervalo invertido"),
    ("x[0-9a-A]", 5, "intervalo invertido"),
    ("a**", 2, "empilhados"),
    ("a*?", 2, "empilhados"),
    ("a++", 2, "empilhados"),
    ("a{2}{3}", 4, "empilhados"),
    ("a{", 1, "quantificador válido"),
    ("a{x}", 1, "quantificador válido"),
    ("a{2", 1, "quantificador válido"),
    ("a{2,x}", 1, "quantificador válido"),
    ("a{,3}", 1, "quantificador válido"),
    ("a{1001}", 1, "maior que"),
    ("a{1,1001}", 1, "maior que"),
    ("a{1001,}", 1, "maior que"),
    ("(a{1000}){1000}", 9, "grande demais"),
    ("(a)\\1", 3, "backreference"),
    ("(?=a)b", 0, "lookahead"),
    ("(?!a)b", 0, "lookahead"),
    ("(?<=a)b", 0, "lookahead"),
    ("abc\\", 3, "fim do padrão"),
    ("\\q", 0, "escape desconhecido"),
    ("a\\b", 1, "âncora"),
    ("^a", 0, "âncora"),
    ("a$", 1, "âncora"),
    ("[\\d-z]", 1, "atalho"),
    ("[a-\\d]", 3, "atalho"),
]


@pytest.mark.parametrize("padrao, posicao, trecho", ERROS)
def test_erros_informam_posicao(padrao, posicao, trecho):
    with pytest.raises(ErroDeSintaxe) as info:
        parse(padrao)
    erro = info.value
    assert erro.posicao == posicao, str(erro)
    assert trecho in erro.mensagem
    assert erro.padrao == padrao
    assert "^" in str(erro)  # mostra onde está o erro


def test_aninhamento_excessivo_vira_erro_de_sintaxe():
    with pytest.raises(ErroDeSintaxe):
        parse("(" * 5000 + "a" + ")" * 5000)


# ---------------------------------------------------------------------------
# Regra do projeto: nada de re no motor
# ---------------------------------------------------------------------------

PROIBIDOS = {"re", "regex", "sre_compile", "sre_parse", "fnmatch"}


@pytest.mark.parametrize(
    "arquivo",
    sorted((Path(__file__).resolve().parent.parent / "motor").glob("*.py")),
    ids=lambda p: p.name,
)
def test_motor_nao_importa_bibliotecas_de_regex(arquivo):
    arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            nomes = [alias.name.split(".")[0] for alias in no.names]
        elif isinstance(no, ast.ImportFrom):
            nomes = [(no.module or "").split(".")[0]]
        else:
            continue
        assert not PROIBIDOS & set(nomes), f"{arquivo.name} importa {nomes}"
