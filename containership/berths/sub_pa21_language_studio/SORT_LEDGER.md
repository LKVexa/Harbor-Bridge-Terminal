# sub_pa21_language_studio -- sort ledger

Berth `sub_pa21_language_studio` (subsystem), UC-2.1.3. Source: `PA21_Language_Studio` (directory, 582f7bf9cd18bdf986a7f68deaa0ede45cabd3e73ba812fd847316453d7b533b). 23 scripts sorted by policy 1.0.1 (rules S0-S9, first match wins; see `reports/SORT_POLICY.md`).

| node | scripts | bytes | rules | kinds |
|---|---:|---:|---|---|
| `N_SMALL` (DF_Small) | 4 | 1070 | S7:4 | batch:2, shell:2 |
| `N_MEDIUM` (DF_Medium) | 1 | 31213 | S8:1 | markdown:1 |
| `N_LARGE` (DF_Large) | 1 | 21466 | S4:1 | c:1 |
| `N_XLARGE` (DF_Xtra_Large) | 17 | 425206 | S3:17 | python:16, html:1 |

| script | node | rule | kind | bytes | lines | band | why |
|---|---|---|---|---:|---:|---|---|
| `INSTALL.cmd` | `N_SMALL` | S7 | batch | 440 | 10 | LOW | batch launcher, complexity LOW (score 7.0) |
| `INSTALL.sh` | `N_SMALL` | S7 | shell | 219 | 5 | LOW | shell launcher, complexity LOW (score 2.5) |
| `README.md` | `N_MEDIUM` | S8 | markdown | 31213 | 731 | HIGH | markdown of 31213 bytes (<= 128 KiB) |
| `examples/embed_studio.py` | `N_XLARGE` | S3 | python | 3648 | 95 | HIGH | python needs a hosted runtime; the QUORUM node is Python-hosted with a JVM verifier |
| `pa21studio/__init__.py` | `N_XLARGE` | S3 | python | 1289 | 30 | MID | python needs a hosted runtime; the QUORUM node is Python-hosted with a JVM verifier |
| `pa21studio/abi.py` | `N_XLARGE` | S3 | python | 15197 | 310 | HIGH | python needs a hosted runtime; the QUORUM node is Python-hosted with a JVM verifier |
| `pa21studio/cli.py` | `N_XLARGE` | S3 | python | 48122 | 1106 | VERY_HIGH | python needs a hosted runtime; the QUORUM node is Python-hosted with a JVM verifier |
| `pa21studio/container.py` | `N_XLARGE` | S3 | python | 21361 | 507 | VERY_HIGH | python needs a hosted runtime; the QUORUM node is Python-hosted with a JVM verifier |
| `pa21studio/core.py` | `N_XLARGE` | S3 | python | 116040 | 2313 | VERY_HIGH | python needs a hosted runtime; the QUORUM node is Python-hosted with a JVM verifier |
| `pa21studio/describe.py` | `N_XLARGE` | S3 | python | 35994 | 713 | VERY_HIGH | python needs a hosted runtime; the QUORUM node is Python-hosted with a JVM verifier |
| `pa21studio/fabric_tif.py` | `N_XLARGE` | S3 | python | 13437 | 333 | HIGH | python needs a hosted runtime; the QUORUM node is Python-hosted with a JVM verifier |
| `pa21studio/fault.py` | `N_XLARGE` | S3 | python | 5202 | 143 | HIGH | python needs a hosted runtime; the QUORUM node is Python-hosted with a JVM verifier |
| `pa21studio/hosts/brrun.c` | `N_LARGE` | S4 | c | 21466 | 523 | VERY_HIGH | c belongs with the freestanding C core and its build system |
| `pa21studio/lctlc.py` | `N_XLARGE` | S3 | python | 11953 | 258 | HIGH | python needs a hosted runtime; the QUORUM node is Python-hosted with a JVM verifier |
| `pa21studio/ledger.py` | `N_XLARGE` | S3 | python | 8902 | 235 | HIGH | python needs a hosted runtime; the QUORUM node is Python-hosted with a JVM verifier |
| `pa21studio/probe.py` | `N_XLARGE` | S3 | python | 7983 | 208 | HIGH | python needs a hosted runtime; the QUORUM node is Python-hosted with a JVM verifier |
| `pa21studio/repair.py` | `N_XLARGE` | S3 | python | 24403 | 603 | VERY_HIGH | python needs a hosted runtime; the QUORUM node is Python-hosted with a JVM verifier |
| `pa21studio/ui/index.html` | `N_XLARGE` | S3 | html | 44040 | 1023 | VERY_HIGH | html needs a hosted runtime; the QUORUM node is Python-hosted with a JVM verifier |
| `pa21studio/ui_server.py` | `N_XLARGE` | S3 | python | 15310 | 364 | VERY_HIGH | python needs a hosted runtime; the QUORUM node is Python-hosted with a JVM verifier |
| `studio.cmd` | `N_SMALL` | S7 | batch | 329 | 8 | LOW | batch launcher, complexity LOW (score 4.8) |
| `studio.py` | `N_XLARGE` | S3 | python | 228 | 6 | LOW | python needs a hosted runtime; the QUORUM node is Python-hosted with a JVM verifier |
| `studio.sh` | `N_SMALL` | S7 | shell | 82 | 3 | LOW | shell launcher, complexity LOW (score 0.3) |
| `verify_studio.py` | `N_XLARGE` | S3 | python | 52097 | 955 | VERY_HIGH | python needs a hosted runtime; the QUORUM node is Python-hosted with a JVM verifier |
