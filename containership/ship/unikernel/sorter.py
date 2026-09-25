"""The sort policy: one script -> one node, by measured needs and complexity.

Schema `UC/SORT_LEDGER/1`. Every decision is deterministic, explainable and
recorded: the features measured from the script's bytes, the complexity band
they yield, the first rule that fired (S0..S9) and the sentence that explains
it. VERIFY re-sorts every cargo file from its bytes and requires the identical
decision, so the ledger can never drift from the policy.

The four nodes, and what each is *for* (from the DF profiles, measured):

  N_SMALL   BOTTLE ROCKET 3.0.0-MODEL -- 20 files, MSSL/ASM-1, builds with C11+OpenSSL:
            the teaching container. Takes the simplest cargo: MSSL assembly and
            small, plain, low-complexity scripts, notes and configs.
  N_MEDIUM  BOTTLE ROCKET 5.0.0 (ISA 4.1) -- the reference: LCTLC/1.1, native
            semantic verifier, independent BRIM verifier, Ed25519 signing, BRTM/1
            trust chain. Takes cargo whose need is *integrity and contract*:
            LCTLC/1.1 units, PA-LCTL bundles, sums, keys, signatures, manifests,
            schemas, mid-sized configs and docs, mid-complexity launchers.
  N_LARGE   BOTTLE ROCKET 4.7.0 (BR/1.1) -- the device I/O & service architecture,
            freestanding C core behind a HAL, LCTLC/1.2 compiled by a Python tool.
            Takes cargo whose need is *native/system*: C/C++/assembly, build systems,
            LCTLC/1.2, high-complexity scripts, large docs.
  N_XLARGE  QUORUM VM 5.0.0-candidate -- Python-hosted, JVM column verifier, 65,535-
            instruction programs, 5,513-file repository. Takes cargo whose need is a
            *hosted runtime or bulk*: Python/Java/JS/HTML, archives, images and
            binaries, anything >= 1 MiB, LCTLC/1.0 (the QVM profile), very-high
            complexity.

Complexity is a band computed from measured counts (lines, branch keywords,
imports/includes, definitions), never a judgement:

    score = lines/10 + 2*branches + 3*imports + 1*definitions
    LOW < 8 <= MID < 40 <= HIGH < 200 <= VERY_HIGH
"""

from __future__ import annotations

import hashlib
import os
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from . import NODE_IDS

SCHEMA = "UC/SORT_LEDGER/1"
POLICY_VERSION = "1.0.1"

BANDS = (("LOW", 8.0), ("MID", 40.0), ("HIGH", 200.0), ("VERY_HIGH", float("inf")))

# --------------------------------------------------------------------------
# kinds
# --------------------------------------------------------------------------

EXT_KIND: Dict[str, str] = {
    ".mssl": "mssl", ".lctlc": "lctlc", ".lctl": "lctl", ".pal": "pal",
    ".c": "c", ".h": "c_header", ".cc": "cpp", ".cpp": "cpp", ".hpp": "cpp", ".s": "asm", ".asm": "asm",
    ".mk": "make", ".cmake": "make", ".ld": "linker",
    ".py": "python", ".pyi": "python", ".ipynb": "notebook",
    ".java": "java", ".jar": "jar", ".class": "java_class", ".kt": "kotlin", ".scala": "scala",
    ".js": "javascript", ".mjs": "javascript", ".ts": "typescript", ".jsx": "javascript", ".tsx": "typescript",
    ".html": "html", ".htm": "html", ".css": "css", ".svg": "svg",
    ".sh": "shell", ".bash": "shell", ".zsh": "shell", ".cmd": "batch", ".bat": "batch", ".ps1": "powershell",
    ".json": "json", ".jsonl": "jsonl", ".yaml": "yaml", ".yml": "yaml", ".toml": "toml", ".ini": "config",
    ".cfg": "config", ".conf": "config", ".env": "config", ".plist": "plist", ".xml": "xml", ".csv": "csv", ".tsv": "csv",
    ".md": "markdown", ".rst": "text", ".txt": "text", ".ebnf": "grammar", ".bnf": "grammar",
    ".sha256": "sums", ".sig": "signature", ".pub": "key", ".key": "key", ".pem": "key", ".hex": "key_or_hex",
    ".zip": "archive", ".tar": "archive", ".gz": "archive", ".tgz": "archive", ".7z": "archive", ".pa21c": "archive",
    ".brimg": "image", ".brsb": "image", ".brmf": "image", ".brtp": "image", ".bin": "binary", ".o": "binary",
    ".a": "binary", ".so": "binary", ".dll": "binary", ".exe": "binary", ".pyc": "binary",
    ".pdf": "document", ".png": "media", ".jpg": "media", ".jpeg": "media", ".gif": "media", ".ico": "media",
    ".woff": "media", ".woff2": "media", ".ttf": "media", ".mp3": "media", ".mp4": "media", ".wav": "media",
    ".log": "log", ".lock": "config",
}
NAME_KIND: Dict[str, str] = {
    "makefile": "make", "gnumakefile": "make", "cmakelists.txt": "make", "dockerfile": "config",
    "license": "text", "notice": "text", "readme": "markdown", "changelog": "markdown",
    "sha256sums": "sums", "sha256sums.txt": "sums", "release_contents.sha256": "sums",
    "build": "shell", "verify": "shell", "run": "shell", "install": "shell",
}
HOSTED_KINDS = {"python", "notebook", "java", "jar", "java_class", "kotlin", "scala", "javascript",
                "typescript", "html", "css", "svg"}
