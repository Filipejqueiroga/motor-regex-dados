"""Interface web do motor: camada fina em Streamlit, sem regra de negócio."""

from __future__ import annotations

import html

import streamlit as st

from motor.automatos import AFD, formatar_simbolo
from motor.exportador import exportar_json
from motor.minimizacao import minimizar
from motor.padroes import PADROES, Padrao
from motor.parser import ErroDeSintaxe, parse
from motor.sanitizador import sanitizar
from motor.simulador import passos
from motor.subconjuntos import construir_afd
from motor.thompson import construir_afn
from motor.tokenizador import Token, Tokenizador
from motor.visualizacao import afd_para_dot, afn_para_dot
from validacao_documentos import validar_documentos

TEXTO_EXEMPLO = (
    "Oi, sou a Maria. Meu CPF é 123.456.789-09 e meu email é maria.silva@gmail.com. "
    "Me liga: (83) 98765-4321. Paguei R$ 1.234,56 no dia 03/11/2026. "
    "Veja https://exemplo.com.br #promoção @loja_oficial"
)
PADRAO_EXEMPLO = r"\d\d\d-\d\d"
CADEIA_EXEMPLO = "123-45"
PERSONALIZADO = "PERSONALIZADO"
LIMITE_ESTADOS_DIAGRAMA = 150

CORES_TOKENS = {
    "CNPJ": "#FFB070",
    "CPF": "#FF9CCB",
    "EMAIL": "#86CBFF",
    "URL": "#B3BEFF",
    "TELEFONE": "#86E6AE",
    "CEP": "#C3E873",
    "DATA": "#DDBBFF",
    "VALOR": "#66E3DA",
    "HASHTAG": "#F5BDB0",
    "MENCAO": "#DCC89F",
    PERSONALIZADO: "#14182B",
}
REGRAS = {"Rótulo": "rotulo", "Mascarar": "mascarar", "Remover": "remover", "Manter": "manter"}
ETAPAS = ("AFN", "AFD", "AFD mínimo")

