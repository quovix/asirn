# ASIC — ASI Compact (spec normativo)

> Versão do spec: **1.0.0** · Status: rascunho · Implementação de referência: [`tools/asirn.py`](../tools/asirn.py)

O **ASIC** é a forma curta do identificador: 9 caracteres que resumem o núcleo
de identidade de uma [ASIRN](ASIRN.md) e trazem um **dígito verificador**
embutido. É o análogo do ASIN/ISBN — curto *porque* existe um registry por trás
que permite expandi-lo de volta.

```
asi:AWGARQQAR
    └──────┘
    97GW253S  ← fingerprint (8 símbolos, 40 bits)
           8  ← dígito verificador (1 símbolo)
```

O ASIC aparece em dois lugares:

1. **Embutido** na ASIRN longa, logo após `asi:`, como fingerprint auto-validável
   do resto do nome.
2. **Sozinho**, como `asi:AWGARQQAR` — a referência curtíssima (em URLs, nomes de
   arquivo, QR, etc.).

## 1. Por que fingerprint e não compressão reversível

Curto **e** autossuficiente são objetivos que brigam. Um código de 9 chars não
tem bits para carregar org+título+versão+canal de forma reversível. A escolha do
padrão é a mesma do ASIN/ISBN:

- o ASIC é um **fingerprint determinístico** (mão única) do núcleo de identidade;
- a **expansão** de volta à ASIRN completa é feita pelo
  [`registry`](../registry/registry.json) (campo `releases`), preenchido no build.

Determinístico = o mesmo release sempre gera o mesmo ASIC, sem alocador central.

## 2. Alfabeto — Crockford Base32

```
0123456789ABCDEFGHJKMNPQRSTVWXYZ
```

Sem `I L O U` (reduz erro de leitura). Na **decodificação** é tolerante:
`I`/`L`→`1`, `O`→`0`, e é case-insensitive. A forma canônica é **maiúscula**.

## 3. Cálculo do fingerprint (8 símbolos)

1. Monte o **núcleo de identidade** (ver [ASIRN §3](ASIRN.md#3-núcleo-de-identidade)):
   `<target>:<org>/<title>:<method>@<version>[~<channel>]`.
2. `digest = SHA-256(core_utf8)`.
3. `value = 40 bits mais significativos do digest`.
4. Codifique `value` em 8 símbolos Crockford Base32 (5 bits cada).

40 bits ⇒ ~1,1 trilhão de valores. Pelo limite de aniversário (colisão
entre si, ≈ n²/2·2⁴⁰), o risco só começa a importar na casa de ~1 milhão de
releases distintos — folga enorme para a escala do projeto. Como o ASIC resume
só o **núcleo de identidade** (não o build), o `n` relevante é o número de
releases, que é pequeno. O espaço é extensível por versão do spec (ver §6).

| bits | símbolos | ~50% colisão | risco 1-em-milhão |
|---|---|---|---|
| 30 | 6 | ~38 mil | ~46 releases |
| **40 (v1)** | **8** | **~1,2 milhão** | **~1.480** |
| 50 | 10 | ~33 milhões | ~47 mil |

O dígito verificador **não** entra nessa conta — ele é integridade (pega
digitação), não unicidade.

## 4. Dígito verificador (1 símbolo)

Padrão de check symbol do Crockford Base32, módulo 37:

```
check = CHECK_ALPHABET[value % 37]
CHECK_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ" + "*~$=U"
```

Os 5 símbolos extras (`* ~ $ = U`) cobrem os valores 32..36 e **só** aparecem na
posição do verificador, nunca no fingerprint. Ele pega erros de digitação de um
símbolo e a maioria das transposições.

## 5. Validação

Dado um ASIC de 9 chars:

1. separe fingerprint (8) e verificador (1);
2. decodifique o fingerprint em `value`;
3. confira `CHECK_ALPHABET[value % 37] == verificador` → senão, **erro de
   digitação**;
4. (quando há a ASIRN longa) recalcule o fingerprint sobre o núcleo e compare →
   senão, **nome corrompido/adulterado**.

## 6. Versionamento do próprio ASIC

Este é o ASIC **v1** (fingerprint de 40 bits, SHA-256, Crockford). Mudanças no
algoritmo (tamanho do fingerprint, função de hash) são uma nova versão do spec
do ASIC e devem ser anunciadas no `registry` para não quebrar expansão de
códigos antigos.

## 7. Exemplos

| Núcleo de identidade | ASIC | Forma curta |
|---|---|---|
| `orbis:quovix/galaxy:recomp@1.2.0~beta` | `AWGARQQAR` | `asi:AWGARQQAR` |

Gere e valide com:

```sh
python3 -I tools/asirn.py --selftest
python3 -I tools/asirn.py 'asi:AWGARQQAR:orbis:quovix/galaxy:recomp@1.2.0~beta'
```
