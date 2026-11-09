"""Parser de expressões regulares: string do padrão -> AST.

Função pública: ``parse(padrao) -> No``.

Gramática (descida recursiva, da menor para a maior precedência)::

    uniao      := concat ('|' concat)*
    concat     := repeticao*
    repeticao  := atomo quantificador?
    quantif.   := '*' | '+' | '?' | '{n}' | '{n,}' | '{n,m}'
    atomo      := literal | '.' | classe | atalho | '\\' escape | '(' uniao ')'

O açúcar sintático é expandido para os cinco nós básicos de ``motor.arvore``:

=============  ===============================================
Sintaxe        Expansão
=============  ===============================================
``X+``         ``X X*``
``X?``         ``X | ε``
``X{n}``       X repetido n vezes
``X{n,}``      X repetido n vezes seguido de ``X*``
``X{n,m}``     X n vezes seguido de (m-n) cópias de ``(X | ε)``
``[a-z0-9_]``  classe com a união dos intervalos
``[^...]``     complemento em relação a ``0..0x10FFFF``
``.``          qualquer caractere exceto ``\\n``
``\\d``         ``[0-9]``
``\\w``         ``[0-9A-Za-z_]`` + ``À-Ö``, ``Ø-ö``, ``ø-ÿ``
``\\s``         espaço, ``\\t``, ``\\n``, ``\\r``, ``\\f``, ``\\v``
=============  ===============================================

``\\D``, ``\\W`` e ``\\S`` são os complementos de ``\\d``, ``\\w`` e ``\\s``.

Padrões inválidos levantam ``ErroDeSintaxe`` com a posição (índice a partir de
0) do problema no padrão.

Este módulo não usa ``re`` nem nenhuma outra biblioteca de regex.
"""

from __future__ import annotations

from typing import Optional

from motor.arvore import Classe, Estrela, No, Uniao, Vazio, concatenar, unir
from motor.automatos import Intervalo, complementar_intervalos, normalizar_intervalos

LIMITE_REPETICAO = 1000
"""Maior valor aceito em ``{n,m}``."""

LIMITE_TAMANHO = 100_000
"""Maior número de símbolos que a árvore expandida pode ter.

Evita explosão de estados em casos como ``(a{1000}){1000}``, em que cada
repetição isolada é aceitável, mas o produto não é.
"""

QUANTIFICADORES = "*+?{"


class ErroDeSintaxe(ValueError):
    """Padrão inválido.

    Atributos: ``mensagem``, ``posicao`` (índice a partir de 0) e ``padrao``.
    """

    def __init__(self, mensagem: str, posicao: int, padrao: Optional[str] = None):
        self.mensagem = mensagem
        self.posicao = posicao
        self.padrao = padrao
        texto = f"{mensagem} (posição {posicao})"
        if padrao is not None:
            texto += f"\n  {padrao}\n  {' ' * posicao}^"
        super().__init__(texto)


# ---------------------------------------------------------------------------
# Classes pré-definidas
# ---------------------------------------------------------------------------

def _intervalo(inicio: str, fim: str) -> Intervalo:
    return (ord(inicio), ord(fim))


DIGITOS = normalizar_intervalos([_intervalo("0", "9")])

PALAVRA = normalizar_intervalos([
    _intervalo("0", "9"),
    _intervalo("A", "Z"),
    _intervalo("a", "z"),
    _intervalo("_", "_"),
    _intervalo("À", "Ö"),
    _intervalo("Ø", "ö"),
    _intervalo("ø", "ÿ"),
])

ESPACOS = normalizar_intervalos((ord(c), ord(c)) for c in " \t\n\r\f\v")

QUALQUER_MENOS_QUEBRA = complementar_intervalos([_intervalo("\n", "\n")])

ATALHOS: dict[str, tuple[Intervalo, ...]] = {
    "d": DIGITOS,
    "w": PALAVRA,
    "s": ESPACOS,
    "D": complementar_intervalos(DIGITOS),
    "W": complementar_intervalos(PALAVRA),
    "S": complementar_intervalos(ESPACOS),
}

ESCAPES_DE_CONTROLE = {"n": "\n", "t": "\t", "r": "\r", "f": "\f", "v": "\v"}


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def parse(padrao: str) -> No:
    """Converte o padrão em uma AST com apenas ``Vazio``, ``Classe``,
    ``Concat``, ``Uniao`` e ``Estrela``.

    Levanta ``ErroDeSintaxe`` se o padrão for inválido.

    >>> from motor.arvore import formatar_arvore
    >>> print(formatar_arvore(parse("ab|c*")))
    Uniao
    ├─ Concat
    │  ├─ Classe [a]
    │  └─ Classe [b]
    └─ Estrela
       └─ Classe [c]
    """
    return _Parser(padrao).executar()