ESTILO = """
<style>
::selection { background: #FFE14D; color: #14182B; }
html { scrollbar-color: #4A5168 #E3E7F1; }
:focus-visible { outline: 3px solid #14182B; outline-offset: 2px; }
[data-testid="stHeader"] { display: none; }
[data-testid="stMain"] { overflow-x: hidden; }
[data-testid="stMainBlockContainer"] { padding: 0 2.5rem 4rem; max-width: 1480px; }

.tarja {
  background: #14182B; color: #F1F3F8;
  margin-inline: calc(50% - 50vw); padding: 1.35rem calc(50vw - 50%);
  display: flex; flex-wrap: wrap; align-items: baseline; gap: .25rem 1.5rem;
}
.tarja h1 { font-size: 1.9rem; line-height: 1.15; font-weight: 700; margin: 0; padding: 0; color: inherit; }
.tarja p { margin: 0; color: #C6CCDF; font-size: 1.05rem; }

[data-testid="stTabs"] button[role="tab"] p { font-size: 1.2rem; }
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] p { font-weight: 700; }
h3 { font-size: 1.3rem !important; padding: .4rem 0 .15rem !important; }

.st-key-etapa_automato button { border-color: #14182B; font-size: 1.05rem; min-height: 3rem; }
[data-testid="stButtonGroup"] button:is([aria-pressed="true"], [aria-checked="true"]),
[data-testid="stButtonGroup"] button:is([aria-pressed="true"], [aria-checked="true"]):hover { background-color: #14182B !important; border-color: #14182B !important; }
[data-testid="stButtonGroup"] button:is([aria-pressed="true"], [aria-checked="true"]) * { color: #FFFFFF !important; }
[data-testid="stGraphVizChart"] { background: #FFFFFF; border: 1px solid #B9C0D3; padding: .5rem; }

.etapa-er {
  border: 1px solid #14182B; min-height: 3rem; padding: .55rem .85rem; background: #FFFFFF;
  font-family: "JetBrains Mono", Consolas, monospace; font-size: .95rem;
  overflow-wrap: anywhere;
}
.documento {
  background: #FFFFFF; border: 1px solid #B9C0D3; padding: 1.1rem 1.25rem;
  white-space: pre-wrap; overflow-wrap: anywhere; line-height: 2.05; font-size: 1.05rem;
}
.documento mark {
  background: var(--caneta); color: #14182B; padding: .12em .3em;
  -webkit-box-decoration-break: clone; box-decoration-break: clone;
}
.documento mark.escuro { color: #FFFFFF; }
.documento .tipo { font-size: .68em; font-weight: 700; margin-left: .55em; }
.vazio { color: #4A5168; padding: .6rem 0; }

.tabela { overflow-x: auto; }
.tokens { width: 100%; border-collapse: collapse; background: #FFFFFF; font-size: 1.02rem; }
.tokens th { background: #14182B; color: #FFFFFF; text-align: left; padding: .55rem .85rem; font-weight: 700; }
.tokens td { padding: .5rem .85rem; border-bottom: 1px solid #B9C0D3; overflow-wrap: anywhere; }
.tokens .dado { font-family: "JetBrains Mono", Consolas, monospace; font-size: .95rem; font-variant-numeric: tabular-nums; }
.tokens .tipo { background: var(--caneta); font-weight: 700; white-space: nowrap; }
.tokens .tipo.escuro { color: #FFFFFF; }

.fita { display: flex; flex-wrap: wrap; gap: 4px; margin-top: .75rem; }
.fita span {
  width: 3.4rem; height: 3.9rem; display: grid; place-items: center;
  border: 2px solid #14182B; background: #FFFFFF;
  font: 700 1.65rem "JetBrains Mono", Consolas, monospace;
  transition: background-color 160ms cubic-bezier(.16, 1, .3, 1), color 160ms cubic-bezier(.16, 1, .3, 1);
}
.fita .lido { background: #FFE14D; }
.fita .atual { background: #14182B; color: #FFE14D; }
.fita .travou { background: #FFFFFF; color: #B3261E; border-color: #B3261E; text-decoration: line-through; }
@media (prefers-reduced-motion: reduce) { .fita span { transition: none; } }

.passo-titulo { font-size: 1.75rem; font-weight: 700; margin: 0 0 .75rem; }
.fatos { margin: 0 0 1rem; padding: 0 !important; font-size: 1.15rem; }
.fatos div { display: flex; justify-content: space-between; align-items: baseline; gap: 1rem; padding: .5rem 0; border-bottom: 1px solid #B9C0D3; }
.fatos dt { font-weight: 400; color: #39405A; }
.fatos dd { margin: 0; font: 700 1.3rem "JetBrains Mono", Consolas, monospace; }
.fatos dd.vivo { background: #FFE14D; padding: 0 .45rem; }
.veredito { padding: .7rem .9rem; font-size: 1.1rem; font-weight: 700; margin-bottom: 1rem; }
.veredito.aceita { background: #C9F2D8; }
.veredito.rejeita { background: #FFD6D2; }

@media (max-width: 640px) {
  [data-testid="stMainBlockContainer"] { padding-inline: 1rem; }
  .fita span { width: 2.6rem; height: 3rem; font-size: 1.25rem; }
}
</style>
"""


def html_destacado(texto: str, tokens: list[Token]) -> str:
    """Marca os tokens no texto; todo conteúdo do usuário passa por escape."""
    partes = []
    posicao = 0
    for token in tokens:
        partes.append(html.escape(texto[posicao:token.inicio]))
        cor = CORES_TOKENS.get(token.tipo, "#FFFFFF")
        classe = ' class="escuro"' if token.tipo == PERSONALIZADO else ""
        tipo = token.tipo
        if token.digitos_validos is False:
            tipo += " inválido"
        partes.append(
            f'<mark{classe} style="--caneta:{cor}">{html.escape(token.texto)}'
            f'<span class="tipo">{html.escape(tipo)}</span></mark>'
        )
        posicao = token.fim
    partes.append(html.escape(texto[posicao:]))
    return f'<div class="documento">{"".join(partes)}</div>'


