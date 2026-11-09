"""Estruturas AFN e AFD"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional

MAX_CODEPOINT = 0x10FFFF
"""Maior code point Unicode. O alfabeto é ``0 .. MAX_CODEPOINT``."""

Intervalo = tuple[int, int]
"""Par ``(inicio, fim)`` de code points, inclusivo nas duas pontas."""

EPSILON = None
"""Rótulo de transição vazia (ε) no AFN."""

ID_TOKEN_PADRAO = 0
"""``id_token`` usado quando há um único padrão."""


# ---------------------------------------------------------------------------
# Funções auxiliares sobre intervalos
# ---------------------------------------------------------------------------

def normalizar_intervalos(intervalos: Iterable[Intervalo]) -> tuple[Intervalo, ...]:
    """Ordena e funde intervalos sobrepostos ou adjacentes.

    >>> normalizar_intervalos([(100, 120), (97, 99), (110, 130)])
    ((97, 130),)
    """
    lista = []
    for inicio, fim in intervalos:
        if not (0 <= inicio <= fim <= MAX_CODEPOINT):
            raise ValueError(f"intervalo inválido: ({inicio}, {fim})")
        lista.append((inicio, fim))
    lista.sort()

    resultado: list[Intervalo] = []
    for inicio, fim in lista:
        if resultado and inicio <= resultado[-1][1] + 1:
            ultimo_inicio, ultimo_fim = resultado[-1]
            resultado[-1] = (ultimo_inicio, max(ultimo_fim, fim))
        else:
            resultado.append((inicio, fim))
    return tuple(resultado)


def complementar_intervalos(intervalos: Iterable[Intervalo]) -> tuple[Intervalo, ...]:
    """Retorna os intervalos de ``0 .. MAX_CODEPOINT`` que NÃO estão na entrada."""
    resultado: list[Intervalo] = []
    proximo = 0
    for inicio, fim in normalizar_intervalos(intervalos):
        if inicio > proximo:
            resultado.append((proximo, inicio - 1))
        proximo = fim + 1
    if proximo <= MAX_CODEPOINT:
        resultado.append((proximo, MAX_CODEPOINT))
    return tuple(resultado)


_NOMES_ESPECIAIS = {
    ord("\n"): "\\n",
    ord("\t"): "\\t",
    ord("\r"): "\\r",
    ord("\f"): "\\f",
    ord("\v"): "\\v",
    ord(" "): "␠",
    ord("\\"): "\\\\",
}


def formatar_simbolo(codigo: int) -> str:
    """Texto legível para um code point (usado em diagramas e mensagens)."""
    if codigo in _NOMES_ESPECIAIS:
        return _NOMES_ESPECIAIS[codigo]
    caractere = chr(codigo)
    if caractere.isprintable():
        return caractere
    return f"U+{codigo:04X}"


def formatar_intervalo(intervalo: Intervalo) -> str:
    """``(48, 57)`` -> ``'0-9'``; ``(97, 97)`` -> ``'a'``."""
    inicio, fim = intervalo
    if inicio == fim:
        return formatar_simbolo(inicio)
    return f"{formatar_simbolo(inicio)}-{formatar_simbolo(fim)}"


def formatar_intervalos(intervalos: Iterable[Intervalo]) -> str:
    """Rótulo legível para um conjunto de intervalos, como ``'0-9A-Za-z_'``.

    Conjuntos muito grandes (como ``[^\\n]``) são mostrados como complemento.
    """
    intervalos = normalizar_intervalos(intervalos)
    if intervalos == ((0, MAX_CODEPOINT),):
        return "qualquer"
    if not intervalos:
        return "∅"
    complemento = complementar_intervalos(intervalos)
    if len(complemento) < len(intervalos) or (
        intervalos[0][0] == 0 and intervalos[-1][1] == MAX_CODEPOINT
    ):
        return "^" + "".join(formatar_intervalo(i) for i in complemento)
    return "".join(formatar_intervalo(i) for i in intervalos)


def _checar_intervalo(intervalo: Intervalo) -> None:
    inicio, fim = intervalo
    if not (0 <= inicio <= fim <= MAX_CODEPOINT):
        raise ValueError(f"intervalo inválido: {intervalo}")


# ---------------------------------------------------------------------------
# AFN
# ---------------------------------------------------------------------------

@dataclass
class AFN:
    """Autômato finito não determinístico com movimentos vazios (AFN-ε).

    Atributos
    ---------
    num_estados:
        Quantidade de estados. Os estados são ``0 .. num_estados - 1``.
    inicial:
        Estado inicial.
    transicoes:
        ``estado -> [(intervalo | None, destino), ...]``. ``None`` (``EPSILON``)
        é uma transição ε. Um estado sem saídas pode não aparecer no dicionário.
    aceitacao:
        ``estado -> id_token`` para cada estado de aceitação.

    Exemplo: AFN de ``a|ε`` (Thompson simplificado)::

        afn = AFN()
        q0, q1 = afn.novo_estado(), afn.novo_estado()
        afn.inicial = q0
        afn.adicionar_transicao(q0, (97, 97), q1)
        afn.adicionar_transicao(q0, EPSILON, q1)
        afn.aceitacao[q1] = ID_TOKEN_PADRAO
    """

    num_estados: int = 0
    inicial: int = 0
    transicoes: dict[int, list[tuple[Optional[Intervalo], int]]] = field(default_factory=dict)
    aceitacao: dict[int, int] = field(default_factory=dict)

    def novo_estado(self) -> int:
        """Cria um estado e retorna seu número."""
        estado = self.num_estados
        self.num_estados += 1
        return estado

    def adicionar_transicao(self, origem: int, intervalo: Optional[Intervalo], destino: int) -> None:
        """Adiciona ``origem --intervalo--> destino``. Use ``EPSILON`` para ε."""
        if intervalo is not None:
            _checar_intervalo(intervalo)
        self.transicoes.setdefault(origem, []).append((intervalo, destino))

    def saidas(self, estado: int) -> list[tuple[Optional[Intervalo], int]]:
        """Transições que saem de ``estado`` (lista vazia se não houver)."""
        return self.transicoes.get(estado, [])

    def validar(self) -> None:
        """Levanta ``ValueError`` se a estrutura violar o contrato."""
        _checar_estado(self.inicial, self.num_estados, "inicial")
        for origem, saidas in self.transicoes.items():
            _checar_estado(origem, self.num_estados, "origem")
            for intervalo, destino in saidas:
                _checar_estado(destino, self.num_estados, "destino")
                if intervalo is not None:
                    _checar_intervalo(intervalo)
        for estado in self.aceitacao:
            _checar_estado(estado, self.num_estados, "aceitação")


# ---------------------------------------------------------------------------
# AFD
# ---------------------------------------------------------------------------

@dataclass
class AFD:
    """Autômato finito determinístico **parcial**.

    Atributos
    ---------
    num_estados:
        Quantidade de estados. Os estados são ``0 .. num_estados - 1``.
    inicial:
        Estado inicial.
    transicoes:
        ``estado -> [(intervalo, destino), ...]``, com os intervalos **ordenados
        e disjuntos**, o que permite busca binária. Não há ε.
    aceitacao:
        ``estado -> id_token`` para cada estado de aceitação.
    estados_afn:
        Opcional. ``estado do AFD -> frozenset de estados do AFN`` que ele
        representa. Preenchido pela construção de subconjuntos e usado nos
        diagramas.

    O AFD é parcial: se nenhum intervalo contém o símbolo lido, o autômato
    **travou**. Não existe estado para o conjunto vazio. Isso é necessário para
    o casamento mais longo (o simulador lê até travar e volta à última
    aceitação).
    """

    num_estados: int = 0
    inicial: int = 0
    transicoes: dict[int, list[tuple[Intervalo, int]]] = field(default_factory=dict)
    aceitacao: dict[int, int] = field(default_factory=dict)
    estados_afn: dict[int, frozenset[int]] = field(default_factory=dict)

    def novo_estado(self, estados_afn: Optional[Iterable[int]] = None) -> int:
        """Cria um estado e retorna seu número.

        ``estados_afn`` registra quais estados do AFN o novo estado representa.
        """
        estado = self.num_estados
        self.num_estados += 1
        if estados_afn is not None:
            self.estados_afn[estado] = frozenset(estados_afn)
        return estado

    def adicionar_transicao(self, origem: int, intervalo: Intervalo, destino: int) -> None:
        """Adiciona ``origem --intervalo--> destino``.

        Mantém a lista de ``origem`` ordenada e recusa sobreposição, pois isso
        tornaria o autômato não determinístico.
        """
        _checar_intervalo(intervalo)
        saidas = self.transicoes.setdefault(origem, [])
        saidas.append((intervalo, destino))
        saidas.sort()
        _checar_disjuntos(origem, saidas)

    def saidas(self, estado: int) -> list[tuple[Intervalo, int]]:
        """Transições que saem de ``estado`` (lista vazia se não houver)."""
        return self.transicoes.get(estado, [])

    def validar(self) -> None:
        """Levanta ``ValueError`` se a estrutura violar o contrato."""
        _checar_estado(self.inicial, self.num_estados, "inicial")
        for origem, saidas in self.transicoes.items():
            _checar_estado(origem, self.num_estados, "origem")
            for intervalo, destino in saidas:
                if intervalo is None:
                    raise ValueError(f"AFD não pode ter transição ε (estado {origem})")
                _checar_intervalo(intervalo)
                _checar_estado(destino, self.num_estados, "destino")
            if saidas != sorted(saidas):
                raise ValueError(f"transições do estado {origem} não estão ordenadas")
            _checar_disjuntos(origem, saidas)
        for estado in self.aceitacao:
            _checar_estado(estado, self.num_estados, "aceitação")


def _checar_estado(estado: int, num_estados: int, papel: str) -> None:
    if not (0 <= estado < num_estados):
        raise ValueError(f"estado {papel} {estado} fora de 0..{num_estados - 1}")


def _checar_disjuntos(origem: int, saidas: list[tuple[Intervalo, int]]) -> None:
    for (anterior, _), (atual, _) in zip(saidas, saidas[1:]):
        if atual[0] <= anterior[1]:
            raise ValueError(
                f"transições sobrepostas no estado {origem}: {anterior} e {atual}"
            )
