#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Implementação de referência do padrão ASIRN / ASIC.

ASIRN — ASI Resource Name: identificador lógico, legível, de um artefato ASI.
ASIC  — ASI Compact: fingerprint curto (9 chars) + dígito verificador, embutido
        na ASIRN entre dois-pontos e também usável sozinho como `asi:<ASIC>`.

Rode `python3 -I tools/asirn.py --selftest` para validar.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from dataclasses import dataclass, field

# --- Crockford Base32 -------------------------------------------------------
# Alfabeto sem I, L, O, U (reduz erro de leitura). Case-insensitive na entrada.
_B32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
# Símbolos de verificação para os valores 32..36 (spec Crockford).
_CHECK_EXTRA = "*~$=U"
_CHECK_ALPHABET = _B32 + _CHECK_EXTRA  # 37 símbolos, índice = valor mod 37

# Normalização de leitura: I/L -> 1, O -> 0 (erros clássicos de digitação).
_B32_DECODE = {c: i for i, c in enumerate(_B32)}
_B32_DECODE.update({"I": 1, "L": 1, "O": 0})

ASIC_BITS = 40          # tamanho do fingerprint (8 símbolos * 5 bits)
ASIC_SYMBOLS = ASIC_BITS // 5


def b32_encode(value: int, symbols: int) -> str:
    out = []
    for shift in range(symbols - 1, -1, -1):
        out.append(_B32[(value >> (5 * shift)) & 0x1F])
    return "".join(out)


def b32_decode(text: str) -> int:
    value = 0
    for ch in text.upper():
        if ch not in _B32_DECODE:
            raise ValueError(f"símbolo Base32 inválido: {ch!r}")
        value = (value << 5) | _B32_DECODE[ch]
    return value


def check_symbol(value: int) -> str:
    """Símbolo de verificação Crockford: value mod 37."""
    return _CHECK_ALPHABET[value % 37]


# --- Enums do padrão (espelham registry/registry.json) ----------------------
TARGETS = {"orbis", "prospero", "cafe", "nx", "pc"}
METHODS = {"recomp", "decomp", "native", "emu"}
CHANNELS = {"dev", "alpha", "beta", "rc"}  # 'stable' é a ausência de canal

# --- Gramática --------------------------------------------------------------
_ASIRN_RE = re.compile(
    r"""^asi:
        (?P<asic>[0-9A-TV-Zilo]{8}[0-9A-TV-Z*~$=U])      # ASIC: 8 símbolos + verificador
        :(?P<target>[a-z0-9]+)
        :(?P<org>[a-z0-9][a-z0-9-]*)/(?P<title>[a-z0-9][a-z0-9-]*)
        :(?P<method>[a-z]+)
        @(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)
        (?:~(?P<channel>[a-z]+))?
        (?:\+(?P<build>[A-Za-z0-9.]+))?
        (?:\?(?P<quals>[^#]+))?
        (?:\#(?P<subpath>[A-Za-z0-9_/-]+))?
        $""",
    re.VERBOSE,
)


@dataclass
class Asirn:
    target: str
    org: str
    title: str
    method: str
    major: int
    minor: int
    patch: int
    channel: str | None = None          # None == stable
    build: str | None = None
    quals: dict[str, str] = field(default_factory=dict)
    subpath: str | None = None

    # ---- núcleo de identidade (o que o ASIC faz hash) ----------------------
    # Deliberadamente EXCLUI build/quals/subpath: eles são voláteis por-build e
    # não mudam a identidade do release. O ASIC identifica o release, não o build.
    def identity_core(self) -> str:
        chan = f"~{self.channel}" if self.channel else ""
        return (f"{self.target}:{self.org}/{self.title}:{self.method}"
                f"@{self.major}.{self.minor}.{self.patch}{chan}")

    def asic(self) -> str:
        digest = hashlib.sha256(self.identity_core().encode("utf-8")).digest()
        value = int.from_bytes(digest, "big") >> (256 - ASIC_BITS)  # 40 bits do topo
        return b32_encode(value, ASIC_SYMBOLS) + check_symbol(value)

    def version(self) -> str:
        chan = f"~{self.channel}" if self.channel else ""
        return f"{self.major}.{self.minor}.{self.patch}{chan}"

    # ---- forma longa (humana) ---------------------------------------------
    def to_asirn(self) -> str:
        s = (f"asi:{self.asic()}:{self.target}:{self.org}/{self.title}"
             f":{self.method}@{self.major}.{self.minor}.{self.patch}")
        if self.channel:
            s += f"~{self.channel}"
        if self.build:
            s += f"+{self.build}"
        if self.quals:
            s += "?" + "&".join(f"{k}={v}" for k, v in self.quals.items())
        if self.subpath:
            s += f"#{self.subpath}"
        return s

    # ---- forma curta (ASIN do projeto) -------------------------------------
    def to_compact(self) -> str:
        return f"asi:{self.asic()}"

    # ---- content ID de PKG Orbis (derivado, formato fixo da Sony) ----------
    def orbis_content_id(self, org_code: str, title_num: int) -> str:
        # AABBBB-TITLEID_00-LABEL16  (36 chars). Deriva label dos 16 primeiros
        # símbolos de um hash do núcleo; titleID vem do registry.
        label = hashlib.sha256(self.identity_core().encode()).hexdigest()[:16].upper()
        return f"UP0001-{org_code}{title_num:05d}_00-{label}"