def html_fita(cadeia: str, lidos: int, travou: bool = False) -> str:
    """Desenha a cadeia em células: lidas, atual e ainda não lidas."""
    celulas = []
    for indice, simbolo in enumerate(cadeia):
        classe = ""
        if indice < lidos - 1:
            classe = ' class="lido"'
        elif indice == lidos - 1:
            classe = ' class="travou"' if travou else ' class="atual"'
        celulas.append(f"<span{classe}>{html.escape(formatar_simbolo(ord(simbolo)))}</span>")
    return f'<div class="fita" aria-label="Cadeia, {lidos} de {len(cadeia)} símbolos lidos">{"".join(celulas)}</div>'


def linhas_da_tabela(tokens: list[Token]) -> list[dict[str, str]]:
    validade = {True: "Válidos", False: "Inválidos", None: "Não se aplica"}
    return [
        {
            "Texto": token.texto,
            "Tipo": token.tipo,
            "Posição": f"{token.inicio}–{token.fim}",
            "Dígitos": validade[token.digitos_validos],
        }
        for token in tokens
    ]


def html_tabela(tokens: list[Token]) -> str:
    """Tabela em HTML, pois ``st.dataframe`` exige o pyarrow."""
    linhas = []
    for token, linha in zip(tokens, linhas_da_tabela(tokens)):
        cor = CORES_TOKENS.get(token.tipo, "#FFFFFF")
        classe = " escuro" if token.tipo == PERSONALIZADO else ""
        linhas.append(
            f'<tr><td class="dado">{html.escape(linha["Texto"])}</td>'
            f'<td class="tipo{classe}" style="--caneta:{cor}">{html.escape(linha["Tipo"])}</td>'
            f'<td class="dado">{linha["Posição"]}</td>'
            f"<td>{linha['Dígitos']}</td></tr>"
        )
    return (
        '<div class="tabela"><table class="tokens"><thead><tr><th scope="col">Texto</th>'
        '<th scope="col">Tipo</th><th scope="col">Posição</th><th scope="col">Dígitos</th>'
        f'</tr></thead><tbody>{"".join(linhas)}</tbody></table></div>'
    )


def situacao_do_passo(afd: AFD, registros: list, indice: int) -> dict:
    """Traduz o registro da simulação no que a tela precisa mostrar."""
    situacao = {"origem": None, "simbolo": None, "estado": afd.inicial, "travou": False}
    if indice > 0:
        origem, simbolo, destino = registros[indice - 1]
        travou = destino is None
        situacao.update(
            origem=origem,
            simbolo=formatar_simbolo(ord(simbolo)),
            estado=origem if travou else destino,
            travou=travou,
        )
    return situacao


@st.cache_resource(show_spinner=False)
def compilar_tokenizador(definicoes: tuple[tuple[str, str, bool], ...]) -> Tokenizador:
    return Tokenizador(Padrao(*definicao) for definicao in definicoes)


@st.cache_resource(show_spinner=False)
def construir_etapas(expressao: str):
    afn = construir_afn(parse(expressao))
    afd = construir_afd(afn)
    return {"AFN": afn, "AFD": afd, "AFD mínimo": minimizar(afd)}


def mostrar_erro_de_padrao(erro: ErroDeSintaxe, expressao: str) -> None:
    st.error(f"Padrão inválido na posição {erro.posicao}: {erro.mensagem}.")
    st.code(f"{expressao}\n{' ' * erro.posicao}^", language=None)


def validar_personalizado(expressao: str) -> bool:
    if not expressao:
        return False
    try:
        parse(expressao)
    except ErroDeSintaxe as erro:
        mostrar_erro_de_padrao(erro, expressao)
        return False
    return True


