"""Padrões de dados na ordem de prioridade do tokenizador."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Padrao:
    nome: str
    expressao: str
    fronteira_numerica: bool = False


PADROES = (
    Padrao("CNPJ", r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", True),
    Padrao("CPF", r"\d{3}\.\d{3}\.\d{3}-\d{2}|\d{11}", True),
    Padrao("EMAIL", r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+"),
    Padrao("URL", r"https?://[^\s]*[^\s.,;:!?)]"),
    Padrao("TELEFONE", r"(\(\d{2}\) ?|\d{2}[ -]?)(9\d{4}|\d{4})-?\d{4}", True),
    Padrao("CEP", r"\d{5}-\d{3}", True),
    Padrao("DATA", r"\d{2}/\d{2}/\d{4}", True),
    Padrao("VALOR", r"R\$ ?(\d{1,3}(\.\d{3})+|\d+)(,\d{2})?", True),
    Padrao("HASHTAG", r"#\w+"),
    Padrao("MENCAO", r"@\w+"),
)
