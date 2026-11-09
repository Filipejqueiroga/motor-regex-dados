"""Casador de referência que roda direto sobre a AST, só para os testes.

Permite verificar o significado da árvore gerada pelo parser sem depender de
Thompson nem do AFD (que são de outra parte do projeto). Não é eficiente, mas é
simples o bastante para ser obviamente correto.
"""

from motor.arvore import Classe, Concat, Estrela, No, Uniao, Vazio


def _fins(no: No, texto: str, inicios: frozenset[int]) -> frozenset[int]:
    """Posições onde ``no`` pode terminar, começando em alguma de ``inicios``."""
    if isinstance(no, Vazio):
        return inicios
    if isinstance(no, Classe):
        return frozenset(
            i + 1 for i in inicios if i < len(texto) and no.contem(texto[i])
        )
    if isinstance(no, Concat):
        return _fins(no.dir, texto, _fins(no.esq, texto, inicios))
    if isinstance(no, Uniao):
        return _fins(no.esq, texto, inicios) | _fins(no.dir, texto, inicios)
    if isinstance(no, Estrela):
        alcancados = set(inicios)
        fronteira = inicios
        while fronteira:
            novos = _fins(no.filho, texto, fronteira) - alcancados
            alcancados |= novos
            fronteira = frozenset(novos)
        return frozenset(alcancados)
    raise TypeError(f"nó desconhecido: {no!r}")


def casa(no: No, texto: str) -> bool:
    """A cadeia inteira pertence à linguagem da árvore?"""
    return len(texto) in _fins(no, texto, frozenset([0]))
