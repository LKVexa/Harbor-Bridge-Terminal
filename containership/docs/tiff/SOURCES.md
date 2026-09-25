# Technical sources and dependency observations

References consulted September 22, 2026. Source text is not bundled or asserted to certify this implementation.

1. LibTIFF, **BigTIFF Design**: https://libtiff.gitlab.io/libtiff/specification/bigtiff.html . Used for magic 42/43, BigTIFF header fields, 64-bit offsets/counts, entry widths and alignment distinctions. Large-file *format parsing* is distinct from this candidate's deliberate 8 MiB file budget.
2. Pillow 12.3.0, **Image file formats**: https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html . Used for TIFF/GIF frame, palette, lossless codec and save behavior. This candidate additionally verifies exact output bytes; library feature availability alone is not correctness evidence.
3. CompuServe, **GIF89a Specification**, hosted by W3C: https://www.w3.org/Graphics/GIF/spec-gif89a.txt . Used for image descriptors, global palettes, sub-block framing, graphic control and comment extensions. UC/FABRIC_GIF/1 narrows the general GIF format; it is not a new general GIF standard.
4. Original uploaded TIFF nine-phase v1.6.0 series: retained in `tifflow/series.zip`; SHA-256 is pinned in `tifflow/APPLICATION.json`. It is the source of the 325-component/325,000-task contract, not evidence that its proposed scientific/cloud features are implemented.
5. Original uploaded UC-2.4.0 candidate and its carried native engine code: source of PA21FAB1/BRO1 state semantics. Input archive SHA-256 values and changed-file inventories accompany this release.

## Observed execution environment

Tests were executed on Linux with CPython 3.13.5, Pillow 12.3.0 and Node.js 22.16.0. The independent test encoder used tifffile 2026.5.15 and NumPy 2.3.5. Those two libraries are **optional test-only dependencies** and not imported by the production codec. The pinned independent test versions require Python 3.12+ together; the ship/runtime requirement remains Python 3.10+ with Pillow. Missing independent-test dependencies produce an explicit skip, never an interoperability PASS.

The installed Pillow TIFF parser source detects BigTIFF with a one-byte header test. The independent big-endian BigTIFF fixtures exposed that limitation locally. The candidate's new minimal raster adapter resolves it without monkey-patching or modifying the installed Pillow package. This observation describes the tested installation, not a claim about all past/future Pillow versions.

No vulnerability-database/CVE certification, package installation, external deployment, credential use or public service publication was performed as part of this patch.