def renderizar_extracao() -> None:
    coluna_texto, coluna_padroes = st.columns([3, 2], gap="large")
    with coluna_texto:
        texto = st.text_area("Texto de entrada", TEXTO_EXEMPLO, height=170, key="texto")
    with coluna_padroes:
        nomes = [padrao.nome for padrao in PADROES]
        ativos = st.pills(
            "Padrões ativos", nomes, default=nomes, selection_mode="multi", key="padroes_ativos", wrap=True
        )
        personalizado = st.text_input(
            "Padrão personalizado",
            key="padrao_personalizado",
            placeholder=r"Por exemplo: [A-Z]{3}-\d{4}",
            help="Tem prioridade sobre os demais padrões.",
        )

    definicoes = [
        (padrao.nome, padrao.expressao, padrao.fronteira_numerica)
        for padrao in PADROES
        if padrao.nome in ativos
    ]
    if validar_personalizado(personalizado):
        definicoes.append((PERSONALIZADO, personalizado, False))

    if not texto:
        st.html('<p class="vazio">Cole um texto para ver os dados encontrados.</p>')
        return
    if not definicoes:
        st.html('<p class="vazio">Ative ao menos um padrão para analisar o texto.</p>')
        return

    tokens = validar_documentos(compilar_tokenizador(tuple(definicoes)).tokenizar(texto))
    if not tokens:
        st.html('<p class="vazio">Nenhum dado reconhecido com os padrões ativos.</p>')
        return

    coluna_marcado, coluna_limpo = st.columns(2, gap="large")
    with coluna_marcado:
        st.subheader("Texto marcado")
        st.html(html_destacado(texto, tokens))
    with coluna_limpo:
        st.subheader("Texto sanitizado")
        tipos = list(dict.fromkeys(token.tipo for token in tokens))
        regras = {}
        colunas_regras = st.columns(4)
        for indice, tipo in enumerate(tipos):
            with colunas_regras[indice % 4]:
                escolha = st.selectbox(tipo, list(REGRAS), key=f"regra_{tipo}")
                regras[tipo] = REGRAS[escolha]
        st.code(sanitizar(texto, tokens, regras), language=None, wrap_lines=True)

    coluna_titulo, coluna_baixar = st.columns([4, 1], vertical_alignment="center")
    with coluna_titulo:
        st.subheader(f"Tokens encontrados: {len(tokens)}")
    with coluna_baixar:
        st.download_button(
            "Baixar JSON",
            exportar_json(tokens),
            file_name="dados_extraidos.json",
            mime="application/json",
            width="stretch",
        )
    st.html(html_tabela(tokens))


def mover_passo(delta: int, total: int) -> None:
    st.session_state.passo = max(0, min(total, st.session_state.passo + delta))


def renderizar_automatos() -> None:
    coluna_padrao, coluna_expressao, coluna_cadeia = st.columns([1, 2, 2], gap="medium")
    opcoes = ["Personalizado", *(padrao.nome for padrao in PADROES)]
    with coluna_padrao:
        escolha = st.selectbox("Padrão", opcoes, key="padrao_automato")
    with coluna_expressao:
        if escolha == "Personalizado":
            expressao = st.text_input("Expressão regular", PADRAO_EXEMPLO, key="expressao_automato")
        else:
            expressao = next(padrao.expressao for padrao in PADROES if padrao.nome == escolha)
            st.text_input("Expressão regular", expressao, disabled=True, key=f"expressao_{escolha}")
    with coluna_cadeia:
        cadeia = st.text_input("Cadeia", CADEIA_EXEMPLO, key="cadeia_automato")

    try:
        etapas = construir_etapas(expressao)
    except ErroDeSintaxe as erro:
        mostrar_erro_de_padrao(erro, expressao)
        return

    coluna_er, coluna_etapas = st.columns([1, 3], gap="small")
    with coluna_er:
        st.html(f'<div class="etapa-er">ER · {html.escape(expressao) or "ε"}</div>')
    with coluna_etapas:
        etapa = st.segmented_control(
            "Etapa do pipeline",
            ETAPAS,
            default="AFD mínimo",
            format_func=lambda nome: f"{nome} · {etapas[nome].num_estados} estados",
            label_visibility="collapsed",
            key="etapa_automato",
            width="stretch",
            wrap=True,
        ) or "AFD mínimo"

    automato = etapas[etapa]
    nomes = [PERSONALIZADO if escolha == "Personalizado" else escolha]
    registros = [] if etapa == "AFN" else passos(automato, cadeia)
    total = len(registros)

    assinatura = (expressao, etapa, cadeia)
    if st.session_state.get("assinatura_passo") != assinatura:
        st.session_state.assinatura_passo = assinatura
        st.session_state.passo = 0
    indice = st.session_state.passo = min(st.session_state.get("passo", 0), total)

    situacao = None if etapa == "AFN" else situacao_do_passo(automato, registros, indice)
    coluna_diagrama, coluna_passo = st.columns([5, 2], gap="large")
    with coluna_diagrama:
        if automato.num_estados > LIMITE_ESTADOS_DIAGRAMA:
            st.warning(
                f"Este autômato tem {automato.num_estados} estados, acima do limite de "
                f"{LIMITE_ESTADOS_DIAGRAMA} para desenhar o diagrama no navegador."
            )
        elif etapa == "AFN":
            st.graphviz_chart(afn_para_dot(automato), width="stretch")
        else:
            st.graphviz_chart(
                afd_para_dot(
                    automato,
                    destaque=situacao["estado"],
                    nomes_tokens=nomes,
                    mostrar_estados_afn=etapa == "AFD",
                ),
                width="stretch",
            )
        if etapa != "AFN" and cadeia:
            st.html(html_fita(cadeia, indice, situacao["travou"]))

    with coluna_passo:
        if etapa == "AFN":
            st.html(
                '<p class="vazio">A execução passo a passo roda no AFD. '
                "Selecione AFD ou AFD mínimo na faixa acima.</p>"
            )
            return
        renderizar_painel_do_passo(automato, situacao, indice, total, len(cadeia))