NATIVE_KINDS = {"c", "c_header", "cpp", "asm", "make", "linker"}
BULK_KINDS = {"archive", "image", "binary", "document", "media", "jar", "java_class"}
TRUST_KINDS = {"sums", "signature", "key", "plist"}
DATA_KINDS = {"json", "jsonl", "yaml", "toml", "config", "xml", "csv", "log"}
DOC_KINDS = {"markdown", "text", "grammar"}
SCRIPT_KINDS = {"shell", "batch", "powershell"}

TRUST_NAME_RE = re.compile(r"(manifest|schema|provenance|trust_store|sha256|sums|signature|\.sig$|\.pub$|\.key$|"
                           r"public_key|private|seed|authority|seal|ledger|acceptance|release_)", re.I)
BRANCH_RE = re.compile(r"\b(if|elif|else|for|while|switch|case|goto|try|except|catch|loop|until|"
                       r"JZ|JNZ|JMP|BEQ|CALL|RET|CMP)\b")
IMPORT_RE = re.compile(r"^\s*(import |from \S+ import |#\s*include|require\(|use |using |source |\. /)", re.M)
DEF_RE = re.compile(r"^\s*(def |class |function |static |void |int |char |uint\d+_t |struct |typedef |[A-Za-z_][A-Za-z0-9_]*\s*\([^;]*\)\s*\{)", re.M)
IO_RE = re.compile(r"\b(socket|open\(|fopen|read\(|write\(|console|storage|mailbox|device|serial|apdu|entropy|"
                   r"clock|timer|network|http|tcp|udp|SVC|CONSOLE_|STORAGE_|MAILBOX_|DEVICE_)\b")

BINARY_SNIFF = 4096


# --------------------------------------------------------------------------
# features
# --------------------------------------------------------------------------

def _is_binary(data: bytes) -> bool:
    chunk = data[:BINARY_SNIFF]
    if b"\x00" in chunk:
        return True
    try:
        chunk.decode("utf-8")
        return False
    except UnicodeDecodeError as exc:
        # policy 1.0.1: a UTF-8 multibyte character cut by the sniff boundary is not binary
        # (a columned-LCTL unit longer than the sniff, with its U+2502 separators, was misread as binary by 1.0.0)
        return not (len(data) > BINARY_SNIFF and exc.start >= len(chunk) - 3)


def _kind_of(rel_path: str, head: bytes, binary: bool) -> str:
    base = os.path.basename(rel_path)
    lower = base.lower()
    if lower in NAME_KIND:
        k = NAME_KIND[lower]
    else:
        stem, ext = os.path.splitext(lower)
        if ext == ".gz" and stem.endswith(".jsonl"):
            return "jsonl_gz"
        if ext == ".gz" and stem.endswith(".tar"):
            return "archive"
        k = EXT_KIND.get(ext, "")
        if not k:
            for pref, kk in (("readme", "markdown"), ("license", "text"), ("notice", "text"),
                             ("makefile", "make"), ("sha256sums", "sums")):
                if lower.startswith(pref):
                    k = kk
                    break
    text_head = head[:512].decode("utf-8", "replace") if not binary else ""
    # dialect magic beats extension
    if text_head.startswith("LCTLC/1.0"):
        return "lctlc10"
    if text_head.startswith("LCTLC/1.1"):
        return "lctlc11"
    if text_head.startswith("LCTLC/1.2"):
        return "lctlc12"
    if text_head.startswith("#PA-LCTL/"):
        return "pal"
    if k == "mssl" or lower.endswith(".mssl"):
        # MSSL assembly (BOTTLE ROCKET 3.0.0) vs an MSSL record document
        if ".profile" in text_head or re.search(r"^\s*(MOVI|MOV|ADD|HALT|NOP)\.", text_head, re.M):
            return "mssl_asm"
        return "mssl_doc"
    if k == "lctlc":
        return "lctlc_other"
    if k == "key_or_hex":
        return "key" if TRUST_NAME_RE.search(base) else "text"
    if not k:
        if binary:
            return "binary"
        if text_head.startswith("#!"):
            if "python" in text_head.splitlines()[0]:
                return "python"
            return "shell"
        return "text"
    if binary and k in DOC_KINDS | DATA_KINDS | SCRIPT_KINDS:
        return "binary"
    return k


