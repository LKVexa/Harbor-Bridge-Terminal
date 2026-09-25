"""Recursive-descent WIT parser with explicit recovery points (INV11-MC-01).

Recovery guarantee (docs/GRAMMAR.md): a syntax error inside an interface/world
item abandons that item only and resumes at the next `;` or the `}` closing
the enclosing block; an error at top level resumes at the next `interface`,
`world`, `package` or `use` keyword.  Lexical errors, UTF-8 errors and limit
breaches stop parsing of that file (fatal).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import ast
from .diagnostics import DiagnosticBag, Span
from .lexer import Token, tokenize
from .limits import DEFAULT_LIMITS, LimitExceeded, Limits
from .source import SourceFile, from_memory

PRIM_KEYWORDS = set(ast.PRIMITIVES) | set(ast.PRIM_ALIASES)
GATE_NAMES = {"since": "version", "unstable": "feature", "deprecated": "version"}


class _Abort(Exception):
    pass


@dataclass(frozen=True)
class ParseConfig:
    """Explicit feature/version configuration; the parser reads no globals."""
    limits: Limits = DEFAULT_LIMITS
    allow_async: bool = False  # future/stream/async func: beyond the pinned level, opt-in only
    allow_fixed_lists: bool = False  # list<T, N> requires the fixed-size-list feature
    allow_nested_packages: bool = True


@dataclass
class ParseResult:
    documents: list[ast.Document] = field(default_factory=list)
    diagnostics: DiagnosticBag = field(default_factory=DiagnosticBag)
    fatal: bool = False
    sources: list[SourceFile] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.fatal and not self.diagnostics.errors

    def status(self) -> str:
        if self.fatal:
            return "FATAL"
        if self.diagnostics.errors:
            return "RECOVERED_WITH_ERRORS"
        if self.diagnostics.items:
            return "OK_WITH_WARNINGS"
        return "OK"


class Parser:
    def __init__(self, src: SourceFile, diags: DiagnosticBag, config: ParseConfig) -> None:
        self.src, self.diags, self.cfg = src, diags, config
        self.toks: list[Token] = tokenize(src, diags, config.limits).tokens
        self.i = 0
        self.depth = 0
        self.decls = 0

    # -- token helpers -------------------------------------------------
    @property
    def tok(self) -> Token:
        return self.toks[self.i]

    def peek(self, k: int = 1) -> Token:
        return self.toks[min(self.i + k, len(self.toks) - 1)]

    def span(self, t: Token) -> Span:
        return self.src.span(t.start, t.end)

    def span_from(self, t: Token) -> Span:
        prev = self.toks[max(self.i - 1, 0)]
        return self.src.span(t.start, max(prev.end, t.end))

    def at(self, kind: str, text: str | None = None) -> bool:
        t = self.tok
        return t.kind == kind and (text is None or t.text == text)

    def at_kw(self, word: str) -> bool:
        return self.tok.kind == "KEYWORD" and self.tok.text == word

    def eat(self, kind: str, text: str | None = None) -> bool:
        if self.at(kind, text):
            self.i += 1
            return True
        return False

    def expect(self, kind: str, text: str | None = None, what: str | None = None) -> Token:
        t = self.tok
        if self.at(kind, text):
            self.i += 1
            return t
        want = what or text or kind
        if t.kind == "EOF":
            self.diags.add("E-PARSE-EOF", f"expected {want}, found end of input", self.span(t))
        else:
            self.diags.add("E-PARSE-EXPECTED", f"expected {want}, found {t.raw!r}", self.span(t))
        raise _Abort()

    def ident(self, what: str = "identifier") -> Token:
        return self.expect("IDENT", what=what)

    def enter(self) -> None:
        self.depth += 1
        self.cfg.limits.check("nesting", self.depth)

    def leave(self) -> None:
        self.depth -= 1

    def count_decl(self) -> None:
        self.decls += 1
        self.cfg.limits.check("declarations", self.decls)

    def sync_item(self) -> None:
        """Recover to after the next ';' or to (not past) the enclosing '}'."""
        depth = 0
        while not self.at("EOF"):
            k = self.tok.kind
            if k in ("LBRACE",):
                depth += 1
            elif k == "RBRACE":
                if depth == 0:
                    return
                depth -= 1
                if depth == 0:
                    self.i += 1
                    return
            elif k == "SEMI" and depth == 0:
                self.i += 1
                return
            self.i += 1

    def sync_top(self) -> None:
        while not self.at("EOF"):
            if self.tok.kind == "KEYWORD" and self.tok.text in ("interface", "world", "package", "use"):
                return
            self.i += 1

    # -- grammar -------------------------------------------------------
    def gates(self) -> tuple[ast.Gate, ...]:
        out: list[ast.Gate] = []
        while self.at("AT") and self.peek().kind == "IDENT" and self.peek().text in GATE_NAMES:
            start = self.tok
            self.i += 1
            name = self.tok.text
            self.i += 1
            self.expect("LPAREN")
            key = self.ident(GATE_NAMES[name])
            if key.text != GATE_NAMES[name]:
                self.diags.add("E-PARSE-EXPECTED", f"@{name} takes `{GATE_NAMES[name]} = ...`", self.span(key))
                raise _Abort()
            self.expect("EQ")
            if GATE_NAMES[name] == "version":
                val = self.expect("VERSION", what="semantic version").text
            else:
                val = self.ident("feature name").text
            self.expect("RPAREN")
            if any(g.kind == name for g in out) or (name in ("since", "unstable") and any(g.kind in ("since", "unstable") for g in out)):
                self.diags.add("E-DUP-GATE", f"conflicting @{name} gate", self.span_from(start))
            out.append(ast.Gate(name, val))
        if any(g.kind == "deprecated" for g in out) and not any(g.kind in ("since", "unstable") for g in out):
            self.diags.add("E-GATE-PAIR", "@deprecated without @since/@unstable", self.span(self.toks[self.i - 1]))
        return tuple(out)

    def version(self) -> str | None:
        if self.eat("AT"):
            return self.expect("VERSION", what="semantic version").text
        return None

    def package_name(self) -> tuple[str, str, str | None]:
        ns = self.ident("package namespace").text
        self.expect("COLON")
        name = self.ident("package name").text
        while self.at("COLON"):  # nested namespace segments are not supported
            self.diags.add("E-PARSE-UNSUPPORTED", "nested package namespaces (a:b:c) are not supported", self.span(self.tok))
            raise _Abort()
        return ns, name, self.version()

    def use_path(self) -> ast.UsePath:
        start = self.tok
        first = self.ident("interface or package")
        if self.eat("COLON"):
            pkg = self.ident("package name")
            self.expect("SLASH")
            iface = self.ident("interface name")
            ver = self.version()
            return ast.UsePath(f"{first.text}:{pkg.text}", iface.text, ver, self.span_from(start))
        return ast.UsePath(None, first.text, None, self.span_from(start))

    def parse_type(self) -> ast.Type:
        self.enter()
        try:
            t = self.tok
            if t.kind == "KEYWORD":
                w = t.text
                if w in PRIM_KEYWORDS:
                    self.i += 1
                    return ast.Prim(ast.PRIM_ALIASES.get(w, w), self.span(t))
                if w == "list":
                    self.i += 1
                    self.expect("LT")
                    elem = self.parse_type()
                    size = None
                    if self.eat("COMMA"):
                        n = self.expect("INT", what="list length")
                        if not self.cfg.allow_fixed_lists:
                            self.diags.add("E-PARSE-UNSUPPORTED", "fixed-length list<T, N> requires the fixed-size-list feature", self.span(n))
                        size = int(n.text)
                    self.expect("GT")
                    return ast.ListT(elem, size, self.span_from(t))
                if w == "option":
                    self.i += 1
                    self.expect("LT")
                    inner = self.parse_type()
                    self.expect("GT")
                    return ast.OptionT(inner, self.span_from(t))
                if w == "result":
                    self.i += 1
                    ok = err = None
                    if self.eat("LT"):
                        if self.eat("UNDERSCORE"):
                            self.expect("COMMA")
                            err = self.parse_type()
                        else:
                            ok = self.parse_type()
                            if self.eat("COMMA"):
                                err = self.parse_type()
                        self.expect("GT")
                    return ast.ResultT(ok, err, self.span_from(t))
                if w == "tuple":
                    self.i += 1
                    self.expect("LT")
                    items: list[ast.Type] = []
                    while not self.at("GT"):
                        items.append(self.parse_type())
                        if not self.eat("COMMA"):
                            break
                    self.expect("GT")
                    return ast.TupleT(tuple(items), self.span_from(t))
                if w in ("own", "borrow"):
                    self.i += 1
                    self.expect("LT")
                    r = self.ident("resource name")
                    self.expect("GT")
                    return ast.Handle(w, r.text, self.span_from(t))
                if w in ("future", "stream"):
                    self.i += 1
                    if not self.cfg.allow_async:
                        self.diags.add("E-PARSE-UNSUPPORTED", f"{w} requires the component-model async feature", self.span(t))
                    payload: ast.Type | None = None
                    if self.eat("LT"):
                        payload = self.parse_type()
                        self.expect("GT")
                    return ast.AsyncT(w, payload, self.span_from(t))
                if w == "error-context":
                    self.diags.add("E-PARSE-UNSUPPORTED", "error-context is not supported at this feature level", self.span(t))
                    raise _Abort()
            if t.kind == "IDENT":
                self.i += 1
                return ast.Ref(t.text, self.span(t))
            self.expect("IDENT", what="type")
            raise _Abort()  # pragma: no cover
        finally:
            self.leave()

    def params(self) -> tuple[ast.Param, ...]:
        self.expect("LPAREN")
        out: list[ast.Param] = []
        seen: dict[str, ast.Param] = {}
        while not self.at("RPAREN"):
            start = self.tok
            name = self.ident("parameter name")
            self.expect("COLON")
            p = ast.Param(name.text, self.parse_type(), self.span_from(start))
            if p.name in seen:
                self.diags.add("E-DUP-MEMBER", f"duplicate parameter {p.name!r}", p.span, related=[s for s in (seen[p.name].span,) if s])
            seen[p.name] = p
            out.append(p)
            if not self.eat("COMMA"):
                break
        self.expect("RPAREN")
        return tuple(out)

    def func_sig(self, name: str, start: Token, gates: tuple[ast.Gate, ...], doc: str, kind: str = "freestanding") -> ast.Func:
        is_async = self.eat("KEYWORD", "async")
        if is_async and not self.cfg.allow_async:
            self.diags.add("E-PARSE-UNSUPPORTED", "async func requires the component-model async feature", self.span(start))
        self.expect("KEYWORD", "func", "`func`")
        ps = self.params()
        res = None
        if self.eat("ARROW"):
            if self.at("LPAREN"):
                self.diags.add("E-PARSE-UNSUPPORTED", "named/multiple results were removed from WIT; use a record or tuple", self.span(self.tok))
                raise _Abort()
            res = self.parse_type()
        return ast.Func(name, ps, res, kind, is_async, gates, doc, self.span_from(start))

    def members(self, kind: str) -> tuple[ast.Member, ...]:
        self.expect("LBRACE")
        out: list[ast.Member] = []
        seen: dict[str, ast.Member] = {}
        while not self.at("RBRACE"):
            start = self.tok
            g = self.gates()
            name = self.ident(f"{kind} member")
            typ = None
            if kind == "record":
                self.expect("COLON")
                typ = self.parse_type()
            elif kind == "variant" and self.eat("LPAREN"):
                typ = self.parse_type()
                self.expect("RPAREN")
            m = ast.Member(name.text, typ, g, start.doc, self.span_from(start))
            if m.name in seen:
                self.diags.add("E-DUP-MEMBER", f"duplicate {kind} member {m.name!r}", m.span, related=[s for s in (seen[m.name].span,) if s])
            seen[m.name] = m
            out.append(m)
            if not self.eat("COMMA"):
                break
        self.expect("RBRACE")
        if kind in ("variant", "enum") and not out:
            self.diags.add("E-PARSE-EXPECTED", f"{kind} must have at least one case", self.span(self.toks[self.i - 1]))
        return tuple(out)

    def typedef(self, gates: tuple[ast.Gate, ...], start: Token) -> ast.TypeDecl:
        kw = self.tok.text
        self.i += 1
        name = self.ident("type name")
        self.count_decl()
        if kw == "type":
            self.expect("EQ")
            target = self.parse_type()
            self.expect("SEMI")
            return ast.TypeDecl(name.text, "alias", target, gates=gates, doc=start.doc, span=self.span_from(start))
        if kw in ("record", "variant", "enum", "flags"):
            ms = self.members(kw)
            return ast.TypeDecl(name.text, kw, None, ms, gates=gates, doc=start.doc, span=self.span_from(start))
        # resource
        funcs: list[ast.Func] = []
        if self.eat("SEMI"):
            return ast.TypeDecl(name.text, "resource", gates=gates, doc=start.doc, span=self.span_from(start))
        self.expect("LBRACE")
        self.enter()
        seen: dict[str, ast.Func] = {}
        while not self.at("RBRACE") and not self.at("EOF"):
            fstart = self.tok
            try:
                g = self.gates()
                if self.eat("KEYWORD", "constructor"):
                    ps = self.params()
                    res = None
                    if self.eat("ARROW"):
                        res = self.parse_type()
                    f = ast.Func("constructor", ps, res, "constructor", False, g, fstart.doc, self.span_from(fstart))
                else:
                    fname = self.ident("method name")
                    self.expect("COLON")
                    kind = "static" if self.eat("KEYWORD", "static") else "method"
                    f = self.func_sig(fname.text, fstart, g, fstart.doc, kind)
                self.expect("SEMI")
                if f.name in seen:
                    self.diags.add("E-DUP-MEMBER", f"duplicate resource member {f.name!r}", f.span, related=[s for s in (seen[f.name].span,) if s])
                seen[f.name] = f
                funcs.append(f)
            except _Abort:
                self.sync_item()
        self.leave()
        self.expect("RBRACE")
        return ast.TypeDecl(name.text, "resource", funcs=tuple(funcs), gates=gates, doc=start.doc, span=self.span_from(start))

    def use_item(self, start: Token) -> ast.Use:
        self.i += 1  # 'use'
        path = self.use_path()
        self.expect("DOT")
        self.expect("LBRACE")
        names: list[tuple[str, str]] = []
        while not self.at("RBRACE"):
            n = self.ident("imported name").text
            alias = n
            if self.eat("KEYWORD", "as"):
                alias = self.ident("alias").text
            names.append((n, alias))
            if not self.eat("COMMA"):
                break
        self.expect("RBRACE")
        self.expect("SEMI")
        return ast.Use(path, tuple(names), self.span_from(start))

    def interface_body(self, name: str, start: Token, gates: tuple[ast.Gate, ...]) -> ast.Interface:
        self.expect("LBRACE")
        self.enter()
        types: list[ast.TypeDecl] = []
        funcs: list[ast.Func] = []
        uses: list[ast.Use] = []
        while not self.at("RBRACE") and not self.at("EOF"):
            istart = self.tok
            try:
                g = self.gates()
                if self.at_kw("use"):
                    uses.append(self.use_item(istart))
                elif self.tok.kind == "KEYWORD" and self.tok.text in ("type", "record", "variant", "enum", "flags", "resource"):
                    types.append(self.typedef(g, istart))
                elif self.at("IDENT"):
                    fname = self.ident()
                    self.expect("COLON")
                    self.count_decl()
                    funcs.append(self.func_sig(fname.text, istart, g, istart.doc))
                    self.expect("SEMI")
                else:
                    self.expect("IDENT", what="interface item")
            except _Abort:
                self.sync_item()
        self.leave()
        self.expect("RBRACE")
        return ast.Interface(name, tuple(types), tuple(funcs), tuple(uses), gates, start.doc, self.span_from(start))

    def world_body(self, name: str, start: Token, gates: tuple[ast.Gate, ...]) -> ast.World:
        self.expect("LBRACE")
        self.enter()
        items: list[ast.WorldItem] = []
        types: list[ast.TypeDecl] = []
        uses: list[ast.Use] = []
        includes: list[ast.Include] = []
        while not self.at("RBRACE") and not self.at("EOF"):
            istart = self.tok
            try:
                g = self.gates()
                if self.tok.kind == "KEYWORD" and self.tok.text in ("import", "export"):
                    direction = self.tok.text
                    self.i += 1
                    self.count_decl()
                    if self.at("IDENT") and self.peek().kind == "COLON" and self.peek(2).kind == "KEYWORD" and self.peek(2).text in ("func", "async", "interface"):
                        ename = self.ident().text
                        self.expect("COLON")
                        if self.at_kw("interface"):
                            self.i += 1
                            inline = self.interface_body(ename, istart, ())
                            self.eat("SEMI")
                            items.append(ast.WorldItem(direction, ename, "inline-interface", inline=inline, gates=g, span=self.span_from(istart)))
                        else:
                            f = self.func_sig(ename, istart, g, istart.doc)
                            self.expect("SEMI")
                            items.append(ast.WorldItem(direction, ename, "func", func=f, gates=g, span=self.span_from(istart)))
                    else:
                        p = self.use_path()
                        self.expect("SEMI")
                        items.append(ast.WorldItem(direction, p.text(), "interface-ref", ref=p, gates=g, span=self.span_from(istart)))
                elif self.at_kw("include"):
                    self.i += 1
                    p = self.use_path()
                    renames: list[tuple[str, str]] = []
                    if self.eat("KEYWORD", "with"):
                        self.expect("LBRACE")
                        while not self.at("RBRACE"):
                            a = self.ident().text
                            self.expect("KEYWORD", "as", "`as`")
                            renames.append((a, self.ident().text))
                            if not self.eat("COMMA"):
                                break
                        self.expect("RBRACE")
                    self.expect("SEMI")
                    includes.append(ast.Include(p, tuple(renames), self.span_from(istart)))
                elif self.at_kw("use"):
                    uses.append(self.use_item(istart))
                elif self.tok.kind == "KEYWORD" and self.tok.text in ("type", "record", "variant", "enum", "flags", "resource"):
                    types.append(self.typedef(g, istart))
                else:
                    self.expect("KEYWORD", what="`import`, `export`, `include`, `use` or a type definition")
            except _Abort:
                self.sync_item()
        self.leave()
        self.expect("RBRACE")
        return ast.World(name, tuple(items), tuple(types), tuple(uses), tuple(includes), gates, start.doc, self.span_from(start))

    def document(self, stop_at_rbrace: bool = False, package: tuple[str, str, str | None] | None = None,
                 pkg_span: Span | None = None) -> ast.Document:
        interfaces: list[ast.Interface] = []
        worlds: list[ast.World] = []
        uses: list[ast.TopUse] = []
        nested: list[ast.Document] = []
        while not self.at("EOF") and not (stop_at_rbrace and self.at("RBRACE")):
            start, start_i = self.tok, self.i
            try:
                g = self.gates()
                if self.at_kw("package"):
                    self.i += 1
                    pk = self.package_name()
                    if self.at("LBRACE"):
                        if not self.cfg.allow_nested_packages or stop_at_rbrace:
                            self.diags.add("E-PARSE-UNSUPPORTED", "nested package blocks are not allowed here", self.span(start))
                            raise _Abort()
                        self.i += 1
                        self.enter()
                        nested.append(self.document(True, pk, self.span_from(start)))
                        self.leave()
                        self.expect("RBRACE")
                    else:
                        self.expect("SEMI")
                        if package is not None or interfaces or worlds or uses:
                            self.diags.add("E-PARSE-PACKAGE", "package declaration must be first and appear once", self.span_from(start))
                        else:
                            package, pkg_span = pk, self.span_from(start)
                elif self.at_kw("interface"):
                    self.i += 1
                    n = self.ident("interface name")
                    self.count_decl()
                    interfaces.append(self.interface_body(n.text, start, g))
                elif self.at_kw("world"):
                    self.i += 1
                    n = self.ident("world name")
                    self.count_decl()
                    worlds.append(self.world_body(n.text, start, g))
                elif self.at_kw("use"):
                    self.i += 1
                    p = self.use_path()
                    alias = self.ident("alias").text if self.eat("KEYWORD", "as") else None
                    self.expect("SEMI")
                    uses.append(ast.TopUse(p, alias, self.span_from(start)))
                else:
                    self.expect("KEYWORD", what="`package`, `interface`, `world` or `use`")
            except _Abort:
                if self.i == start_i:
                    self.i += 1  # guarantee progress
                if stop_at_rbrace:
                    self.sync_item()
                else:
                    self.sync_top()
        return ast.Document(self.src.name, package, tuple(interfaces), tuple(worlds), tuple(uses), tuple(nested), pkg_span)


def parse_sources(sources: list[SourceFile], config: ParseConfig | None = None,
                  diags: DiagnosticBag | None = None) -> ParseResult:
    config = config or ParseConfig()
    diags = diags or DiagnosticBag(config.limits.max_diagnostics)
    res = ParseResult(diagnostics=diags, sources=list(sources))
    for src in sources:
        try:
            p = Parser(src, diags, config)
            if any(d.code.startswith("E-LEX") and d.span and d.span.file == src.name for d in diags.errors):
                res.fatal = True
                continue
            res.documents.append(p.document())
        except LimitExceeded as exc:
            diags.add("E-LIMIT", str(exc))
            res.fatal = True
        except RecursionError:
            diags.add("E-LIMIT", "nesting exceeded the interpreter stack")
            res.fatal = True
    return res


def parse_text(text: str | bytes, label: str = "input.wit", config: ParseConfig | None = None) -> ParseResult:
    config = config or ParseConfig()
    diags = DiagnosticBag(config.limits.max_diagnostics)
    try:
        src = from_memory(label, text, diags, config.limits)
    except LimitExceeded as exc:
        diags.add("E-LIMIT", str(exc))
        return ParseResult(diagnostics=diags, fatal=True)
    if src is None:
        return ParseResult(diagnostics=diags, fatal=True)
    return parse_sources([src], config, diags)
