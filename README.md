# Motor de Regex para Tokenização e Sanitização de Dados

Motor de expressões regulares construído do zero, sem `re` nem bibliotecas de regex, e aplicado à extração de dados em textos brutos. Projeto da disciplina de Linguagens Formais e Computabilidade.

O pipeline implementa a sequência clássica:

```
Expressão regular → AST → AFN-ε (Thompson) → AFD (subconjuntos) → AFD mínimo → simulação
```

A interface encontra CPF, CNPJ, e-mail, URL, telefone, CEP, data, valor, hashtag e menção, classifica cada ocorrência, produz um texto sanitizado, exporta JSON e mostra os autômatos, inclusive executando o AFD símbolo a símbolo.

## Instalação

É necessário Python 3.10 ou superior. O Graphviz não precisa ser instalado, pois os diagramas são renderizados no navegador.

```bash
python -m venv .venv
```

Ative o ambiente virtual:

```bash
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Linux e macOS
source .venv/bin/activate
```

Instale as dependências:

```bash
python -m pip install -r requirements.txt
```

## Execução da aplicação

```bash
python -m streamlit run app.py
```

A aplicação abre em `http://localhost:8501`, já preenchida com o texto de exemplo. As fontes são carregadas do Google Fonts; sem internet, a interface usa as fontes do sistema.

## Execução dos testes

```bash
python -m pytest
```

O teste diferencial (`tests/test_diferencial.py`) compara o motor com `re.fullmatch` em padrões e cadeias aleatórios, usando a semente fixa `20261110`, que aparece na mensagem de qualquer falha. Esse é o único lugar do projeto em que `re` é usado.

## Sintaxe suportada

| Sintaxe | Significado |
| --- | --- |
| `ab`, `a\|b`, `a*` | Concatenação, união e estrela |
| `a+`, `a?` | Uma ou mais vezes; zero ou uma vez |
| `a{n}`, `a{n,}`, `a{n,m}` | Repetição, com limite de 1000 |
| `( )` | Agrupamento |
| `[a-z0-9_]`, `[^...]` | Classe e classe negada |
| `.` | Qualquer caractere, exceto quebra de linha |
| `\d`, `\w`, `\s` | Dígito, caractere de palavra (inclui letras acentuadas) e espaço em branco |
| `\D`, `\W`, `\S` | Complementos dos atalhos |
| `\n`, `\t`, `\r`, `\f`, `\v` | Caracteres de controle |
| `\` seguido de símbolo | Escape do símbolo |

Quando dois padrões aceitam o mesmo trecho, vence o primeiro na ordem de prioridade: padrão personalizado, CNPJ, CPF, EMAIL, URL, TELEFONE, CEP, DATA, VALOR, HASHTAG, MENCAO. O casamento é sempre o mais longo.

## Desempenho

Medido com `python -m tests.medir_desempenho`, com os dez padrões ativos, em Windows 11 e Python 3.12:

| Entrada | Tamanho | Tempo |
| --- | --- | --- |
| Texto realista, com 4040 tokens | 100.000 caracteres | 0,32 s |
| Pior caso: `a` repetido, sem `@` | 2.000 caracteres | 3,1 s |
| Pior caso: `a` repetido, sem `@` | 4.000 caracteres | 12,3 s |

Cada tentativa de casamento é linear, mas reiniciar em cada posição torna o pior caso quadrático: dobrar a entrada quadruplica o tempo. Isso ocorre quando um padrão lê trechos longos e falha no final, como o de e-mail em uma sequência de letras sem `@`. Em 100 mil caracteres desse tipo, a estimativa por extrapolação é de cerca de duas horas.

## Limitações

- Backreferences, lookahead, lookbehind e âncoras não são suportados, pois não fazem parte do modelo adotado de linguagens regulares.
- O motor reconhece apenas o formato dos dados. Os dígitos verificadores de CPF e CNPJ envolvem aritmética e são verificados em uma etapa posterior (`validacao_documentos.py`).
- Entidades semânticas, como nomes de pessoas e organizações, estão fora do escopo.
- Datas são verificadas apenas quanto ao formato, sem validar o calendário.
- A construção de subconjuntos pode gerar um número exponencial de estados. Padrões como `(a|b)*a(a|b){20}` podem levar muito tempo para compilar.
- Diagramas com mais de 150 estados não são desenhados, para não travar o navegador; a execução passo a passo continua disponível.
