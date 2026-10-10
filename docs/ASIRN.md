# ASIRN — ASI Resource Name (spec normativo)

> Versão do spec: **1.0.0** · Status: rascunho · Implementação de referência: [`tools/asirn.py`](../tools/asirn.py)

A **ASIRN** é o identificador lógico canônico de um artefato produzido neste
padrão. É legível por humano e carrega, no próprio nome, todos os metadados que
descrevem *o quê* é o artefato: alvo de execução, origem, técnica, versão e
canal de release. Convenção inspirada em ARN (AWS) + PURL + SemVer.

Há duas representações, documentadas aqui e no spec do [ASIC](ASIC.md):

| Representação | Para quê | Exemplo |
|---|---|---|
| **ASIRN** (longa, humana) | leitura, logs, manifestos, specs | `asi:FR69GJ5CI:orbis:quovix/rmge01:recomp@1.2.0` |
| **ASIC** (curta, compacta) | referência, URLs, nomes de arquivo | `asi:FR69GJ5CI` |

## 1. Forma canônica

```
asi:<asic>:<target>:<org>/<title>:<method>@<version>[~<channel>][+<build>][?<qualifiers>][#<subpath>]
```

Exemplo completo (todos os campos presentes):

```
asi:FR69GJ5CI:orbis:quovix/rmge01:recomp@1.2.0+g9f3a1c?arch=x86-64&region=us#eboot
```

## 2. Campos

| # | Campo | Símbolo | Obrigatório | Domínio | Papel |
|---|---|---|---|---|---|
| 0 | scheme | `asi:` | sim | literal | marca "artefato ASI" (foco IA) |
| 1 | **asic** | `…:` | sim | 9 chars (ver [ASIC](ASIC.md)) | fingerprint + dígito verificador do núcleo |
| 2 | **target** | `:` | sim | `orbis` `prospero` `cafe` `nx` `pc` | plataforma de execução |
| 3 | **org** | `:` | sim | `[a-z0-9][a-z0-9-]*` | organização |
| 4 | **title** | `/` | sim | `[a-z0-9][a-z0-9-]*` | título |
| 5 | **method** | `:` | sim | `recomp` `decomp` `native` `emu` | técnica de produção |
| 6 | **version** | `@` | sim | SemVer `X.Y.Z` | versão |
| 7 | **channel** | `~` | não | `dev` `alpha` `beta` `rc` | trilha de release (ausente = `stable`) |
| 8 | **build** | `+` | não | `[A-Za-z0-9.]+` | metadado de build (ex. `g<hash>`, data) |
| 9 | **qualifiers** | `?` | não | `k=v&k=v` | variantes (arch, region, disc hash…) |
| 10 | **subpath** | `#` | não | `[A-Za-z0-9_/-]+` | componente interno (`eboot`, `assets`…) |

O domínio dos enums (targets, methods, channels, orgs, titles) é fixado em
[`registry/registry.json`](../registry/registry.json), a fonte de verdade.

## 3. Núcleo de identidade

O **núcleo de identidade** é o subconjunto que define *qual release* é o
artefato — e é exatamente o que o ASIC resume:

```
<target>:<org>/<title>:<method>@<version>[~<channel>]
```

Build, qualifiers e subpath **não** fazem parte do núcleo: são voláteis
por-build/por-variante e não mudam a identidade. Dois builds da mesma versão
têm o **mesmo ASIC**.

## 4. Versionamento (SemVer + canais)

- **MAJOR** — quebra de compatibilidade (formato de save, mapeamento de
  controle, ABI do recompilador).
- **MINOR** — conteúdo/feature retrocompatível.
- **PATCH** — correção.
- **Canal** (`~`): `dev → alpha → beta → rc → stable`. `stable` é a ausência
  de canal — nunca se escreve `~stable`.
- **Build** (`+`): sempre rastreável ao commit, ex. `+g<shorthash>` e/ou
  `+<AAAA.MM.DD>`.

## 5. Serialização segura para filesystem / PKG

`: / ? #` quebram em alguns filesystems. A forma de arquivo troca `:`→`.` e
`/`→`.`, e descarta `? #`:

```
asi.orbis.quovix.rmge01.recomp@1.2.0+g9f3a1c.pkg
```

## 6. Mapeamento para content ID de PKG (Orbis / PS4)

O content ID do PKG tem formato fixo da Sony (`AABBBB-TITLEID_00-<label 16ch>`,
36 chars) e **não pode ser** a ASIRN literal. Ele é **derivado**:

```
UP0001-<pkg_code><title_num:05d>_00-<label16>
        └ registry ┘             └ 16 hex do hash do núcleo ┘
```

Ex.: `UP0001-QVOX00001_00-7E0C9848AC532465`. O `pkg_code` e o `title_num` vêm
do registry; o label é determinístico a partir do núcleo de identidade.

## 7. Gramática (ABNF)

```abnf
asirn      = "asi:" asic ":" target ":" coord ":" method "@" version
             [ "~" channel ] [ "+" build ] [ "?" quals ] [ "#" subpath ]
asic       = 8(b32) checksym
coord      = org "/" title
target     = 1*lcalnum
org        = lcalnum *( lcalnum / "-" )
title      = lcalnum *( lcalnum / "-" )
method     = "recomp" / "decomp" / "native" / "emu"
version    = 1*DIGIT "." 1*DIGIT "." 1*DIGIT
channel    = "dev" / "alpha" / "beta" / "rc"
build      = 1*( ALPHA / DIGIT / "." )
quals      = qual *( "&" qual )
qual       = key "=" val
subpath    = 1*( ALPHA / DIGIT / "_" / "/" / "-" )
b32        = %x30-39 / %x41-5A  ; alfabeto Crockford (ver ASIC.md)
lcalnum    = %x61-7A / DIGIT
```

## 8. Conformidade

Uma ASIRN é **válida** quando (a) casa a gramática, (b) `target`/`method`/
`channel`/`org`/`title` existem no registry, e (c) o ASIC embutido confere com
o recalculado sobre o núcleo de identidade. A implementação de referência
[`tools/asirn.py`](../tools/asirn.py) é normativa em caso de divergência.

## 9. Mapeamento para repositório git

A identidade **estável** (sem `method`/`version`) vira o **nome do repositório**;
`method`, `channel` e `version` viram **branch** e **tag**. Assim um único repo
hospeda todas as versões e canais daquele método, e o nome do repo nunca muda
entre releases.

Quando o `title` é um **game ID** (6 chars, ex. `rmge01`), o repo usa um slug
**descritivo**; caso contrário, a forma canônica ancorada no ASIC.

| Elemento git | Deriva de | Exemplo |
|---|---|---|
| **org** (dono no GitHub) | `<org>` | `quovix` |
| **nome do repo** (game ID) | `port-<GAMEID>-<console>-from-<source>` | `port-RMGE01-ps4-from-wii` |
| **nome do repo** (fallback) | `asi.<asic>.<target>.<org>` (`:`→`.`) | `asi.FR69GJ5CI.orbis.quovix` |
| **branch** | `<method>` (+ `~<channel>`) | `recomp`, `recomp~beta` |
| **tag / release** | `v<version>` | `v1.2.0` |

- `<console>` é o nome comercial do `target` (`orbis`→`ps4`, `prospero`→`ps5`,
  `cafe`→`wiiu`, `nx`→`switch`).
- `<source>` é a plataforma de **origem**, inferida pelo 1º char do game ID
  (`R`/`S`→`wii`, `G`→`gc`).

Slug completo: `quovix/port-RMGE01-ps4-from-wii`, branch `recomp`, tag `v1.2.0`.
Título de exibição (README): `[PORT][RMGE01][PS4<-WII]`.

O nome do repo só usa `[A-Za-z0-9._-]` (restrição do GitHub) — os tags `[...]`,
`<-` e espaços ficam só no **título de exibição**, não no slug. Os helpers
`repo_slug()`, `display_title()`, `git_branch()` e `git_tag()` em
[`tools/asirn.py`](../tools/asirn.py) emitem esses valores a partir de uma ASIRN.