def measure(rel_path: str, data: bytes) -> Dict[str, Any]:
    """Every feature the policy reads, from the bytes alone."""
    binary = _is_binary(data)
    kind = _kind_of(rel_path, data, binary)
    text = "" if binary else data.decode("utf-8", "replace")
    lines = text.count("\n") + (1 if text and not text.endswith("\n") else 0) if text else 0
    branches = len(BRANCH_RE.findall(text)) if text else 0
    imports = len(IMPORT_RE.findall(text)) if text else 0
    defs = len(DEF_RE.findall(text)) if text else 0
    io_refs = len(IO_RE.findall(text)) if text else 0
    score = lines / 10.0 + 2.0 * branches + 3.0 * imports + 1.0 * defs
    band = next(name for name, ceiling in BANDS if score < ceiling)
    return {
        "kind": kind, "bytes": len(data), "lines": lines, "binary": binary,
        "branches": branches, "imports": imports, "definitions": defs, "io_refs": io_refs,
        "complexity_score": round(score, 3), "complexity_band": band,
        "trust_name": bool(TRUST_NAME_RE.search(os.path.basename(rel_path))),
        "hosted": kind in HOSTED_KINDS, "native": kind in NATIVE_KINDS,
        "bulk": (kind in BULK_KINDS) or len(data) >= (1 << 20),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


# --------------------------------------------------------------------------
# rules
# --------------------------------------------------------------------------

def _by_band(band: str, low: str, mid: str, high: str, very_high: str) -> str:
    return {"LOW": low, "MID": mid, "HIGH": high, "VERY_HIGH": very_high}[band]


RULES: List[Tuple[str, str]] = [
    ("S0", "a script written in a node's own guest dialect goes to that node: MSSL assembly -> N_SMALL, LCTLC/1.1 -> N_MEDIUM, LCTLC/1.2 -> N_LARGE, LCTLC/1.0 (QVM profile) -> N_XLARGE"),
    ("S1", "a PA-LCTL bundle (.pal) goes to N_MEDIUM, the reference node the corpora's own adapter binds"),
    ("S2", "bulk cargo -- archives, images, binaries, media, PDFs, or anything >= 1 MiB -- goes to N_XLARGE, the roomiest, hosted node"),
    ("S3", "hosted-runtime source (Python, Java, JavaScript/TypeScript, HTML/CSS/SVG, notebooks) and Columned LCTL plans (.lctl, verified by the JVM column verifier) go to N_XLARGE, the Python-hosted node with the JVM verifier"),
    ("S4", "native/system source (C, C++, headers, assembly, Makefiles, linker scripts) goes to N_LARGE, the freestanding C core with the device I/O and service architecture"),
    ("S5", "integrity and contract artifacts (sums, signatures, keys, manifests, schemas, provenance, ledgers, trust stores) go to N_MEDIUM, the node with signing, the trust chain and the independent verifier"),
    ("S6", "structured data and configuration go by size: <= 4 KiB -> N_SMALL, <= 256 KiB -> N_MEDIUM, larger -> N_LARGE"),
    ("S7", "launchers and shell/batch scripts go by complexity band: LOW -> N_SMALL, MID -> N_MEDIUM, HIGH -> N_LARGE, VERY_HIGH -> N_XLARGE"),
    ("S8", "documents and notes go by size: <= 8 KiB -> N_SMALL (teaching), <= 128 KiB -> N_MEDIUM, larger -> N_LARGE"),
    ("S9", "everything else goes by complexity band: LOW -> N_SMALL, MID -> N_MEDIUM, HIGH -> N_LARGE, VERY_HIGH -> N_XLARGE"),
]
RULE_TEXT = dict(RULES)


def decide(rel_path: str, f: Dict[str, Any]) -> Tuple[str, str, str]:
    """(node_id, rule_id, explanation) for measured features `f`."""
    k = f["kind"]
    if k == "mssl_asm":
        return "N_SMALL", "S0", "MSSL/ASM-1 assembly is the guest dialect of BOTTLE ROCKET 3.0.0-MODEL"
    if k == "lctlc11":
        return "N_MEDIUM", "S0", "LCTLC/1.1 is the guest dialect of BOTTLE ROCKET 5.0.0 (ISA 4.1)"
    if k == "lctlc12":
        return "N_LARGE", "S0", "LCTLC/1.2 (columned-lctl/4.3) is the guest dialect of BOTTLE ROCKET 4.7.0 (BR/1.1)"
    if k == "lctlc10":
        return "N_XLARGE", "S0", "LCTLC/1.0 is the QUORUM VM profile"
    if k == "pal":
        return "N_MEDIUM", "S1", "a PA-LCTL bundle; the reference node runs the corpora's own adapter"
    if f["bulk"]:
        why = f"{k} of {f['bytes']} bytes" if k in BULK_KINDS else f"{f['bytes']} bytes >= 1 MiB"
        return "N_XLARGE", "S2", f"bulk cargo ({why}) needs the roomiest, hosted node"
    if f["hosted"]:
        return "N_XLARGE", "S3", f"{k} needs a hosted runtime; the QUORUM node is Python-hosted with a JVM verifier"
    if k == "lctl":
        return "N_XLARGE", "S3", "a Columned LCTL plan; the QUORUM node hosts the LCTL 1.6.1-RC1 column verifier (JVM) that lowers and verifies plans"
    if f["native"] or k == "lctlc_other":
        return "N_LARGE", "S4", f"{k} belongs with the freestanding C core and its build system"
    if k in TRUST_KINDS or (f["trust_name"] and k in DATA_KINDS | DOC_KINDS | {"text"}):
        return "N_MEDIUM", "S5", f"{k} named like an integrity/contract artifact needs signing, trust chain and independent verification"
    if k in DATA_KINDS or k in ("jsonl_gz", "mssl_doc"):
        if f["bytes"] <= 4096:
            return "N_SMALL", "S6", f"{k} of {f['bytes']} bytes (<= 4 KiB)"
        if f["bytes"] <= 256 * 1024:
            return "N_MEDIUM", "S6", f"{k} of {f['bytes']} bytes (<= 256 KiB)"
        return "N_LARGE", "S6", f"{k} of {f['bytes']} bytes (> 256 KiB)"
    if k in SCRIPT_KINDS:
        n = _by_band(f["complexity_band"], "N_SMALL", "N_MEDIUM", "N_LARGE", "N_XLARGE")
        return n, "S7", f"{k} launcher, complexity {f['complexity_band']} (score {f['complexity_score']})"
    if k in DOC_KINDS:
        if f["bytes"] <= 8192:
            return "N_SMALL", "S8", f"{k} of {f['bytes']} bytes (<= 8 KiB): teaching-sized"
        if f["bytes"] <= 128 * 1024:
            return "N_MEDIUM", "S8", f"{k} of {f['bytes']} bytes (<= 128 KiB)"
        return "N_LARGE", "S8", f"{k} of {f['bytes']} bytes (> 128 KiB)"
    n = _by_band(f["complexity_band"], "N_SMALL", "N_MEDIUM", "N_LARGE", "N_XLARGE")
    return n, "S9", f"{k}, complexity {f['complexity_band']} (score {f['complexity_score']})"


def sort_script(rel_path: str, data: bytes) -> Dict[str, Any]:
    f = measure(rel_path, data)
    node, rule, why = decide(rel_path, f)
    return {"path": rel_path, "node": node, "rule": rule, "explanation": why, **f}


def policy_record() -> Dict[str, Any]:
    return {"schema": "UC/SORT_POLICY/1", "version": POLICY_VERSION,
            "complexity": {"score": "lines/10 + 2*branches + 3*imports + 1*definitions",
                           "bands": {"LOW": "< 8", "MID": "< 40", "HIGH": "< 200", "VERY_HIGH": ">= 200"}},
            "rules": [{"id": i, "rule": t} for i, t in RULES],
            "first_match_wins": True,
            "nodes": list(NODE_IDS),
            "history": [{"version": "1.0.0", "change": "initial policy (UC-1.0.0)"},
                        {"version": "1.0.1", "change": "measurement fix: the binary sniff tolerates a UTF-8 multibyte character cut at the "
                                                        "4096-byte sniff boundary; 1.0.0 misread a columned-LCTL unit longer than the sniff "
                                                        "(its U+2502 separators) as binary and sent it to N_XLARGE as bulk instead of its own node"}]}
