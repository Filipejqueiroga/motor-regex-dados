"""Testes da interface Streamlit, sem navegador."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from app import CORES_TOKENS, html_destacado, html_fita, html_tabela, linhas_da_tabela, situacao_do_passo
from motor.minimizacao import minimizar
from motor.padroes import PADROES
from motor.parser import parse
from motor.simulador import passos
from motor.subconjuntos import construir_afd
from motor.thompson import construir_afn
from motor.tokenizador import Token

ARQUIVO_APP = str(Path(__file__).resolve().parent.parent / "app.py")


@pytest.fixture
def app():
    aplicacao = AppTest.from_file(ARQUIVO_APP, default_timeout=30).run()
    assert not aplicacao.exception
    return aplicacao


def corpo_da_tabela(aplicacao):
    return next((e.proto.body for e in aplicacao.get("html") if 'class="tokens"' in e.proto.body), None)


def tipos_da_tabela(aplicacao):
    celulas = corpo_da_tabela(aplicacao).split('<td class="tipo')[1:]
    return [celula.split(">", 1)[1].split("<", 1)[0] for celula in celulas]


def test_exemplo_da_secao_4_encontra_todos_os_tipos(app):
    assert tipos_da_tabela(app) == [
        "CPF", "EMAIL", "TELEFONE", "VALOR", "DATA", "URL", "HASHTAG", "MENCAO",
    ]
    assert "<td>Válidos</td>" in corpo_da_tabela(app)


def test_regra_de_sanitizacao_e_aplicada(app):
    app.selectbox(key="regra_CPF").set_value("Mascarar").run()
    assert not app.exception
    assert "*" * 14 in app.code[0].value


def test_padrao_personalizado_invalido_nao_derruba(app):
    app.text_input(key="padrao_personalizado").set_value("a(b").run()
    assert not app.exception
    assert "posição 1" in app.error[0].value
    assert "CPF" in tipos_da_tabela(app)


def test_padrao_personalizado_valido_entra_na_tabela(app):
    app.text_input(key="padrao_personalizado").set_value("Maria").run()
    assert not app.exception
    assert tipos_da_tabela(app)[0] == "PERSONALIZADO"


def test_texto_vazio_nao_gera_tabela(app):
    app.text_area(key="texto").set_value("").run()
    assert not app.exception
    assert corpo_da_tabela(app) is None


def test_expressao_invalida_nos_automatos_mostra_posicao(app):
    app.text_input(key="expressao_automato").set_value("[a").run()
    assert not app.exception
    assert "posição 0" in app.error[0].value


def test_passo_a_passo_avanca_e_volta(app):
    app.button(key="passo_proximo").click().run()
    assert not app.exception
    assert app.session_state.passo == 1
    app.button(key="passo_anterior").click().run()
    assert app.session_state.passo == 0


def test_mudar_cadeia_reinicia_o_passo(app):
    app.button(key="passo_proximo").click().run()
    app.text_input(key="cadeia_automato").set_value("1").run()
    assert not app.exception
    assert app.session_state.passo == 0


def test_todas_as_etapas_e_padroes_renderizam(app):
    for padrao in PADROES:
        app.selectbox(key="padrao_automato").set_value(padrao.nome).run()
        assert not app.exception, padrao.nome


def test_html_do_usuario_e_escapado():
    texto = "<script>alert(1)</script> #tag<b>"
    token = Token("HASHTAG", "#tag", 26, 30)
    resultado = html_destacado(texto, [token])
    assert "<script>" not in resultado
    assert "&lt;script&gt;" in resultado
    assert "&lt;b&gt;" in resultado


def test_tabela_escapa_conteudo_do_usuario():
    resultado = html_tabela([Token("PERSONALIZADO", "<img src=x>", 0, 11)])
    assert "<img" not in resultado
    assert "&lt;img" in resultado


def test_token_malicioso_e_escapado():
    resultado = html_destacado("<i>", [Token("PERSONALIZADO", "<i>", 0, 3)])
    assert "<i>" not in resultado


def test_documento_invalido_e_indicado_no_texto():
    token = Token("CPF", "111.111.111-11", 0, 14, digitos_validos=False)
    assert "CPF inválido" in html_destacado(token.texto, [token])


def test_fita_escapa_e_marca_celulas():
    resultado = html_fita("a<b", 2)
    assert "&lt;" in resultado
    assert resultado.count('class="lido"') == 1
    assert resultado.count('class="atual"') == 1


def test_fita_indica_travamento():
    assert 'class="travou"' in html_fita("ab", 1, travou=True)


def test_tabela_traduz_validade():
    tokens = [Token("CPF", "x", 0, 1, False), Token("URL", "y", 2, 3)]
    assert [linha["Dígitos"] for linha in linhas_da_tabela(tokens)] == ["Inválidos", "Não se aplica"]


def test_situacao_do_passo_trava_no_estado_de_origem():
    afd = minimizar(construir_afd(construir_afn(parse("ab"))))
    registros = passos(afd, "ax")
    situacao = situacao_do_passo(afd, registros, 2)
    assert situacao["travou"]
    assert situacao["estado"] == registros[1][0]


def test_todo_padrao_tem_cor():
    assert {padrao.nome for padrao in PADROES} <= set(CORES_TOKENS)