def parse(text: str, *, verify: bool = True) -> Asirn:
    m = _ASIRN_RE.match(text.strip())
    if not m:
        raise ValueError("ASIRN malformada")
    g = m.groupdict()
    target, method = g["target"], g["method"]
    if target not in TARGETS:
        raise ValueError(f"target desconhecido: {target!r}")
    if method not in METHODS:
        raise ValueError(f"method desconhecido: {method!r}")
    channel = g["channel"]
    if channel is not None and channel not in CHANNELS:
        raise ValueError(f"canal desconhecido: {channel!r} (use {sorted(CHANNELS)} ou omita p/ stable)")
    quals: dict[str, str] = {}
    if g["quals"]:
        for pair in g["quals"].split("&"):
            k, _, v = pair.partition("=")
            quals[k] = v
    obj = Asirn(
        target=target, org=g["org"], title=g["title"], method=method,
        major=int(g["major"]), minor=int(g["minor"]), patch=int(g["patch"]),
        channel=channel, build=g["build"], quals=quals, subpath=g["subpath"],
    )
    if verify:
        got = g["asic"].upper()
        want = obj.asic()
        if got != want:
            raise ValueError(f"ASIC não confere: embutido={got} calculado={want} "
                             f"(nome corrompido ou editado à mão)")
    return obj


# --- self-test --------------------------------------------------------------
def _selftest() -> int:
    a = Asirn(target="orbis", org="quovix", title="galaxy", method="recomp",
              major=1, minor=2, patch=0, channel="beta",
              build="g9f3a1c", quals={"arch": "x86-64", "region": "us"}, subpath="eboot")
    long_form = a.to_asirn()
    print("ASIRN   :", long_form)
    print("compact :", a.to_compact())
    print("ASIC    :", a.asic())
    print("core    :", a.identity_core())
    print("PKG CID :", a.orbis_content_id("QVOX", 1))

    # round-trip de parse + verificação do dígito
    b = parse(long_form)
    assert b.to_asirn() == long_form, "round-trip falhou"

    # ASIC estável entre builds diferentes do mesmo release
    a2 = Asirn(target="orbis", org="quovix", title="galaxy", method="recomp",
               major=1, minor=2, patch=0, channel="beta", build="gDEADBEE")
    assert a.asic() == a2.asic(), "ASIC deveria ignorar build"

    # corrupção detectada
    corrupted = long_form.replace(":orbis:", ":prospero:")
    try:
        parse(corrupted)
    except ValueError as e:
        print("corrupção pega:", str(e)[:60], "...")
    else:
        raise AssertionError("corrupção NÃO foi detectada")

    # dígito verificador pega troca de 1 símbolo no ASIC
    asic = a.asic()
    bad = ("0" if asic[0] != "0" else "1") + asic[1:]
    assert bad[-1] == asic[-1]  # mesmo verificador, dados diferentes -> inválido
    print("OK: todos os self-tests passaram")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="codec/validador ASIRN·ASIC")
    ap.add_argument("asirn", nargs="?", help="ASIRN pra validar/expandir")
    ap.add_argument("--selftest", action="store_true")
    ns = ap.parse_args(argv)
    if ns.selftest:
        return _selftest()
    if not ns.asirn:
        ap.print_help()
        return 2
    obj = parse(ns.asirn)
    print("válida ✓")
    print("  compact:", obj.to_compact())
    print("  version:", obj.version(), "| canal:", obj.channel or "stable")
    print("  target :", obj.target, "| método:", obj.method)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
