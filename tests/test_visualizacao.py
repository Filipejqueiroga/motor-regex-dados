"""Testes da geração de Graphviz DOT."""

import pytest

from motor.automatos import AFD, AFN, EPSILON, MAX_CODEPOINT
from motor.minimizacao import minimizar
from motor.parser import parse
from motor.subconjuntos import construir_afd
from motor.thompson import construir_afn
from motor.visualizacao import afd_para_dot, afn_para_dot, rotulo_intervalos


def afn_de(padrao):
    return construir_afn(parse(padrao))


def afd_de(padrao):
    return construir_afd(afn_de(padrao))


@pytest.mark.parametrize(
    ("intervalos", "esperado"),
    [
        ([(48, 57)], "0-9"),
        ([(97, 122)], "a-z"),
        ([(97, 97)], "a"),
        ([(94, 94)], "^"),
        ([(0, MAX_CODEPOINT)], "qualquer"),
        ([(0, 47), (58, MAX_CODEPOINT)], "[^0-9]"),
        ([(0, 9), (11, MAX_CODEPOINT)], "[^\\n]"),
        ([(48, 57), (65, 70)], "0-9 A-F"),
    ],
)
def test_rotulo_intervalos(intervalos, esperado):
    assert rotulo_intervalos(intervalos) == esperado


def test_rotulo_usa_atalho_para_palavra_e_seu_complemento():
    from motor.automatos import complementar_intervalos
    from motor.parser import ESPACOS, PALAVRA

    assert rotulo_intervalos(PALAVRA) == r"\w"
    assert rotulo_intervalos(ESPACOS) == r"\s"
    assert rotulo_intervalos(complementar_intervalos(PALAVRA)) == r"[^\w]"


def test_afn_tem_epsilon_inicial_e_aceitacao():
    afn = afn_de("a|b")
    dot = afn_para_dot(afn)
    assert dot.startswith("digraph AFN {")
    assert 'label="ε"' in dot
    assert f'"inicio" -> "{afn.inicial}"' in dot
    estado_final = next(iter(afn.aceitacao))
    linha = next(l for l in dot.splitlines() if l.strip().startswith(f'"{estado_final}" ['))
    assert "peripheries=2" in linha


def test_afn_agrupa_intervalos_da_mesma_aresta():
    afn = AFN()
    q0, q1 = afn.novo_estado(), afn.novo_estado()
    afn.adicionar_transicao(q0, (48, 57), q1)
    afn.adicionar_transicao(q0, (97, 122), q1)
    afn.adicionar_transicao(q0, EPSILON, q1)
    afn.aceitacao[q1] = 0
    dot = afn_para_dot(afn)
    assert 'label="0-9 a-z"' in dot
    assert dot.count(f'"{q0}" -> "{q1}"') == 2


def test_afd_mostra_conjunto_do_afn_e_token():
    afd = afd_de("ab")
    dot = afd_para_dot(afd, nomes_tokens=["CPF"])
    for estado in range(afd.num_estados):
        conjunto = sorted(afd.estados_afn[estado])
        assert "{" + ",".join(map(str, conjunto[:6])) in dot
    assert 'xlabel="CPF"' in dot


def test_afd_sem_nomes_usa_id_do_token():
    assert "token 0" in afd_para_dot(afd_de("a"))


def test_afd_minimo_pode_ocultar_conjuntos():
    dot = afd_para_dot(minimizar(afd_de("a|b")), mostrar_estados_afn=False)
    assert "{" not in dot.split("\n", 6)[-1].replace("digraph", "")


def test_destaque_marca_somente_o_estado_pedido():
    afd = afd_de("ab")
    sem_destaque = afd_para_dot(afd)
    com_destaque = afd_para_dot(afd, destaque=1)
    assert "penwidth=3.5" not in sem_destaque
    assert com_destaque.count("penwidth=3.5") == 1
    linha = next(l for l in com_destaque.splitlines() if l.strip().startswith('"1" ['))
    assert "penwidth=3.5" in linha


def test_destaque_invalido_e_recusado():
    with pytest.raises(ValueError):
        afd_para_dot(afd_de("a"), destaque=99)


@pytest.mark.parametrize("padrao", [r'"', r"\\", r"\n", r"\t", "a b", r"\"x\\"])
def test_simbolos_especiais_sao_escapados(padrao):
    dot = afd_para_dot(afd_de(padrao))
    for linha in dot.splitlines():
        if "label=" not in linha:
            continue
        valor = linha.split('label="', 1)[1]
        i = 0
        while valor[i] != '"':
            i += 2 if valor[i] == "\\" else 1
        assert valor[i + 1:].strip()[0] in ",]"


def test_saida_e_deterministica():
    afd = afd_de("(a|b)*abb")
    assert afd_para_dot(afd) == afd_para_dot(afd)


def test_afd_vazio_de_transicoes():
    afd = AFD()
    afd.novo_estado()
    afd.aceitacao[0] = 0
    assert '"0" [' in afd_para_dot(afd)
