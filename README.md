# quovix

Tooling open-source para **recompilação/porte nativo** de jogos para consoles,
com foco em IA. O projeto distribui **apenas ferramenta e runtime** — nenhum
asset ou binário proprietário. Cada artefato exige o **dump do próprio usuário**
(BYO-dump).

## Padrão de identificação ASIRN · ASIC

Todo artefato é identificado por um nome que carrega seus próprios metadados.
Respondendo à pergunta "precisamos de duas versões?": **sim** — uma legível e
uma compacta, porque os dois objetivos (ler fácil × caber curto) brigam entre si.

- **[ASIRN](docs/ASIRN.md)** — forma longa, legível, com todos os campos:

  ```
  asi:FR69GJ5CI:orbis:quovix/rmge01:recomp@1.2.0+g9f3a1c?arch=x86-64#eboot
  ```

- **[ASIC](docs/ASIC.md)** — forma curta (9 chars) com dígito verificador
  embutido, o "ASIN" do projeto:

  ```
  asi:FR69GJ5CI
  ```

O ASIC também vive **dentro** da ASIRN (logo após `asi:`), funcionando como
fingerprint auto-validável do resto do nome.

| Camada | Valor |
|---|---|
| Org GitHub | `quovix` |
| Repo (padrão) | `quovix/asirn` |
| Repo (artefato) | `quovix/port-RMGE01-ps4-from-wii` |
| Título de exibição | `[PORT][RMGE01][PS4<-WII]` |
| Identificador lógico | `asi:FR69GJ5CI:orbis:quovix/rmge01:recomp@1.2.0` |
| Referência curta | `asi:FR69GJ5CI` |
| Arquivo / PKG | `asi.orbis.quovix.rmge01.recomp@1.2.0.pkg` |
| PKG content ID (Orbis) | `UP0001-QVOX00001_00-7E0C9848AC532465` |

### Ferramenta de referência

```sh
python3 -I tools/asirn.py --selftest        # valida a implementação
python3 -I tools/asirn.py '<asirn>'          # valida/expande uma ASIRN
```

A fonte de verdade dos enums e títulos é [`registry/registry.json`](registry/registry.json).

## Estrutura

```
docs/ASIRN.md       spec normativo da forma longa
docs/ASIC.md        spec normativo da forma curta + dígito verificador
registry/           enums, orgs, títulos (fonte de verdade)
tools/asirn.py      codec/validador de referência
```
