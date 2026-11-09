"""Minimização de autômatos finitos determinísticos (AFD).

Remove estados inalcançáveis e não produtivos, e refina partições preservando
as categorias de tokens (menor id_token) e transições por intervalos.
"""

from __future__ import annotations

from typing import Any

from motor.automatos import AFD, Intervalo


def _assinatura_transicoes(
    afd: AFD,
    estado: int,
    bloco_id: dict[int, int],
    uteis: set[int],
) -> tuple[tuple[Intervalo, int], ...]:
    """Calcula a assinatura normalizada de transições de um estado para os blocos da partição."""
    saidas_uteis = []
    for inter, dest in afd.saidas(estado):
        if dest in uteis:
            saidas_uteis.append((inter, bloco_id[dest]))

    # Mesclar intervalos adjacentes que levam ao mesmo bloco
    saidas_mescladas: list[tuple[Intervalo, int]] = []
    for inter, b_dest in saidas_uteis:
        if (
            saidas_mescladas
            and saidas_mescladas[-1][1] == b_dest
            and saidas_mescladas[-1][0][1] + 1 == inter[0]
        ):
            ant_inter, ant_dest = saidas_mescladas[-1]
            saidas_mescladas[-1] = ((ant_inter[0], inter[1]), ant_dest)
        else:
            saidas_mescladas.append((inter, b_dest))

    return tuple(saidas_mescladas)


def minimizar(afd: AFD) -> AFD:
    """Minimiza um AFD parcial.

    - Remove estados inalcançáveis a partir do estado inicial.
    - Remove estados que não alcançam nenhum estado de aceitação (não produtivos).
    - Refina partições (Moore) iniciando pela separação por ``id_token`` para
      não misturar tokens diferentes.
    - Unifica intervalos adjacentes que levam ao mesmo bloco.
    - Preserva o mapeamento de ``estados_afn`` agregando os conjuntos dos estados fundidos.
    """
    afd.validar()

    # 1. Estados alcançáveis a partir do inicial
    alcancaveis = set()
    pilha = [afd.inicial]
    while pilha:
        s = pilha.pop()
        if s not in alcancaveis:
            alcancaveis.add(s)
            for _, dest in afd.saidas(s):
                if dest not in alcancaveis:
                    pilha.append(dest)

    # 2. Estados produtivos (alcançam aceitação)
    reverso: dict[int, list[int]] = {}
    for s in alcancaveis:
        for _, dest in afd.saidas(s):
            if dest in alcancaveis:
                reverso.setdefault(dest, []).append(s)

    produtivos = set(s for s in afd.aceitacao if s in alcancaveis)
    pilha = list(produtivos)
    while pilha:
        s = pilha.pop()
        for anterior in reverso.get(s, ()):
            if anterior not in produtivos:
                produtivos.add(anterior)
                pilha.append(anterior)

    uteis = alcancaveis & produtivos

    # Se o inicial não for útil, a linguagem aceita é vazia
    if afd.inicial not in uteis:
        min_afd = AFD(num_estados=1, inicial=0)
        min_afd.validar()
        return min_afd

    # 3. Partição inicial separando por id_token
    # Não aceitação mapeia para None; cada id_token forma uma partição separada
    grupos: dict[Any, list[int]] = {}
    for s in sorted(uteis):
        chave = afd.aceitacao.get(s, None)
        grupos.setdefault(chave, []).append(s)

    particao: list[list[int]] = list(grupos.values())

    # 4. Refinamento de partição (Moore)
    while True:
        bloco_id = {s: idx for idx, bloco in enumerate(particao) for s in bloco}
        nova_particao: list[list[int]] = []
        houve_divisao = False

        for bloco in particao:
            if len(bloco) <= 1:
                nova_particao.append(bloco)
                continue

            sub_grupos: dict[tuple[tuple[Intervalo, int], ...], list[int]] = {}
            for s in bloco:
                sig = _assinatura_transicoes(afd, s, bloco_id, uteis)
                sub_grupos.setdefault(sig, []).append(s)

            if len(sub_grupos) > 1:
                houve_divisao = True
            nova_particao.extend(sub_grupos.values())

        if not houve_divisao:
            break
        particao = nova_particao

    # 5. Construção do AFD mínimo
    # O bloco contendo afd.inicial deve ser o estado 0
    idx_inicial = None
    for i, bloco in enumerate(particao):
        if afd.inicial in bloco:
            idx_inicial = i
            break
    assert idx_inicial is not None

    blocos_finais = [particao[idx_inicial]] + [
        bloco for i, bloco in enumerate(particao) if i != idx_inicial
    ]

    min_afd = AFD()
    mapa_novo = {}

    for novo_estado, bloco in enumerate(blocos_finais):
        afn_conjunto = set()
        for s in bloco:
            afn_conjunto.update(afd.estados_afn.get(s, ()))
        min_afd.novo_estado(afn_conjunto)
        for s in bloco:
            mapa_novo[s] = novo_estado

        rep = bloco[0]
        if rep in afd.aceitacao:
            min_afd.aceitacao[novo_estado] = afd.aceitacao[rep]

    min_afd.inicial = 0

    for novo_estado, bloco in enumerate(blocos_finais):
        rep = bloco[0]
        saidas_uteis = []
        for inter, dest in afd.saidas(rep):
            if dest in uteis:
                saidas_uteis.append((inter, mapa_novo[dest]))

        saidas_mescladas: list[tuple[Intervalo, int]] = []
        for inter, d in saidas_uteis:
            if (
                saidas_mescladas
                and saidas_mescladas[-1][1] == d
                and saidas_mescladas[-1][0][1] + 1 == inter[0]
            ):
                ant_inter, ant_dest = saidas_mescladas[-1]
                saidas_mescladas[-1] = ((ant_inter[0], inter[1]), ant_dest)
            else:
                saidas_mescladas.append((inter, d))

        for inter, d in saidas_mescladas:
            min_afd.adicionar_transicao(novo_estado, inter, d)

    min_afd.validar()
    return min_afd
