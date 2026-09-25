"""Operator CLI: ``python -m inv10_component_composition_system.cli <cmd>``.

Commands: compose MANIFEST | explain MANIFEST | diff A.json B.json |
migrate RECORDS.json | wit FILE WORLD | schema-check RESULT.json | version
Exit codes: 0 ok, 1 refused (machine-readable error on stdout), 2 usage.
"""
from __future__ import annotations

import json
import pathlib
import sys

from . import __version__
from .composition import CompositionError
from . import features, manifest, observability, schemas, wit


def _out(obj) -> None:
    print(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    a = list(sys.argv[1:] if argv is None else argv)
    if not a:
        print(__doc__, file=sys.stderr)
        return 2
    cmd, args = a[0], a[1:]
    try:
        if cmd == "version":
            _out({"version": __version__, "schema": "PK_COMPOSITION/1", "identity_profile": "PK_COMPOSITION_ID/2"})
        elif cmd in {"compose", "explain"}:
            m = manifest.load(args[0])
            if cmd == "compose":
                _out(features.compose_extended(m.units, external=m.external, aliases=m.aliases or None))
            else:
                try:
                    res = features.compose_extended(m.units, external=m.external, aliases=m.aliases or None)
                    err = None
                except CompositionError as exc:
                    res, err = None, exc.as_dict()
                units = features.apply_aliases(m.units, m.aliases) if m.aliases else m.units
                rep = observability.explain(units, external=m.external, result=res, error=err)
                print(observability.render_explain_text(rep))
                return 1 if err else 0
        elif cmd == "diff":
            _out(features.diff(*(json.loads(pathlib.Path(p).read_text()) for p in args[:2])))
        elif cmd == "migrate":
            _out(features.migrate_legacy(json.loads(pathlib.Path(args[0]).read_text())))
        elif cmd == "wit":
            u = wit.parse(pathlib.Path(args[0]).read_text()).to_unit(args[1])
            _out(schemas.component_document(u))
        elif cmd == "schema-check":
            schemas.validate_composition(json.loads(pathlib.Path(args[0]).read_text()))
            _out({"valid": True})
        else:
            print(__doc__, file=sys.stderr)
            return 2
    except CompositionError as exc:
        _out(exc.as_dict())
        return 1
    except (IndexError, FileNotFoundError) as exc:
        print(f"usage error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
