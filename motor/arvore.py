"""Árvore sintática (AST) das expressões regulares.

Depois da expansão do açúcar sintático feita pelo parser, toda árvore usa
apenas cinco nós:

=================  ==============================================
Nó                 Significado
=================  ==============================================
``Vazio``          cadeia vazia (ε)
``Classe``         um símbolo dentro dos intervalos; um literal é
                   uma classe de um intervalo só
``Concat``         concatenação ``esq`` seguido de ``dir``
``Uniao``          união ``esq | dir``
``Estrela``        fecho de Kleene ``filho*``
=================  ==============================================

Os nós são imutáveis, então uma subárvore pode ser reaproveitada em vários
lugares (por exemplo, nas cópias geradas por ``X{3}``). Quem percorre a árvore
deve tratar cada ocorrência de forma independente: Thompson cria estados novos a
cada visita.
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from typing import Iterable, Sequence, Union

from motor.automatos import Intervalo, formatar_intervalos, normalizar_intervalos


class No:
    """Classe base de todos os nós da AST."""

    __slots__ = ()


@dataclass(frozen=True)
class Vazio(No):
    """Cadeia vazia (ε)."""


@dataclass(frozen=True)
class Classe(No):
    """Um símbolo pertencente a ``intervalos``.

    Os intervalos ficam sempre normalizados: ordenados, sem sobreposição e com
    vizinhos fundidos. Uma classe sem intervalos não aceita nenhum símbolo.
    """

    intervalos: tuple[Intervalo, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "intervalos", normalizar_intervalos(self.intervalos))

    @classmethod
    def literal(cls, caractere: str) -> "Classe":
        """Classe que aceita apenas ``caractere``."""
        codigo = ord(caractere)
        return cls(((codigo, codigo),))

    def contem(self, simbolo: Union[str, int]) -> bool:
        """Diz se o símbolo (caractere ou code point) pertence à classe."""
        codigo = ord(simbolo) if isinstance(simbolo, str) else simbolo
        posicao = bisect_right(self.intervalos, (codigo, float("inf"))) - 1
        return posicao >= 0 and self.intervalos[posicao][1] >= codigo


@dataclass(frozen=True)
class Concat(No):
    """Concatenação: ``esq`` seguido de ``dir``."""

    esq: No
    dir: No


@dataclass(frozen=True)
class Uniao(No):
    """União: ``esq | dir``."""

    esq: No
    dir: No


@dataclass(frozen=True)
class Estrela(No):
    """Fecho de Kleene: zero ou mais repetições de ``filho``."""

    filho: No


# ---------------------------------------------------------------------------
# Construção
# ---------------------------------------------------------------------------

def concatenar(nos: Iterable[No]) -> No:
    """Concatena uma sequência de nós.

    ``Vazio`` é descartado, pois ``ε·X = X``. A árvore é montada de forma
    balanceada, para que padrões longos (como ``a{1000}``) tenham profundidade
    logarítmica e não estourem a recursão de quem percorre a árvore.
    """
    lista = [no for no in nos if not isinstance(no, Vazio)]
    if not lista:
        return Vazio()
    return _balancear(lista, Concat)


def unir(nos: Iterable[No]) -> No:
    """União de uma sequência de nós, montada de forma balanceada."""
    lista = list(nos)
    if not lista:
        raise ValueError("união precisa de pelo menos um ramo")
    return _balancear(lista, Uniao)


def _balancear(lista: Sequence[No], tipo) -> No:
    if len(lista) == 1:
        return lista[0]
    meio = len(lista) // 2
    return tipo(_balancear(lista[:meio], tipo), _balancear(lista[meio:], tipo))


# ---------------------------------------------------------------------------
# Exibição
# ---------------------------------------------------------------------------

def descrever(no: No) -> str:
    """Rótulo de um nó, sem os filhos."""
    if isinstance(no, Classe):
        return f"Classe [{formatar_intervalos(no.intervalos)}]"
    return type(no).__name__


def filhos(no: No) -> tuple[No, ...]:
    """Filhos diretos de um nó."""
    if isinstance(no, (Concat, Uniao)):
        return (no.esq, no.dir)
    if isinstance(no, Estrela):
        return (no.filho,)
    return ()


def formatar_arvore(no: No) -> str:
    """Desenha a árvore em texto, um nó por linha::

        Uniao
        ├─ Concat
        │  ├─ Classe [a]
        │  └─ Classe [b]
        └─ Estrela
           └─ Classe [c]
    """
    linhas: list[str] = []
    pilha: list[tuple[No, str, str]] = [(no, "", "")]
    while pilha:
        atual, prefixo_linha, prefixo_filhos = pilha.pop()
        linhas.append(prefixo_linha + descrever(atual))
        lista = filhos(atual)
        for indice in reversed(range(len(lista))):
            ultimo = indice == len(lista) - 1
            pilha.append((
                lista[indice],
                prefixo_filhos + ("└─ " if ultimo else "├─ "),
                prefixo_filhos + ("   " if ultimo else "│  "),
            ))
    return "\n".join(linhas)
