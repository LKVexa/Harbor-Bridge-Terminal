"""Applying the corrections the studio already knows how to name.

`describe` maps a refusal to the rule it broke and to what to do about it.
For a large share of refusals, "what to do about it" is not a judgement call:
the missing column header row goes in one place, `@unit version` has exactly
one legal value, ARG keys have one legal order, and a source operand separated
by a comma was meant to be separated by U+203A. Telling an author to make an
edit that has only one correct form, and then waiting to be asked again, is
work the studio can do itself.

So it does -- under three rules that keep it honest:

  1. Only determinate corrections. If a refusal admits more than one sensible
     repair, or needs a value nobody has written down (`MOVI requires imm`),
     this module declines and says so. It never invents an operand.
  2. Every edit is reported: which refusal, which rule, the line, and the text
     before and after. A repair nobody can see is a repair nobody can audit.
  3. The compiler decides. Each round applies exactly one correction and asks
     the runtime's own toolchain again. Nothing here has an opinion about
     whether a program is valid; it only proposes the next edit.

The result is `studio try --fix` and `studio fix`: a source goes in, a source
that compiles comes out, along with the list of what had to change to get
there -- or an honest stop at the first refusal that needs a human.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Callable, Dict, List, Optional, Tuple

SCHEMA = "PA21.STUDIO/REPAIR/1"

COLUMNS = ["ID", "LANE", "OP", "OUT", "CTRL", "IN", "ARG", "META"]
MAGIC = "LCTLC/1.2"
HDR = "ID│LANE│OP│OUT│CTRL│IN│ARG│META"
SEP = "›"
UNIT_DEFAULTS = {"version": "4.3.0", "language": "columned-lctl/4.3",
                 "isa": "BR/1.1", "br_image_version": "10",
                 "br_request_caps": "CONTROL"}

# opcodes that must not name a destination register, and those that must.
NO_DEST = {"NOP", "JMP", "JZ", "JNZ", "HALT", "CMP", "STORE", "PUSH", "BITTST",
           "STOREX", "BEQ", "CALL", "RET", "JMPR", "ENTER", "LEAVE", "TRAP",
           "CHECKPOINT", "YIELD"}


class Source:
    """A COLUMNED LCTL source split into the parts a repair addresses."""

    def __init__(self, text: str):
        self.text = text

    # -- structure ------------------------------------------------------
    @property
    def lines(self) -> List[str]:
        return self.text.split("\n")

    def unit_index(self) -> int:
        for i, ln in enumerate(self.lines):
            if ln.startswith("@unit "):
                return i
        return -1

    def header_index(self) -> int:
        for i, ln in enumerate(self.lines):
            if ln.replace(" ", "") == HDR.replace(" ", ""):
                return i
        return -1

    def row_indices(self) -> List[int]:
        h = self.header_index()
        out = []
        for i, ln in enumerate(self.lines):
            if i == h or "│" not in ln:
                continue
            out.append(i)
        return out

    def cells(self, i: int) -> List[str]:
        return self.lines[i].split("│")

    def replace_line(self, i: int, new: str) -> "Source":
        ls = self.lines
        ls[i] = new
        return Source("\n".join(ls))

    def set_cell(self, i: int, col: int, value: str) -> "Source":
        c = self.cells(i)
        if col >= len(c):
            return self
        c[col] = value
        return self.replace_line(i, "│".join(c))

    def insert(self, i: int, line: str) -> "Source":
        ls = self.lines
        ls.insert(i, line)
        return Source("\n".join(ls))

    def registers_used(self) -> List[str]:
        return sorted(set(re.findall(r"\bR(\d+)\b", self.text)), key=int)

    def free_register(self) -> Optional[str]:
        used = {int(x) for x in self.registers_used()}
        for n in range(15, -1, -1):
            if n not in used:
                return f"R{n}"
        return None

    def next_id(self) -> str:
        taken = {self.cells(i)[0].strip() for i in self.row_indices()}
        for n in range(1, 700):
            # A..Z, then AA, AB, ... -- the same shape the scaffolds use
            s, m = "", n
            while m:
                m, r = divmod(m - 1, 26)
                s = chr(ord("A") + r) + s
            if s not in taken:
                return s
        return "ZZZ"


# ---------------------------------------------------------------------------
# the corrections
#
# Each takes the source and the compiler's message, and returns either None
# (this rule does not apply to this message, or cannot be applied safely) or
# a (new source, what changed) pair.
# ---------------------------------------------------------------------------


def _fix_encoding(s: Source, msg: str) -> Optional[Tuple[Source, str]]:
    if "CR prohibited" in msg:
        return Source(s.text.replace("\r\n", "\n").replace("\r", "\n")), \
            "removed carriage returns; the canonical line ending is LF"
    if "source must be NFC" in msg:
        return Source(unicodedata.normalize("NFC", s.text)), \
            "normalised the source to Unicode NFC"
    m = re.search(r"trailing whitespace line (\d+)", msg)
    if m:
        i = int(m.group(1)) - 1
        if 0 <= i < len(s.lines):
            return s.replace_line(i, s.lines[i].rstrip()), \
                f"stripped trailing whitespace on line {i + 1}"
    return None


def _fix_magic(s: Source, msg: str) -> Optional[Tuple[Source, str]]:
    if "unsupported/missing" not in msg or MAGIC not in msg:
        return None
    if s.lines and s.lines[0].strip() == MAGIC:
        return None
    return s.insert(0, MAGIC), f"inserted the {MAGIC} magic line at the top"


def _fix_structure(s: Source, msg: str) -> Optional[Tuple[Source, str]]:
    """The header row, and the terminator: one place each, no ambiguity."""
    if "row outside table" not in msg and "missing @unit/header/@end" not in msg:
        return None
    u = s.unit_index()
    if u < 0:
        return None                      # a unit line cannot be invented
    if s.header_index() < 0:
        return s.insert(u + 1, HDR), \
            "inserted the column header row after the @unit line"
    if not [ln for ln in s.lines if ln.strip() == "@end"]:
        text = s.text if s.text.endswith("\n") else s.text + "\n"
        return Source(text + "@end\n"), "appended the @end terminator"
    return None


def _fix_duplicate_header(s: Source, msg: str) -> Optional[Tuple[Source, str]]:
    if "duplicate header" not in msg:
        return None
    seen = False
    for i, ln in enumerate(s.lines):
        if ln.replace(" ", "") == HDR.replace(" ", ""):
            if seen:
                ls = s.lines
                del ls[i]
                return Source("\n".join(ls)), \
                    f"removed the duplicate column header on line {i + 1}"
            seen = True
    return None


def _unit_set(s: Source, key: str, value: str) -> Optional[Source]:
    i = s.unit_index()
    if i < 0:
        return None
    ln = s.lines[i]
    if re.search(rf"\b{re.escape(key)}=", ln):
        ln = re.sub(rf"\b{re.escape(key)}=\S+", f"{key}={value}", ln, count=1)
    else:
        ln = ln.rstrip() + f" {key}={value}"
    return s.replace_line(i, ln)


def _fix_unit_value(s: Source, msg: str) -> Optional[Tuple[Source, str]]:
    m = re.search(r"@unit (\S+) must be (\S+)", msg)
    if m:
        key, want = m.group(1), m.group(2)
        new = _unit_set(s, key, want)
        return (new, f"set @unit {key}={want}, which the compiler names as "
                     f"the only legal value") if new else None
    m = re.search(r"missing @unit (\S+)", msg)
    if m and m.group(1) in UNIT_DEFAULTS:
        key = m.group(1)
        new = _unit_set(s, key, UNIT_DEFAULTS[key])
        return (new, f"added the required @unit {key}={UNIT_DEFAULTS[key]}") \
            if new else None
    return None


def _fix_termination(s: Source, msg: str) -> Optional[Tuple[Source, str]]:
    if "loop requires termination=budgeted" not in msg:
        return None
    new = _unit_set(s, "termination", "budgeted")
    return (new, "declared termination=budgeted: the control-flow graph has a "
                 "cycle, so reaching HALT is not provable") if new else None


def _fix_caps(s: Source, msg: str) -> Optional[Tuple[Source, str]]:
    m = re.search(r"capability (\w+) exceeds @unit declaration", msg)
    if not m:
        return None
    want = m.group(1)
    i = s.unit_index()
    if i < 0:
        return None
    cur = re.search(r"br_request_caps=([A-Z|]+)", s.lines[i])
    have = cur.group(1).split("|") if cur else []
    if want in have:
        return None
    new = _unit_set(s, "br_request_caps", "|".join(have + [want]))
    return (new, f"added {want} to br_request_caps; a row uses it and the "
                 f"unit had not asked for it") if new else None


def _fix_declared_capability(s: Source, msg: str
                             ) -> Optional[Tuple[Source, str]]:
    m = re.search(r"(\w+): declared capability (\w+), expected (\w+)", msg)
    if not m:
        return None
    op, got, want = m.group(1), m.group(2), m.group(3)
    for i in s.row_indices():
        c = s.cells(i)
        if len(c) < 5 or c[2].strip() != op:
            continue
        cell = c[4].strip()
        cm = re.match(r"(C\d+):(\w+)$", cell)
        if cm and cm.group(2) == got:
            return s.set_cell(i, 4, f"{cm.group(1)}:{want}"), \
                (f"line {i + 1}: {op} declared {got}; its opcode class "
                 f"requires {want}")
    return None


def _fix_operand_separator(s: Source, msg: str) -> Optional[Tuple[Source, str]]:
    """A source operand list written with the wrong separator, or lower case."""
    m = re.search(r"bad register (\S+)", msg)
    if not m:
        return None
    tok = m.group(1)
    for i in s.row_indices():
        c = s.cells(i)
        if len(c) < 6:
            continue
        cell = c[5].strip()
        if tok not in cell:
            continue
        parts = [p for p in re.split(r"[,;\s]+", cell) if p]
        if len(parts) > 1 and all(re.match(r"[Rr]\d+$", p) for p in parts):
            fixed = SEP.join(p.upper() for p in parts)
            return s.set_cell(i, 5, fixed), \
                (f"line {i + 1}: source operands {cell!r} were not separated "
                 f"by U+203A; wrote {fixed!r}")
        if re.match(r"[Rr]\d+$", cell) and cell != cell.upper():
            return s.set_cell(i, 5, cell.upper()), \
                f"line {i + 1}: register names are upper case"
        if SEP in cell:
            up = SEP.join(p.strip().upper() for p in cell.split(SEP))
            if up != cell:
                return s.set_cell(i, 5, up), \
                    f"line {i + 1}: register names are upper case"
    return None


def _fix_arg_order(s: Source, msg: str) -> Optional[Tuple[Source, str]]:
    if "ARG keys must be lexically ordered" not in msg:
        return None
    for i in s.row_indices():
        c = s.cells(i)
        if len(c) < 7:
            continue
        cell = c[6].strip()
        if ";" not in cell:
            continue
        parts = [p for p in cell.split(";") if p]
        ordered = sorted(parts, key=lambda p: p.split("=")[0])
        if ordered != parts:
            return s.set_cell(i, 6, ";".join(ordered)), \
                (f"line {i + 1}: ARG keys sorted, {cell!r} -> "
                 f"{';'.join(ordered)!r}")
    return None


def _slug(text: str) -> str:
    out = re.sub(r"[^A-Za-z0-9]+", "-", text.strip()).strip("-").lower()
    return out[:48] or "note"


def _fix_meta(s: Source, msg: str) -> Optional[Tuple[Source, str]]:
    if "META must be provenance key=value" not in msg:
        return None
    for i in s.row_indices():
        c = s.cells(i)
        if len(c) < 8:
            continue
        cell = c[7].strip()
        if not cell or cell == "_" or re.match(r"^[a-z_][\w.]*=", cell):
            continue
        return s.set_cell(i, 7, f"note={_slug(cell)}"), \
            (f"line {i + 1}: META is key=value, not prose; wrote "
             f"note={_slug(cell)}")
    return None


def _fix_empty_cell(s: Source, msg: str) -> Optional[Tuple[Source, str]]:
    """A cell left blank where the language writes an explicit empty marker."""
    if ("ARG token must be key=value" not in msg
            and "expected key=value" not in msg):
        return None
    for i in s.row_indices():
        c = s.cells(i)
        for col in (6, 7):
            if col < len(c) and c[col].strip() == "":
                return s.set_cell(i, col, "_"), \
                    (f"line {i + 1}: an empty {COLUMNS[col]} cell is written "
                     f"_, which is the language's empty marker")
    return None


def _fix_columns(s: Source, msg: str) -> Optional[Tuple[Source, str]]:
    """A row missing its trailing ARG or META cell -- the only safe padding."""
    m = re.search(r"line (\d+): exactly 8 canonical columns required", msg)
    if not m:
        return None
    i = int(m.group(1)) - 1
    if not (0 <= i < len(s.lines)):
        return None
    c = s.cells(i)
    if not 6 <= len(c) < 8:
        return None                      # too many columns is not determinate
    padded = c + ["_"] * (8 - len(c))
    return s.replace_line(i, "│".join(padded)), \
        (f"line {i + 1}: padded {len(c)} columns to 8 with empty cells; a row "
         f"missing trailing cells is the only case that is unambiguous")


def _fix_destination(s: Source, msg: str) -> Optional[Tuple[Source, str]]:
    m = re.search(r"(\w+): destination operand contract violation", msg)
    if not m:
        return None
    op = m.group(1)
    for i in s.row_indices():
        c = s.cells(i)
        if len(c) < 4 or c[2].strip() != op:
            continue
        out = c[3].strip()
        if op in NO_DEST and out != "_":
            return s.set_cell(i, 3, "_"), \
                (f"line {i + 1}: {op} produces no value, so its OUT column "
                 f"is _ (was {out})")
        if op not in NO_DEST and out == "_":
            free = s.free_register()
            if not free:
                return None
            return s.set_cell(i, 3, free), \
                (f"line {i + 1}: {op} must name a destination register; used "
                 f"{free}, which nothing else in this source reads")
    return None


def _fix_canonical_integer(s: Source, msg: str) -> Optional[Tuple[Source, str]]:
    m = re.search(r"non-canonical (?:constant expression|integer) (\S+)", msg)
    if not m:
        return None
    tok = m.group(1)
    body = tok.replace("_", "").lstrip("+")
    if body.lower().startswith("0x"):
        try:
            canon = hex(int(body, 16))
        except ValueError:
            return None
    else:
        if not re.fullmatch(r"[0-9]+", body):
            return None
        canon = str(int(body))
    if canon == tok:
        return None
    return Source(s.text.replace(f"={tok}", f"={canon}")), \
        f"wrote the immediate {tok} in canonical form as {canon}"


def _fix_falls_off_end(s: Source, msg: str) -> Optional[Tuple[Source, str]]:
    if "falls off end without" not in msg and "falls off program" not in msg:
        return None
    rows = s.row_indices()
    if not rows:
        return None
    last = rows[-1]
    nid = s.next_id()
    row = f"{nid}│exec│HALT│_│C0:CONTROL│_│_│note=added-by-studio-fix"
    return s.insert(last + 1, row), \
        (f"appended a HALT row ({nid}); the program ran off the end, and "
         f"halting is the only ending that does not change what it computes")


FIXES: List[Dict[str, object]] = [
    {"id": "encoding", "fn": _fix_encoding,
     "for": "CR prohibited / source must be NFC / trailing whitespace",
     "does": "canonicalises the bytes of the file"},
    {"id": "magic", "fn": _fix_magic,
     "for": "unsupported/missing LCTLC/1.2",
     "does": "inserts the magic line"},
    {"id": "structure", "fn": _fix_structure,
     "for": "row outside table / missing @unit/header/@end",
     "does": "inserts the column header row, or the @end terminator"},
    {"id": "duplicate_header", "fn": _fix_duplicate_header,
     "for": "duplicate header", "does": "removes the second header row"},
    {"id": "unit_value", "fn": _fix_unit_value,
     "for": "@unit <key> must be <value> / missing @unit <key>",
     "does": "sets the @unit attribute to the value the compiler names"},
    {"id": "termination", "fn": _fix_termination,
     "for": "loop requires termination=budgeted",
     "does": "declares how a cyclic unit ends"},
    {"id": "capabilities", "fn": _fix_caps,
     "for": "<op>: capability <cap> exceeds @unit declaration",
     "does": "adds the capability to br_request_caps"},
    {"id": "declared_capability", "fn": _fix_declared_capability,
     "for": "<op>: declared capability <a>, expected <b>",
     "does": "rewrites the row's CTRL cell to the capability its opcode "
             "class requires"},
    {"id": "operand_separator", "fn": _fix_operand_separator,
     "for": "bad register <token>",
     "does": "separates source operands with U+203A and upper-cases "
             "register names"},
    {"id": "arg_order", "fn": _fix_arg_order,
     "for": "ARG keys must be lexically ordered",
     "does": "sorts the ARG keys"},
    {"id": "meta", "fn": _fix_meta,
     "for": "META must be provenance key=value",
     "does": "turns prose in META into note=<slug>"},
    {"id": "empty_cell", "fn": _fix_empty_cell,
     "for": "ARG token must be key=value, where the cell is blank",
     "does": "writes _ in a cell left empty, and nothing where the cell "
             "holds something the studio would have to interpret"},
    {"id": "columns", "fn": _fix_columns,
     "for": "line <n>: exactly 8 canonical columns required",
     "does": "pads a row that is missing trailing cells"},
    {"id": "destination", "fn": _fix_destination,
     "for": "<op>: destination operand contract violation",
     "does": "empties OUT for opcodes that produce nothing, or names an "
             "unused register for those that must have one"},
    {"id": "canonical_integer", "fn": _fix_canonical_integer,
     "for": "non-canonical integer / constant expression",
     "does": "rewrites the immediate in canonical form"},
    {"id": "falls_off_end", "fn": _fix_falls_off_end,
     "for": "program falls off end without HALT/RET/JMPR/YIELD",
     "does": "appends a HALT row"},
]

# Refusals that are deliberately NOT repaired, with the reason -- so that a
# caller can tell "the studio cannot" from "the studio has not thought about
# it". Each of these needs a value or a decision that is not in the source.
DECLINED: List[Dict[str, str]] = [
    {"matches": "requires imm",
     "why": "the immediate is a value only the author knows"},
    {"matches": "requires svc",
     "why": "which service to call is the program's meaning, not its form"},
    {"matches": "requires target",
     "why": "which row to branch to is the program's meaning"},
    {"matches": "requires offset",
     "why": "which object or address to use is the program's meaning"},
    {"matches": "invalid branch target",
     "why": "the intended destination cannot be inferred from a wrong one"},
    {"matches": "invalid opcode",
     "why": "guessing which opcode was meant would change the program"},
    {"matches": "invalid/duplicate ID",
     "why": "renumbering a row would silently redirect every branch to it"},
    {"matches": "source operand count violation",
     "why": "adding or dropping an operand changes what is computed"},
    {"matches": "too many instructions",
     "why": "the program is over the VM's limit and must be made smaller"},
    {"matches": "unreachable executable instruction",
     "why": "whether the row or the branch is wrong is the author's call"},
    {"matches": "no executable rows",
     "why": "there is no program here to repair"},
]


def catalogue() -> Dict[str, object]:
    """What this module will and will not do, for `describe` to hand over."""
    return {
        "schema": SCHEMA,
        "repairs": [{"id": f["id"], "for": f["for"], "does": f["does"]}
                    for f in FIXES],
        "declines": DECLINED,
        "rule": "only corrections with one legal form are applied, one per "
                "round, each re-checked by the runtime's own compiler, and "
                "every edit is reported",
        "how": "studio try --from - --fix, or studio fix FILE [--write]",
    }


# Which refusal each correction answers, stated rather than inferred: a
# caller asking "would you fix this?" gets the same answer the repair loop
# would give, without having to run it.
ANSWERS: List[Tuple[str, str]] = [
    ("CR prohibited", "encoding"),
    ("source must be NFC", "encoding"),
    ("trailing whitespace", "encoding"),
    ("unsupported/missing LCTLC", "magic"),
    ("row outside table", "structure"),
    ("missing @unit/header/@end", "structure"),
    ("duplicate header", "duplicate_header"),
    ("must be 4.3.0", "unit_value"),
    ("@unit ", "unit_value"),
    ("loop requires termination=budgeted", "termination"),
    ("exceeds @unit declaration", "capabilities"),
    ("declared capability", "declared_capability"),
    ("bad register", "operand_separator"),
    ("ARG keys must be lexically ordered", "arg_order"),
    ("META must be provenance key=value", "meta"),
    ("canonical columns required", "columns"),
    ("ARG token must be key=value", "empty_cell"),
    ("destination operand contract violation", "destination"),
    ("non-canonical integer", "canonical_integer"),
    ("non-canonical constant expression", "canonical_integer"),
    ("falls off end without", "falls_off_end"),
    ("falls off program", "falls_off_end"),
]


def fixable(message: str) -> Optional[str]:
    """The correction this refusal would be answered with, if any."""
    m = (message or "").lower()
    for needle, rule in ANSWERS:
        if needle.lower() in m:
            return rule
    return None


def repair(source: str, compile_probe: Callable[[str], Optional[str]],
           max_rounds: int = 24) -> Dict[str, object]:
    """Correct what has one correct form, until the compiler is satisfied.

    `compile_probe` takes a source and returns the compiler's refusal, or None
    if it compiled. Nothing here decides whether a program is valid.
    """
    cur = Source(source)
    applied: List[Dict[str, object]] = []
    seen: List[str] = []
    error = compile_probe(cur.text)
    rounds = 0
    while error and rounds < max_rounds:
        rounds += 1
        step = None
        for f in FIXES:
            got = f["fn"](cur, error)                          # type: ignore
            if got is not None:
                nxt, what = got
                if nxt.text != cur.text:
                    step = (f["id"], nxt, what)
                    break
        if step is None:
            declined = next((d for d in DECLINED
                             if d["matches"].lower() in error.lower()), None)
            return {"schema": SCHEMA, "compiled": False, "source": cur.text,
                    "repairs": applied, "rounds": rounds, "error": error,
                    "declined": declined,
                    "reason": (declined or {}).get(
                        "why", "no determinate correction is defined for this "
                               "refusal, and guessing would change the "
                               "program")}
        rule, nxt, what = step
        applied.append({"rule": rule, "refusal": error, "change": what})
        cur = nxt
        seen.append(error)
        error = compile_probe(cur.text)
        if error and seen.count(error) > 2:
            return {"schema": SCHEMA, "compiled": False, "source": cur.text,
                    "repairs": applied, "rounds": rounds, "error": error,
                    "declined": None,
                    "reason": "the same refusal survived its correction, so "
                              "the studio stopped rather than loop"}
    return {"schema": SCHEMA, "compiled": error is None, "source": cur.text,
            "repairs": applied, "rounds": rounds, "error": error,
            "declined": None,
            "reason": "" if error is None else
                      f"still refused after {rounds} rounds"}
