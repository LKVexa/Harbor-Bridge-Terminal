"""Source-span-aware diagnostics with stable codes (INV11-MC-05)."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

ERROR, WARNING, NOTE = "error", "warning", "note"

# Stable code registry: code -> (severity, summary, remediation).  Codes are
# append-only; retired codes stay reserved (see docs/DIAGNOSTICS.md).
CODES: dict[str, tuple[str, str, str]] = {
    "E-SRC-UTF8": (ERROR, "source is not valid UTF-8", "re-encode the file as UTF-8"),
    "E-SRC-IO": (ERROR, "source could not be read", "check the path and permissions"),
    "E-SRC-BOM": (WARNING, "UTF-8 byte-order mark ignored", "remove the BOM"),
    "E-LEX-CHAR": (ERROR, "unexpected character", "remove or escape the character"),
    "E-LEX-IDENT": (ERROR, "malformed identifier", "identifiers are kebab-case words of [a-z0-9] (or [A-Z0-9]) starting with a letter"),
    "E-LEX-COMMENT": (ERROR, "unterminated block comment", "close the comment with */"),
    "E-LEX-VERSION": (ERROR, "malformed semantic version", "use MAJOR.MINOR.PATCH[-pre][+build]"),
    "E-PARSE-EXPECTED": (ERROR, "unexpected token", "see the expected token list"),
    "E-PARSE-EOF": (ERROR, "unexpected end of input", "the declaration is truncated"),
    "E-PARSE-UNSUPPORTED": (ERROR, "unsupported grammar production", "see docs/GRAMMAR.md unsupported list"),
    "E-PARSE-PACKAGE": (ERROR, "package declaration problem", "declare exactly one `package ns:name@ver;` per package"),
    "E-DUP-DECL": (ERROR, "duplicate declaration", "rename or remove one declaration"),
    "E-DUP-MEMBER": (ERROR, "duplicate member", "field/case/param names must be unique"),
    "E-DUP-GATE": (ERROR, "duplicate feature gate", "use at most one @since/@unstable per item"),
    "E-GATE-PAIR": (ERROR, "@deprecated must be paired with @since or @unstable", "add @since(version = ...)"),
    "E-RES-UNKNOWN": (ERROR, "unresolved name", "declare or `use` the name"),
    "E-RES-CYCLE": (ERROR, "dependency cycle", "break the cycle between interfaces/worlds"),
    "E-RES-KIND": (ERROR, "name refers to the wrong kind of item", "reference an interface/world/type as appropriate"),
    "E-RES-PACKAGE": (ERROR, "unknown or conflicting package", "provide the dependency package or pin one version"),
    "E-RES-TYPECYCLE": (ERROR, "recursive type definition", "WIT types may not be recursive; use a resource"),
    "E-RES-HANDLE": (ERROR, "handle of non-resource type", "own/borrow only apply to resources"),
    "E-LIMIT": (ERROR, "resource limit exceeded", "reduce input size or raise the configured limit"),
    "W-DIAG-TRUNCATED": (WARNING, "further diagnostics suppressed", "fix reported errors first"),
}


@dataclass(frozen=True, order=True)
class Span:
    file: str
    start: int  # byte offset into normalized source
    end: int
    line: int
    col: int
    end_line: int = 0
    end_col: int = 0

    def as_dict(self) -> dict[str, object]:
        return {"file": self.file, "start": self.start, "end": self.end, "line": self.line,
                "col": self.col, "end_line": self.end_line or self.line, "end_col": self.end_col or self.col}


@dataclass(frozen=True)
class Diagnostic:
    code: str
    message: str
    span: Span | None = None
    path: str = ""  # symbol path, e.g. ns:pkg/iface.func
    related: tuple[Span, ...] = ()

    @property
    def severity(self) -> str:
        return CODES.get(self.code, (ERROR, "", ""))[0]

    @property
    def hint(self) -> str:
        return CODES.get(self.code, (ERROR, "", ""))[2]

    def sort_key(self) -> tuple[str, int, str, str]:
        s = self.span
        return (s.file if s else "", s.start if s else -1, self.code, self.message)

    def as_dict(self) -> dict[str, object]:
        return {"code": self.code, "severity": self.severity, "message": self.message,
                "span": self.span.as_dict() if self.span else None, "path": self.path,
                "related": [r.as_dict() for r in self.related], "hint": self.hint}

    def render(self) -> str:
        loc = f"{self.span.file}:{self.span.line}:{self.span.col}: " if self.span else ""
        extra = f" [{self.path}]" if self.path else ""
        return f"{loc}{self.severity} {self.code}: {self.message}{extra}\n  hint: {self.hint}"


class DiagnosticBag:
    """Collects diagnostics with a hard cap so hostile input cannot amplify output."""

    def __init__(self, cap: int = 200) -> None:
        self.cap, self.truncated = cap, False
        self.items: list[Diagnostic] = []

    def add(self, code: str, message: str, span: Span | None = None, path: str = "",
            related: Iterable[Span] = ()) -> None:
        if code not in CODES:
            raise KeyError(f"unregistered diagnostic code {code}")
        if len(self.items) >= self.cap:
            self.truncated = True
            return
        self.items.append(Diagnostic(code, message, span, path, tuple(related)))

    @property
    def errors(self) -> list[Diagnostic]:
        return [d for d in self.items if d.severity == ERROR]

    def sorted(self) -> list[Diagnostic]:
        out = sorted(self.items, key=Diagnostic.sort_key)
        if self.truncated:
            out.append(Diagnostic("W-DIAG-TRUNCATED", f"more than {self.cap} diagnostics"))
        return out
