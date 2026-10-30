# Holistic Compression Sources (HCS)

Canonical source vault for the CHCE engine and all CHIMERA-family projects
(heavenzip, ziptastic, compfactory). Every third-party compressor,
preprocessor, and recompressor used by CHCE lives in [`/old`](./old).

## Why this repo exists

CHCE composes many specialized codecs and preprocessors. Rather than chase
upstream repos in every consumer project, HCS pins every source here at a
known-good revision. Consumers (heavenzip, ziptastic) pull this repo with
`git subtree` and build from the pinned `old/` tree.

## Integration Rule

| Layer | Consumes HCS how |
|---|---|
| `ziptastic` (native engine) | `git subtree` of `/old` → `vendor/` |
| `heavenzip` (orchestrator) | Prebuilt binaries from `ziptastic` releases, not `/old` |
| `compfactory` (workshop) | Full checkout; edits propagate via PR to HCS |

## Source Catalog

### Entropy / Final-Stage Coders
| Source | Role | License | Pin |
|---|---|---|---|
| `xz` | LZMA2 reference implementation | 0BSD / LGPL-2.1 | TBD |
| `7zip` | PPMd source + LZMA SDK | Public Domain | TBD |
| `brotli` | Static dictionary + context-modeled coder | MIT | TBD |

### LZ / Match-Finder Backends
| Source | Role | License | Pin |
|---|---|---|---|
| `srep` | Long-range block-hash matcher | Public Domain | TBD |
| `zstd` | Speed/ratio spectrum backend | BSD-3 / GPLv2 | TBD |
| `lz4` | Max-speed backend | BSD-2 | TBD |
| `freearc-c` | LZMA, PPMd, Tornado, GRZip bundle | varies | TBD |

### BWT Backends
| Source | Role | License | Pin |
|---|---|---|---|
| `libbsc` | BWT + LCP + ANS | Apache-2.0 | TBD |

### Context-Mixing Backends
| Source | Role | License | Pin |
|---|---|---|---|
| `zpaq` (`libzpaq`) | CM backend, Tier-3 ratio | Public Domain | TBD |

### Preprocessors
| Source | Role | License | Pin |
|---|---|---|---|
| `parmar` | Subword tokenization for text | check | TBD |
| `bitshuffle` | Numeric bit-transpose | BSD-3 | TBD |

### Recompressors
| Source | Role | License | Pin |
|---|---|---|---|
| `preflate` | DEFLATE recompressor (C++) | Apache-2.0 | TBD |
| `preflate-rs` | DEFLATE recompressor (Rust) | Apache-2.0 | TBD |
| `precomp` | Legacy recompressor (reference) | Apache-2.0 | TBD |
| `packjpg` | JPEG recompressor ⚠ LGPL-3 | LGPL-3 | TBD |
| `zopfli` | Iterative Deflate optimizer | Apache-2.0 | TBD |
| `advancecomp` | Archive recompressor | GPL-3 | TBD |
| `zlib-ng` | Fast Deflate (encoder path) | zlib | TBD |
| `libdeflate` | Fast Deflate (encoder path) | MIT | TBD |

### Reference Only (Not Linked)
| Source | Why kept | License |
|---|---|---|
| `freearc-next` | Historic context, Lua pipeline design | mixed |

## License Warning

**`packjpg` is LGPL-3.** If CHCE is closed-source, treat it as an
external process, not a linked library. See `LICENSES/` for full texts.

## Bumping a Source

1. `cd old/<source>` and check out the new revision.
2. Update the pin in `SOURCES.md`.
3. Regenerate `LICENSES/` if license text changed.
4. Open a PR. CI (when added) will build CHCE against the new pin.