class _Parser:
    """Descida recursiva. Cada regra retorna ``(no, tamanho)``, em que
    ``tamanho`` é o número de símbolos da árvore depois da expansão."""

    def __init__(self, padrao: str):
        self.padrao = padrao
        self.pos = 0

    # -- utilidades ---------------------------------------------------------

    def atual(self) -> Optional[str]:
        return self.padrao[self.pos] if self.pos < len(self.padrao) else None

    def seguinte(self) -> Optional[str]:
        indice = self.pos + 1
        return self.padrao[indice] if indice < len(self.padrao) else None

    def erro(self, mensagem: str, posicao: Optional[int] = None) -> ErroDeSintaxe:
        return ErroDeSintaxe(mensagem, self.pos if posicao is None else posicao, self.padrao)

    # -- regras -------------------------------------------------------------

    def executar(self) -> No:
        try:
            no, tamanho = self.uniao()
        except RecursionError:
            raise self.erro("grupos aninhados em excesso") from None
        if self.atual() is not None:
            # concat só para em '|' ou ')'; uniao consome todos os '|'.
            raise self.erro("')' sem '(' correspondente")
        self.checar_tamanho(tamanho, 0)
        return no

    def uniao(self) -> tuple[No, int]:
        ramos = [self.concat()]
        while self.atual() == "|":
            self.pos += 1
            ramos.append(self.concat())
        return unir(no for no, _ in ramos), sum(t for _, t in ramos)

    def concat(self) -> tuple[No, int]:
        partes = []
        while self.atual() is not None and self.atual() not in "|)":
            partes.append(self.repeticao())
        return concatenar(no for no, _ in partes), sum(t for _, t in partes)

    def repeticao(self) -> tuple[No, int]:
        if self.atual() in QUANTIFICADORES:
            raise self.erro(f"quantificador '{self.atual()}' sem operando")
        no, tamanho = self.atomo()
        if self.atual() is not None and self.atual() in QUANTIFICADORES:
            no, tamanho = self.quantificador(no, tamanho)
            if self.atual() is not None and self.atual() in QUANTIFICADORES:
                raise self.erro(
                    "quantificadores empilhados não são suportados "
                    "(modos lazy e possessivo estão fora do escopo); "
                    "use parênteses, como (a*)*"
                )
        return no, tamanho

    def atomo(self) -> tuple[No, int]:
        caractere = self.atual()
        inicio = self.pos

        if caractere == "(":
            self.pos += 1
            if self.atual() == "?":
                raise self.erro(
                    "lookahead, lookbehind e grupos especiais '(?...)' não são "
                    "suportados: não descrevem linguagens regulares neste motor",
                    inicio,
                )
            no, tamanho = self.uniao()
            if self.atual() != ")":
                raise self.erro("'(' sem ')' correspondente", inicio)
            self.pos += 1
            return no, tamanho

        if caractere == "[":
            return Classe(self.classe()), 1

        if caractere == ".":
            self.pos += 1
            return Classe(QUALQUER_MENOS_QUEBRA), 1

        if caractere == "\\":
            intervalos, _ = self.escape()
            return Classe(intervalos), 1

        if caractere in "^$":
            raise self.erro(
                f"âncora '{caractere}' não é suportada; para o literal use '\\{caractere}'"
            )

        self.pos += 1
        return Classe.literal(caractere), 1

    def escape(self) -> tuple[tuple[Intervalo, ...], bool]:
        """Lê ``\\x``. Retorna ``(intervalos, eh_atalho)``."""
        inicio = self.pos
        self.pos += 1
        caractere = self.atual()
        if caractere is None:
            raise self.erro("'\\' no fim do padrão", inicio)
        self.pos += 1

        if caractere in ATALHOS:
            return ATALHOS[caractere], True
        if caractere in ESCAPES_DE_CONTROLE:
            codigo = ord(ESCAPES_DE_CONTROLE[caractere])
            return ((codigo, codigo),), False
        if "0" <= caractere <= "9":
            raise self.erro(
                f"backreference '\\{caractere}' não é suportada: "
                "não descreve uma linguagem regular",
                inicio,
            )
        if caractere in "bBAZz":
            raise self.erro(f"âncora '\\{caractere}' não é suportada", inicio)
        if caractere.isascii() and caractere.isalnum():
            raise self.erro(f"escape desconhecido '\\{caractere}'", inicio)

        codigo = ord(caractere)
        return ((codigo, codigo),), False

    def classe(self) -> tuple[Intervalo, ...]:
        """Lê ``[...]`` ou ``[^...]``."""
        inicio = self.pos
        self.pos += 1
        negada = False
        if self.atual() == "^":
            negada = True
            self.pos += 1

        intervalos: list[Intervalo] = []
        primeiro = True
        while True:
            caractere = self.atual()
            if caractere is None:
                raise self.erro("'[' sem ']' correspondente", inicio)
            if caractere == "]" and not primeiro:
                self.pos += 1
                break
            primeiro = False

            inicio_item = self.pos
            itens, simbolo = self.item_de_classe()
            # '-' entre dois itens forma um intervalo; no início ou no fim é literal.
            if self.atual() == "-" and self.seguinte() not in (None, "]"):
                if simbolo is None:
                    raise self.erro("atalho não pode ser limite de intervalo", inicio_item)
                self.pos += 1
                inicio_fim = self.pos
                _, simbolo_fim = self.item_de_classe()
                if simbolo_fim is None:
                    raise self.erro("atalho não pode ser limite de intervalo", inicio_fim)
                if simbolo_fim < simbolo:
                    raise self.erro(
                        f"intervalo invertido '{chr(simbolo)}-{chr(simbolo_fim)}'",
                        inicio_item,
                    )
                intervalos.append((simbolo, simbolo_fim))
            else:
                intervalos.extend(itens)

        if negada:
            return complementar_intervalos(intervalos)
        return normalizar_intervalos(intervalos)

    def item_de_classe(self) -> tuple[tuple[Intervalo, ...], Optional[int]]:
        """Lê um item dentro de ``[...]``.

        Retorna ``(intervalos, simbolo)``; ``simbolo`` é o code point quando o
        item é um único caractere (podendo ser limite de intervalo) e ``None``
        quando é um atalho como ``\\d``.
        """
        if self.atual() == "\\":
            intervalos, eh_atalho = self.escape()
            return intervalos, None if eh_atalho else intervalos[0][0]
        codigo = ord(self.atual())
        self.pos += 1
        return ((codigo, codigo),), codigo

    def quantificador(self, no: No, tamanho: int) -> tuple[No, int]:
        inicio = self.pos
        caractere = self.atual()
        self.pos += 1

        if caractere == "*":
            return Estrela(no), tamanho
        if caractere == "+":
            return concatenar([no, Estrela(no)]), 2 * tamanho
        if caractere == "?":
            return unir([no, Vazio()]), tamanho

        # '{n}', '{n,}' ou '{n,m}'
        invalido = "'{' não forma um quantificador válido; para o literal use '\\{'"
        minimo = self.numero()
        if minimo is None:
            raise self.erro(invalido, inicio)
        maximo: Optional[int]
        if self.atual() == "}":
            maximo = minimo
        elif self.atual() == ",":
            self.pos += 1
            if self.atual() == "}":
                maximo = None
            else:
                maximo = self.numero()
                if maximo is None or self.atual() != "}":
                    raise self.erro(invalido, inicio)
        else:
            raise self.erro(invalido, inicio)
        self.pos += 1  # '}'

        if minimo > LIMITE_REPETICAO or (maximo is not None and maximo > LIMITE_REPETICAO):
            raise self.erro(f"repetição maior que {LIMITE_REPETICAO} não é permitida", inicio)
        if maximo is not None and minimo > maximo:
            raise self.erro(f"repetição {{{minimo},{maximo}}} com mínimo maior que máximo", inicio)
        return self.repetir(no, tamanho, minimo, maximo, inicio)

    def numero(self) -> Optional[int]:
        inicio = self.pos
        while self.atual() is not None and "0" <= self.atual() <= "9":
            self.pos += 1
        if self.pos == inicio:
            return None
        return int(self.padrao[inicio:self.pos])

    def repetir(
        self, no: No, tamanho: int, minimo: int, maximo: Optional[int], posicao: int
    ) -> tuple[No, int]:
        if maximo is None:
            partes = [no] * minimo + [Estrela(no)]
            novo_tamanho = tamanho * (minimo + 1)
        else:
            opcional = unir([no, Vazio()])
            partes = [no] * minimo + [opcional] * (maximo - minimo)
            novo_tamanho = tamanho * maximo
        self.checar_tamanho(novo_tamanho, posicao)
        return concatenar(partes), novo_tamanho

    def checar_tamanho(self, tamanho: int, posicao: int) -> None:
        if tamanho > LIMITE_TAMANHO:
            raise self.erro(
                f"padrão expandido grande demais ({tamanho} símbolos; "
                f"limite {LIMITE_TAMANHO})",
                posicao,
            )
