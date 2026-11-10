"""Geração de diagramas Graphviz DOT para AFN e AFD."""

from __future__ import annotations

from typing import Iterable, Optional, Sequence

from motor.automatos import (
    AFD,
    AFN,
    MAX_CODEPOINT,
    Intervalo,
    complementar_intervalos,
    formatar_intervalo,
    normalizar_intervalos,
)
from motor.parser import ESPACOS, PALAVRA

ROTULO_EPSILON = "ε"
LARGURA_MAXIMA_ROTULO = 18
ESTADOS_AFN_POR_LINHA = 6

COR_TINTA = "#14182B"
COR_SECUNDARIA = "#4A5168"
COR_FUNDO_ESTADO = "#FFFFFF"
COR_INICIAL = "#DDE3F3"
COR_ACEITACAO = "#C9F2D8"
COR_DESTAQUE = "#FFE14D"
FONTE_DIAGRAMA = "JetBrains Mono, Consolas, monospace"

_NOMES_DE_CLASSE = {PALAVRA: r"\w", ESPACOS: r"\s"}


def rotulo_intervalos(intervalos: Iterable[Intervalo]) -> str:
    """Rótulo legível de uma transição: ``0-9``, ``a-z``, ``\\w`` ou ``[^...]``."""
    normalizados = normalizar_intervalos(intervalos)
    if normalizados == ((0, MAX_CODEPOINT),):
        return "qualquer"
    if normalizados in _NOMES_DE_CLASSE:
        return _NOMES_DE_CLASSE[normalizados]

    complemento = complementar_intervalos(normalizados)
    if complemento in _NOMES_DE_CLASSE:
        return f"[^{_NOMES_DE_CLASSE[complemento]}]"
    if len(complemento) < len(normalizados) or (
        normalizados[0][0] == 0 and normalizados[-1][1] == MAX_CODEPOINT
    ):
        return f"[^{_juntar_intervalos(complemento)}]"
    return _juntar_intervalos(normalizados)


def afn_para_dot(afn: AFN) -> str:
    """Gera o DOT de um AFN, agrupando intervalos de mesma origem e destino."""
    linhas = _cabecalho("AFN", "circle", afn.inicial)
    for estado in range(afn.num_estados):
        linhas.append(_no(estado, str(estado), estado == afn.inicial, estado in afn.aceitacao))

    arestas: dict[tuple[int, int], list[Intervalo]] = {}
    arestas_vazias: set[tuple[int, int]] = set()
    for origem, saidas in afn.transicoes.items():
        for intervalo, destino in saidas:
            if intervalo is None:
                arestas_vazias.add((origem, destino))
            else:
                arestas.setdefault((origem, destino), []).append(intervalo)

    for origem, destino in sorted(arestas_vazias):
        linhas.append(_aresta(origem, destino, ROTULO_EPSILON))
    for (origem, destino), intervalos in sorted(arestas.items()):
        linhas.append(_aresta(origem, destino, rotulo_intervalos(intervalos)))
    linhas.append("}")
    return "\n".join(linhas)


def afd_para_dot(
    afd: AFD,
    destaque: Optional[int] = None,
    nomes_tokens: Optional[Sequence[str]] = None,
    mostrar_estados_afn: bool = True,
) -> str:
    """Gera o DOT de um AFD.

    ``destaque`` marca o estado atual no modo passo a passo. ``nomes_tokens``
    traduz ``id_token`` para o nome do padrão. ``mostrar_estados_afn`` deve ser
    falso no AFD mínimo, cujos estados fundem subconjuntos diferentes.
    """
    if destaque is not None and not 0 <= destaque < afd.num_estados:
        raise ValueError(f"estado de destaque {destaque} fora de 0..{afd.num_estados - 1}")

    forma = "ellipse" if mostrar_estados_afn and afd.estados_afn else "circle"
    linhas = _cabecalho("AFD", forma, afd.inicial)
    for estado in range(afd.num_estados):
        partes = [str(estado)]
        if mostrar_estados_afn and estado in afd.estados_afn:
            partes.extend(_linhas_do_conjunto(afd.estados_afn[estado]))
        token = None
        if estado in afd.aceitacao:
            token = _nome_token(afd.aceitacao[estado], nomes_tokens)
        linhas.append(
            _no(
                estado,
                partes,
                estado == afd.inicial,
                estado in afd.aceitacao,
                estado == destaque,
                token,
            )
        )

    arestas: dict[tuple[int, int], list[Intervalo]] = {}
    for origem, saidas in afd.transicoes.items():
        for intervalo, destino in saidas:
            arestas.setdefault((origem, destino), []).append(intervalo)
    for (origem, destino), intervalos in sorted(arestas.items()):
        linhas.append(_aresta(origem, destino, rotulo_intervalos(intervalos)))
    linhas.append("}")
    return "\n".join(linhas)