def renderizar_painel_do_passo(afd: AFD, situacao: dict, indice: int, total: int, tamanho: int) -> None:
    linhas = [f'<p class="passo-titulo">Passo {indice} de {total}</p><dl class="fatos">']
    linhas.append(f'<div><dt>Estado atual</dt><dd class="vivo">{situacao["estado"]}</dd></div>')
    simbolo = html.escape(situacao["simbolo"]) if situacao["simbolo"] is not None else "–"
    linhas.append(f"<div><dt>Símbolo lido</dt><dd>{simbolo}</dd></div>")
    origem = situacao["origem"] if situacao["origem"] is not None else "–"
    linhas.append(f"<div><dt>Veio do estado</dt><dd>{origem}</dd></div></dl>")

    if indice == total:
        if situacao["travou"]:
            linhas.append(
                f'<div class="veredito rejeita">Cadeia rejeitada: o AFD travou no símbolo {indice} de {tamanho}.</div>'
            )
        elif situacao["estado"] in afd.aceitacao:
            linhas.append(
                f'<div class="veredito aceita">Cadeia aceita: o estado {situacao["estado"]} é de aceitação.</div>'
            )
        else:
            linhas.append(
                f'<div class="veredito rejeita">Cadeia rejeitada: o estado {situacao["estado"]} não é de aceitação.</div>'
            )
    st.html("".join(linhas))

    anterior, proximo = st.columns(2)
    with anterior:
        st.button(
            "Anterior", key="passo_anterior", disabled=indice == 0, width="stretch",
            on_click=mover_passo, args=(-1, total),
        )
    with proximo:
        st.button(
            "Próximo", key="passo_proximo", type="primary", disabled=indice == total, width="stretch",
            on_click=mover_passo, args=(1, total),
        )
    st.button(
        "Voltar ao início", key="passo_inicio", disabled=indice == 0, width="stretch",
        on_click=mover_passo, args=(-indice, total),
    )


def main() -> None:
    st.set_page_config(page_title="Motor de Regex", layout="wide")
    st.html(ESTILO)
    st.html(
        '<header class="tarja"><h1>Motor de Regex</h1>'
        "<p>Da expressão regular ao AFD mínimo, sem biblioteca de regex</p></header>"
    )
    aba_extracao, aba_automatos = st.tabs(["Extração", "Autômatos"])
    with aba_extracao:
        renderizar_extracao()
    with aba_automatos:
        renderizar_automatos()


if __name__ == "__main__":
    main()
