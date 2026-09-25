# Sort policy 1.0.1 -- needs and complexity -> node

Deterministic, explainable, re-derivable. Measured features (from bytes alone): kind (extension + name + dialect
magic), bytes, lines, branches, imports, definitions, io_refs, trust-name, hosted/native/bulk flags, complexity
`lines/10 + 2*branches + 3*imports + 1*definitions` banded LOW < 8, MID < 40, HIGH < 200, VERY_HIGH >= 200.
First matching rule wins. Every decision is written to the berth's SORT_LEDGER with the rule id and a sentence.

| rule | placement |
|---|---|
| `S0` | a script written in a node's own guest dialect goes to that node: MSSL assembly -> N_SMALL, LCTLC/1.1 -> N_MEDIUM, LCTLC/1.2 -> N_LARGE, LCTLC/1.0 (QVM profile) -> N_XLARGE |
| `S1` | a PA-LCTL bundle (.pal) goes to N_MEDIUM, the reference node the corpora's own adapter binds |
| `S2` | bulk cargo -- archives, images, binaries, media, PDFs, or anything >= 1 MiB -- goes to N_XLARGE, the roomiest, hosted node |
| `S3` | hosted-runtime source (Python, Java, JavaScript/TypeScript, HTML/CSS/SVG, notebooks) and Columned LCTL plans (.lctl, verified by the JVM column verifier) go to N_XLARGE, the Python-hosted node with the JVM verifier |
| `S4` | native/system source (C, C++, headers, assembly, Makefiles, linker scripts) goes to N_LARGE, the freestanding C core with the device I/O and service architecture |
| `S5` | integrity and contract artifacts (sums, signatures, keys, manifests, schemas, provenance, ledgers, trust stores) go to N_MEDIUM, the node with signing, the trust chain and the independent verifier |
| `S6` | structured data and configuration go by size: <= 4 KiB -> N_SMALL, <= 256 KiB -> N_MEDIUM, larger -> N_LARGE |
| `S7` | launchers and shell/batch scripts go by complexity band: LOW -> N_SMALL, MID -> N_MEDIUM, HIGH -> N_LARGE, VERY_HIGH -> N_XLARGE |
| `S8` | documents and notes go by size: <= 8 KiB -> N_SMALL (teaching), <= 128 KiB -> N_MEDIUM, larger -> N_LARGE |
| `S9` | everything else goes by complexity band: LOW -> N_SMALL, MID -> N_MEDIUM, HIGH -> N_LARGE, VERY_HIGH -> N_XLARGE |

Nodes: N_SMALL, N_MEDIUM, N_LARGE, N_XLARGE. `uc sort <file>` explains a placement; gate B2 re-derives every ledger from
its cargo bytes; gate U1 checks the shipped policy equals the code and that the documented examples still hold.

History: 1.0.0: initial policy (UC-1.0.0). 1.0.1: measurement fix: the binary sniff tolerates a UTF-8 multibyte character cut at the 4096-byte sniff boundary; 1.0.0 misread a columned-LCTL unit longer than the sniff (its U+2502 separators) as binary and sent it to N_XLARGE as bulk instead of its own node.
