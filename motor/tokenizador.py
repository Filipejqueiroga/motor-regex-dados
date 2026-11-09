"""Busca de dados em texto usando um único AFD mínimo."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Token:
    tipo: str
    texto: str
    inicio: int
    fim: int
    digitos_validos: bool | None = None
