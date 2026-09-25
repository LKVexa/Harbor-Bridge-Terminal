"""WIT tokenizer with spans and trivia (INV11-MC-01 items 002/004/005)."""
from __future__ import annotations

import re
from dataclasses import dataclass

from .diagnostics import DiagnosticBag
from .limits import DEFAULT_LIMITS, Limits
from .source import SourceFile

KEYWORDS = frozenset("""
use type func u8 u16 u32 u64 s8 s16 s32 s64 f32 f64 float32 float64 char record resource own
borrow flags variant enum bool string option result future stream list as from static
interface tuple import export world package constructor include with async error-context
""".split())

PUNCT = {"(": "LPAREN", ")": "RPAREN", "{": "LBRACE", "}": "RBRACE", "<": "LT", ">": "GT",
         ",": "COMMA", ";": "SEMI", ":": "COLON", ".": "DOT", "=": "EQ", "*": "STAR",
         "/": "SLASH", "@": "AT", "_": "UNDERSCORE"}

_IDENT = re.compile(r"%?[A-Za-z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)*")
_WORD_OK = re.compile(r"(?:[a-z][a-z0-9]*|[A-Z][A-Z0-9]*)$")
_NUM = re.compile(r"(0|[1-9][0-9]*)(?:\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
                  r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?)?")


@dataclass(frozen=True)
class Token:
    kind: str  # IDENT KEYWORD VERSION INT punct-name EOF
    text: str  # normalized spelling (identifier without % escape)
    raw: str
    start: int
    end: int
    file: str
    doc: str = ""  # attached /// or /** */ doc comment (trivia, never semantic)


@dataclass
class LexResult:
    tokens: list[Token]
    comments: list[tuple[int, int, str]]


def valid_identifier(word: str) -> bool:
    return all(_WORD_OK.match(w) for w in word.split("-"))


def tokenize(src: SourceFile, diags: DiagnosticBag, limits: Limits = DEFAULT_LIMITS) -> LexResult:
    text, n, i = src.text, len(src.text), 0
    tokens: list[Token] = []
    comments: list[tuple[int, int, str]] = []
    pending_doc: list[str] = []
    while i < n:
        c = text[i]
        if c in " \t\n":
            i += 1
            continue
        if text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j < 0 else j
            body = text[i:j]
            comments.append((i, j, body))
            if body.startswith("///") and not body.startswith("////"):
                pending_doc.append(body[3:].strip())
            i = j
            continue
        if text.startswith("/*", i):
            depth, j = 1, i + 2
            while j < n and depth:
                if text.startswith("/*", j):
                    depth, j = depth + 1, j + 2
                elif text.startswith("*/", j):
                    depth, j = depth - 1, j + 2
                else:
                    j += 1
            if depth:
                diags.add("E-LEX-COMMENT", "block comment never closed", src.span(i, n))
                break
            body = text[i:j]
            comments.append((i, j, body))
            if body.startswith("/**") and body != "/**/":
                pending_doc.append(body[3:-2].strip())
            i = j
            continue
        doc = "\n".join(pending_doc)
        if c == "-" and text.startswith("->", i):
            tokens.append(Token("ARROW", "->", "->", i, i + 2, src.name, doc))
            pending_doc, i = [], i + 2
            continue
        if c.isdigit():
            m = _NUM.match(text, i)
            assert m is not None
            kind = "VERSION" if m.group(2) is not None else "INT"
            end = m.end()
            if end < n and (text[end].isalnum() or text[end] == "_" or (text[end] == "." and end + 1 < n and text[end + 1].isdigit())):
                diags.add("E-LEX-VERSION", f"malformed number/version near {text[i:end + 1]!r}", src.span(i, end + 1))
            tokens.append(Token(kind, m.group(0), m.group(0), i, end, src.name, doc))
            pending_doc, i = [], end
            continue
        m = _IDENT.match(text, i)
        if m and (c.isalpha() or c == "%"):
            raw = m.group(0)
            word = raw[1:] if raw.startswith("%") else raw
            limits.check("identifier", len(word))
            if not valid_identifier(word):
                diags.add("E-LEX-IDENT", f"identifier {raw!r} mixes case within a word", src.span(i, m.end()))
            kind = "KEYWORD" if (word in KEYWORDS and not raw.startswith("%")) else "IDENT"
            tokens.append(Token(kind, word, raw, i, m.end(), src.name, doc))
            pending_doc, i = [], m.end()
            continue
        if c == "_" and (i + 1 >= n or not (text[i + 1].isalnum() or text[i + 1] == "-")):
            tokens.append(Token("UNDERSCORE", "_", "_", i, i + 1, src.name, doc))
            pending_doc, i = [], i + 1
            continue
        if c in PUNCT and c != "_":
            tokens.append(Token(PUNCT[c], c, c, i, i + 1, src.name, doc))
            pending_doc, i = [], i + 1
            continue
        diags.add("E-LEX-CHAR", f"unexpected character {c!r}", src.span(i, i + 1))
        i += 1
        if len(diags.errors) > 50:
            break
        limits.check("tokens", len(tokens))
    limits.check("tokens", len(tokens))
    tokens.append(Token("EOF", "", "", n, n, src.name))
    return LexResult(tokens, comments)
