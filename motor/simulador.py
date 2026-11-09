"""Simulação de AFDs parciais com transições por intervalos."""

from __future__ import annotations

from bisect import bisect_right

from motor.automatos import AFD


def _transicao(afd: AFD, estado: int, simbolo: str) -> int | None:
    saidas = afd.saidas(estado)
    codigo = ord(simbolo)
    posicao = bisect_right(saidas, ((codigo, float("inf")), float("inf"))) - 1
    if posicao >= 0 and saidas[posicao][0][1] >= codigo:
        return saidas[posicao][1]
    return None


def aceita(afd: AFD, cadeia: str) -> bool:
    estado = afd.inicial
    for simbolo in cadeia:
        estado = _transicao(afd, estado, simbolo)
        if estado is None:
            return False
    return estado in afd.aceitacao


def maior_casamento(afd: AFD, texto: str, inicio: int) -> tuple[int, int] | None:
    """Retorna o fim exclusivo e o token da última aceitação a partir de inicio."""
    if not 0 <= inicio <= len(texto):
        raise ValueError("início fora do texto")
    estado = afd.inicial
    ultimo = (inicio, afd.aceitacao[estado]) if estado in afd.aceitacao else None
    for posicao in range(inicio, len(texto)):
        estado = _transicao(afd, estado, texto[posicao])
        if estado is None:
            break
        if estado in afd.aceitacao:
            ultimo = (posicao + 1, afd.aceitacao[estado])
    return ultimo


def passos(afd: AFD, cadeia: str) -> list[tuple[int, str, int | None]]:
    """Registra (estado, símbolo, destino), incluindo o passo que trava o AFD."""
    resultado = []
    estado = afd.inicial
    for simbolo in cadeia:
        destino = _transicao(afd, estado, simbolo)
        resultado.append((estado, simbolo, destino))
        if destino is None:
            break
        estado = destino
    return resultado
