"""Construção de subconjuntos: conversão de AFN em AFD parcial.

Converte um autômato finito com movimentos vazios (AFN-ε) em um autômato
finito determinístico (AFD) parcial sobre o alfabeto Unicode.
"""

from __future__ import annotations

from collections import deque
from typing import Iterable, Union

from motor.automatos import AFD, AFN, Intervalo


def particionar_intervalos(intervalos: Iterable[Intervalo]) -> list[Intervalo]:
    """Divide um conjunto de intervalos em intervalos atômicos disjuntos.

    Coleta os limites dos intervalos de entrada e fatia o espaço coberto
    em intervalos disjuntos onde cada símbolo pertence ao mesmo conjunto de
    intervalos originais.

    Exemplo:
        [(97, 109), (104, 122)] -> [(97, 103), (104, 109), (110, 122)]
    """
    intervalos_lista = list(intervalos)
    if not intervalos_lista:
        return []

    cortes = set()
    for inicio, fim in intervalos_lista:
        cortes.add(inicio)
        cortes.add(fim + 1)

    pontos = sorted(cortes)
    atomicos: list[Intervalo] = []

    for i in range(len(pontos) - 1):
        p_ini = pontos[i]
        p_fim = pontos[i + 1] - 1
        if p_ini <= p_fim:
            # Mantém apenas os intervalos que pertencem à união dos intervalos originais
            if any(inicio <= p_ini <= fim for inicio, fim in intervalos_lista):
                atomicos.append((p_ini, p_fim))

    return atomicos


def epsilon_fecho(
    arg1: Union[AFN, Iterable[int], int],
    arg2: Union[AFN, Iterable[int], int] = None,
) -> frozenset[int]:
    """Calcula o fecho-ε de um conjunto de estados no AFN.

    Suporta tanto ``epsilon_fecho(afn, estados)`` quanto
    ``epsilon_fecho(estados, afn)``, bem como um único estado inteiro.
    """
    if isinstance(arg1, AFN):
        afn = arg1
        estados = arg2 if arg2 is not None else ()
    elif isinstance(arg2, AFN):
        estados = arg1
        afn = arg2
    else:
        raise TypeError("É necessário fornecer uma instância de AFN para epsilon_fecho.")

    if isinstance(estados, int):
        estados = [estados]

    fecho = set(estados)
    pilha = list(estados)
    while pilha:
        atual = pilha.pop()
        for rotulo, destino in afn.saidas(atual):
            if rotulo is None and destino not in fecho:
                fecho.add(destino)
                pilha.append(destino)

    return frozenset(fecho)


def mover(
    arg1: Union[AFN, Iterable[int], int],
    arg2: Union[Iterable[int], int, Intervalo, str],
    arg3: Union[AFN, Intervalo, int, str] = None,
) -> frozenset[int]:
    """Retorna os estados alcançáveis a partir de ``estados`` pelo ``intervalo``.

    Suporta tanto ``mover(afn, estados, intervalo)`` quanto
    ``mover(estados, intervalo, afn)``. O intervalo pode ser uma tupla
    ``(inicio, fim)``, um caractere único ou um code point inteiro.
    """
    if isinstance(arg1, AFN):
        afn = arg1
        estados = arg2
        intervalo = arg3
    elif isinstance(arg3, AFN):
        estados = arg1
        intervalo = arg2
        afn = arg3
    else:
        raise TypeError("É necessário fornecer uma instância de AFN para mover.")

    if isinstance(estados, int):
        estados = [estados]

    if isinstance(intervalo, str):
        if len(intervalo) != 1:
            raise ValueError("Símbolo caractere deve ter comprimento 1.")
        c = ord(intervalo)
        i_inicio, i_fim = c, c
    elif isinstance(intervalo, int):
        i_inicio, i_fim = intervalo, intervalo
    elif isinstance(intervalo, tuple) and len(intervalo) == 2:
        i_inicio, i_fim = intervalo
    else:
        raise ValueError(f"Intervalo ou símbolo inválido: {intervalo}")

    resultado = set()
    for estado in estados:
        for rotulo, destino in afn.saidas(estado):
            if rotulo is not None:
                r_inicio, r_fim = rotulo
                if r_inicio <= i_inicio and i_fim <= r_fim:
                    resultado.add(destino)

    return frozenset(resultado)


def construir_afd(afn: AFN) -> AFD:
    """Converte um AFN em um AFD parcial usando a construção de subconjuntos.

    - Particiona o alfabeto a partir dos intervalos de saída de cada conjunto
      de estados, sem nunca enumerar os símbolos Unicode um a um.
    - Une intervalos adjacentes que levam ao mesmo estado de destino.
    - O AFD permanece parcial (não cria estado para conjunto vazio).
    - Desempata aceitações múltiplas pelo menor ``id_token``.
    - Registra em ``estados_afn`` o subconjunto de estados do AFN representado
      por cada estado do AFD.
    """
    afn.validar()
    afd = AFD()

    inicial_fecho = epsilon_fecho(afn, [afn.inicial])
    estado_inicial = afd.novo_estado(inicial_fecho)
    afd.inicial = estado_inicial

    tokens_inicial = [afn.aceitacao[q] for q in inicial_fecho if q in afn.aceitacao]
    if tokens_inicial:
        afd.aceitacao[estado_inicial] = min(tokens_inicial)

    subconjuntos: dict[frozenset[int], int] = {inicial_fecho: estado_inicial}
    fila = deque([inicial_fecho])

    while fila:
        atual_fecho = fila.popleft()
        u_afd = subconjuntos[atual_fecho]

        intervalos_saida = []
        for q in atual_fecho:
            for rotulo, _ in afn.saidas(q):
                if rotulo is not None:
                    intervalos_saida.append(rotulo)

        if not intervalos_saida:
            continue

        atomicos = particionar_intervalos(intervalos_saida)

        transicoes_brutas: list[tuple[Intervalo, int]] = []
        for inter in atomicos:
            destinos = mover(afn, atual_fecho, inter)
            if not destinos:
                continue
            dest_fecho = epsilon_fecho(afn, destinos)
            if not dest_fecho:
                continue

            if dest_fecho not in subconjuntos:
                v_afd = afd.novo_estado(dest_fecho)
                subconjuntos[dest_fecho] = v_afd
                tokens_dest = [afn.aceitacao[q] for q in dest_fecho if q in afn.aceitacao]
                if tokens_dest:
                    afd.aceitacao[v_afd] = min(tokens_dest)
                fila.append(dest_fecho)
            else:
                v_afd = subconjuntos[dest_fecho]

            transicoes_brutas.append((inter, v_afd))

        # Unir intervalos adjacentes que levam ao mesmo destino
        if transicoes_brutas:
            transicoes_mescladas: list[tuple[Intervalo, int]] = []
            for inter, dest in transicoes_brutas:
                if (
                    transicoes_mescladas
                    and transicoes_mescladas[-1][1] == dest
                    and transicoes_mescladas[-1][0][1] + 1 == inter[0]
                ):
                    ant_inter, ant_dest = transicoes_mescladas[-1]
                    transicoes_mescladas[-1] = ((ant_inter[0], inter[1]), ant_dest)
                else:
                    transicoes_mescladas.append((inter, dest))

            for inter, dest in transicoes_mescladas:
                afd.adicionar_transicao(u_afd, inter, dest)

    afd.validar()
    return afd