def _juntar_intervalos(intervalos: Iterable[Intervalo]) -> str:
    linhas: list[str] = []
    atual = ""
    for intervalo in intervalos:
        parte = formatar_intervalo(intervalo)
        if atual and len(atual) + len(parte) + 1 > LARGURA_MAXIMA_ROTULO:
            linhas.append(atual)
            atual = parte
        else:
            atual = f"{atual} {parte}" if atual else parte
    linhas.append(atual)
    return "\n".join(linhas)


def _linhas_do_conjunto(estados: Iterable[int]) -> list[str]:
    ordenados = sorted(estados)
    blocos = [
        ",".join(str(estado) for estado in ordenados[i:i + ESTADOS_AFN_POR_LINHA])
        for i in range(0, len(ordenados), ESTADOS_AFN_POR_LINHA)
    ]
    blocos[0] = "{" + blocos[0]
    blocos[-1] += "}"
    return blocos


def _nome_token(id_token: int, nomes_tokens: Optional[Sequence[str]]) -> str:
    if nomes_tokens is not None and 0 <= id_token < len(nomes_tokens):
        return nomes_tokens[id_token]
    return f"token {id_token}"


def _escapar(texto: str) -> str:
    return texto.replace("\\", "\\\\").replace('"', '\\"')


def _rotulo_dot(partes: str | Sequence[str]) -> str:
    linhas = partes.split("\n") if isinstance(partes, str) else partes
    return "\\n".join(_escapar(linha) for linha in linhas)


def _cabecalho(nome: str, forma: str, inicial: int) -> list[str]:
    return [
        f"digraph {nome} {{",
        '  rankdir=LR; bgcolor="transparent"; nodesep=0.4; ranksep=0.4; forcelabels=true;',
        f'  node [shape={forma}, style=filled, fillcolor="{COR_FUNDO_ESTADO}", '
        f'color="{COR_TINTA}", fontcolor="{COR_TINTA}", penwidth=1.6, '
        f'fontname="{FONTE_DIAGRAMA}", fontsize=19];',
        f'  edge [color="{COR_SECUNDARIA}", fontcolor="{COR_TINTA}", arrowsize=0.8, '
        f'fontname="{FONTE_DIAGRAMA}", fontsize=18];',
        f'  "inicio" [shape=plaintext, style="", label="início", fontcolor="{COR_SECUNDARIA}"];',
        f'  "inicio" -> "{inicial}";',
    ]


def _no(
    estado: int,
    rotulo: str | Sequence[str],
    inicial: bool,
    aceitacao: bool,
    destacado: bool = False,
    token: Optional[str] = None,
) -> str:
    atributos = [f'label="{_rotulo_dot(rotulo)}"']
    if aceitacao:
        atributos.append("peripheries=2")
    if token is not None:
        atributos.append(f'xlabel="{_rotulo_dot(token)}"')
    if destacado:
        atributos.extend([f'fillcolor="{COR_DESTAQUE}"', "penwidth=3.5"])
    elif aceitacao:
        atributos.append(f'fillcolor="{COR_ACEITACAO}"')
    elif inicial:
        atributos.append(f'fillcolor="{COR_INICIAL}"')
    return f'  "{estado}" [{", ".join(atributos)}];'


def _aresta(origem: int, destino: int, rotulo: str) -> str:
    return f'  "{origem}" -> "{destino}" [label="{_rotulo_dot(rotulo)}"];'
