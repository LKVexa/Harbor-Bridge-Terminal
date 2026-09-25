# Supported image formats and toolchain profiles (normative)

Implements MC-001 / MC-002 / MC-003. Code: `image/elf.py`, `image/facts.py`.

## Accepted container format

| Field | Accepted | Anything else |
|---|---|---|
| magic | `\x7fELF` | `UK_PARSE_BAD_MAGIC` |
| EI_CLASS / EI_DATA / EI_VERSION | ELFCLASS64 / little-endian / 1 | `UK_PARSE_UNSUPPORTED_FORMAT` |
| e_type | ET_EXEC, or ET_DYN **without** PT_INTERP (static-pie) | `UK_PARSE_UNSUPPORTED_FORMAT` (ET_REL, ET_CORE) / `UK_SEAL_DYNAMIC` |
| e_machine | 62 → `x86_64`, 183 → `aarch64` | `UK_PARSE_UNSUPPORTED_FORMAT` |
| e_phentsize / e_shentsize | 56 / 64 | `UK_PARSE_MALFORMED` |

PE, Mach-O, raw multiboot blobs and CBOR/OCI wrappers are not accepted. Adding a format is a minor
version bump with new golden and adversarial fixtures (see `VERSIONING.md`).

## Parser bounds (`elf.Limits`, defaults)

| Limit | Default | Code on breach |
|---|---|---|
| image bytes | 64 MiB | `UK_PARSE_TOO_LARGE` |
| program headers | 64 | `UK_PARSE_LIMIT` |
| section headers | 512 | `UK_PARSE_LIMIT` |
| symbols (all tables) | 200,000 | `UK_PARSE_LIMIT` |
| dynamic entries | 4,096 | `UK_PARSE_LIMIT` |
| notes / note payload | 256 / 64 KiB | `UK_PARSE_LIMIT` |
| relocations | 2,000,000 | `UK_PARSE_LIMIT` |
| name length | 4,096 | `UK_PARSE_MALFORMED` |
| work units | 20,000,000 | `UK_PARSE_BUDGET` |

Structural rules: every table must lie inside the file (overflow-checked). PT_LOAD segments must not
overlap in memory. File-backed sections must not overlap in the file. Section names must be unique.
Symbol and relocation indices must be in range, and `memsz >= filesz`. Relocation entries must
reference an existing symbol.

## Extracted facts

These facts are bound to `parser_version` and the image's sha256 in the decision record: segments,
sections, symbols (both `.symtab` and `.dynsym`), `DT_NEEDED`, `PT_INTERP`, notes, the GNU build-id,
the relocation count and the entry point.

## Toolchain profiles

| Profile | Positive marker (defined func) | Syscall surface | Status |
|---|---|---|---|
| `unikraft` | `ukplat_entry` | defined `uk_syscall_r_<name>` / `uk_syscall_e_<name>` → `<name>` | convention validated on locally-built fixtures only (W-TOOLCHAIN) |
| `solo5` | `solo5_app_main` | referenced `solo5_<call>` → `solo5.<call>` | same |

An image with no marker, or with more than one, gets `UK_SEAL_UNKNOWN_TOOLCHAIN`. An image with no
symbol table gets `UK_SEAL_NO_EVIDENCE`. It is admitted only when `allow_attested_facts` is on and a
signature-verified provenance statement carries `attested_facts`.

## Canonical syscall vocabulary

Unikraft names are Linux syscall names, for example `read` and `clock_gettime`. Solo5 names are
hypercall names with a `solo5.` prefix. The raw symbol is kept next to each canonical name
(`syscall_evidence`) for forensics.
