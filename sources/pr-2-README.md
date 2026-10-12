# A sharper exponent for integer multiplication

**Community research maintained by Douglas Colkitt — conditional on the original
OpenAI #109 framework.**

The reviewed community witness gives

$$
T(n)=O\!\left(n(\log n)^{1-\kappa}\right),\qquad
\boxed{\kappa=\frac{971668963}{25000000000000}
=3.886675852\times10^{-5}>2^{-15}}.
$$

This uses the fixed finite-alphabet Turing-machine model with a fixed number of
one-dimensional tapes in OpenAI's
[*Integer multiplication below n log n*](https://github.com/openai/math/tree/adc7f1241b42e322a6451854ab7e4b4c146bf78a/preprints/Integer-multiplication-below-n-log-n-September-23-2026).
The saving is approximately **27.36% above 2^-15**. These numbers compare
asymptotic exponent savings, not practical running times.

**Final contribution: [Rohan Arun (@rohanarun), PR #39](https://github.com/CrocSwap/integer-mult-bounds/pull/39).**
Rohan supplies the fixed-middle-basis composition, simultaneous-basis proof,
complete profile certificates and final integration, with substantial OpenAI
Codex assistance. This result builds on a substantial community dependency
chain, credited below and in the original source notices.

**[Proof and reproduction guide](research/copied-fixed-reversed/README.md)** ·
[Exact certificate](research/copied-fixed-reversed/certificate.json) ·
[Completed maintainer audit](docs/research/community-final-audit.md) ·
[Release notes](docs/releases/community-kappa-15.md)

## What changed

The community work combines recursive batching and partial-swap frames with
semantic precision bounds, arbitrary-coordinate routing and bulk Gaussian
resampling. Two-stage circuits, paid copied-center operations and improved
contiguous blocks further strengthen the finite networks. The final PR fixes
one factor's basis and certifies its complete physical transition profile while
retaining a compatible generic basis for the other factor.

The selected bit network has m=575 and 188181929 roles. Its exact recursive
saving is 3886826921/10^14; the complex network supplies 717/10^7. The final
assembly retains all seven strict exponent margins, including numerical,
movement and normalization costs. See the [audit](docs/research/community-final-audit.md)
for the general arguments and their acceptance boundary.

## Attribution

This is a community result. Principal incorporated contributions include:

- **Rohan Arun (@rohanarun):** corner geometry, reversed/fixed-basis composition,
  exact checks and the final [#39](https://github.com/CrocSwap/integer-mult-bounds/pull/39) witness.
- **icekylinx:** recursive batching, partial swaps, fixed projector profiles,
  copied retained centers and the selected complex construction.
- **Zhihao Chen (@jacklightChen):** controlled bases, translated frames,
  semantic/bulk compatibility and two-stage integration.
- **RaD project (@hipotures):** semantic precision, arbitrary-coordinate
  routing, phase-cell inversion and bulk resampling.
- **James Chang (@jamesyc):** reversed two-stage geometry and exact controls.
- **Aurel Prosz (@Paureel) and Swapnil Jain:** attributed two-stage development
  and the paid copied-stream endpoint construction.
- **Dominik Scholz (@DominikScholz):** dimension, parameter and fixed-basis refinements.
- **eumemic:** complex circuits, Gaussian resampling and source-frame work;
  **Bortlesboat** and **dleen:** aligned pairing, retained totals and sharing.

The [full contribution record](CONTRIBUTORS.md) also credits parallel,
incremental, superseded and pending work, including princezuda's separate
Lean certificate submission. Inclusion there does not claim incorporation
or verification of every PR. Douglas Colkitt maintains the project and its
original research, review and integration, with OpenAI Codex assistance.
OpenAI's original manuscript and Harvey–van der Hoeven's analytic work retain
their attribution. Contributor-specific AI disclosures remain in [NOTICE](NOTICE).

## Evidence and limits

The pinned contribution is PR #39 at `70ae24129649f6d6d4ec6360962a80c3c42a38f1`.
It has passed the maintainer's conditional mathematical audit. The original
#109 framework remains assumed; this is not full formal verification,
independent human peer review, or a claim of worldwide priority or optimality.
No complete practical multiplication-machine implementation is supplied.

Validation includes 218 tests, 20 historical patch checks, fresh finite
producers and profile certificates, Ubuntu/GCC reproduction and a three-version
Linux Python matrix. A separate arithmetic checker confirms the two recursive
moments and all seven margins without importing the candidate's checkers.
The [audit](docs/research/community-final-audit.md) separates that executable
evidence from the general proof arguments.

The former **2^-30 checkpoint** remains preserved at `1a74950`, with its
[proof note](artifacts/ternary-note.pdf), [certificate](certificates/ternary-side.json)
and [review guide](docs/research/ternary-review.md). Earlier artifacts are
historical witnesses, not descriptions of this release's construction.
PR #40 and later work remain outside the pinned audit.

## Reproduce

Requires Python 3.11 or newer, Git, Make and a C++17 compiler with unsigned
128-bit integer support (tested with GCC and Clang). No third-party Python
packages or network access are needed for verification.

```sh
make verify
git diff --exit-code -- certificates patches
```

For the final witness and the independent arithmetic/source audit:

```sh
make copied-fixed-reversed-check
make copied-fixed-reversed-producer
make community-audit-check
```

Allow several minutes and multiple gigabytes of memory for full producer
rebuilds. See [reproduction details](docs/reproducibility.md).

## Historical witnesses and independent patches


Each patch applies independently to the **unmodified** pinned source; they are
alternatives, not a sequence to apply together. The
[result history](docs/research/result-history.md) records the earlier mechanisms
and scoped ceilings.

| Patch | Conditional saving | Scope |
| --- | --- | --- |
| [frozen-154](patches/frozen-154.patch) | `2^-154` | Original network and recurrence exponents |
| [balanced-153](patches/balanced-153.patch) | `2^-153` | Balanced assembly parameters |
| [same-network-129](patches/same-network-129.patch) | `2^-129` | Original network, sharper recurrence comparison |
| [h46-111](patches/h46-111.patch) | `2^-111` | Smaller network, dyadic parameters |
| [h46-109](patches/h46-109.patch) | `2^-109` | Rational recurrence saving, strict final margin |
| [h46-108](patches/h46-108.patch) | `2^-108` | Variable stopping exponent |
| [h46-rational](patches/h46-rational.patch) | `5.8e-33` | Strongest supplied parameter-only witness |
| [nonadjacent-layout](patches/nonadjacent-layout.patch) | Original parameters retained | Routing proof and revised layout cost only |
| [frozen-nonadjacent-107](patches/frozen-nonadjacent-107.patch) | `2^-107` | Direct routing, original network and recurrence exponents |
| [h46-nonadjacent-78](patches/h46-nonadjacent-78.patch) | `2^-78` | Direct routing with the h = 46 network |
| [h46-nonadjacent-76](patches/h46-nonadjacent-76.patch) | `2^-76` | Direct routing with tuned dimension and stopping parameters |
| [h46-shared-side-75](patches/h46-shared-side-75.patch) | `2^-75` | Stage-1/stage-3 side-role sharing, routing, and parameter tuning |
| [h46-incidence-67](patches/h46-incidence-67.patch) | `2^-67` | Rectangle incidence circuits, full auxiliary sharing, routing, and parameter tuning |
| [h46-dag-63](patches/h46-dag-63.patch) | `2^-63` | Shared intermediate sums and reversible role allocation |
| [h46-shared-point](patches/h46-shared-point.patch) | `13*2^-66` | Cross-group sharing |
| [h50-paired-59](patches/h50-paired-59.patch) | `2^-59` | Paired sums, stopped guard and tighter Gaussian setup |
| **[compact-control-34](patches/compact-control-34.patch)** | **`83/10^12 > 2^-34`** | **Compact controls, complete reservations, local repair and separate complex arity** |
| [complex-compression-31](patches/complex-compression-31.patch) | `2^-31` | Weighted complex circuits, binary phase frames and complete auxiliary sharing |
| **[ternary-30](patches/ternary-30.patch)** | **`2^-30`** | **Ternary five-subset circuit, rational frames and fixed-alphabet interchange** |

## Preserved aligned paired refinement

The [aligned paired construction](docs/research/aligned-paired-network.md)
refines the earlier `2^-59` paired witness. At `h=50`, it removes 14,944 binary
additions, reducing side roles from 509,194 to 494,250 with the same absolute
rank deficit. Its independent conditional target is `17*2^-63`, using the
earlier retained parameter recipe. It does not replace the newer checkpoint
above, and its counts and analytic interfaces must not be combined with the
newer constructions without a separate argument.

The [exact certificate](certificates/aligned-paired-network.json),
[independent manuscript patch](patches/h50-aligned-paired.patch),
[proof note](artifacts/aligned-paired-note.pdf) and
[focused review packet](docs/research/aligned-paired-review.md)
([PDF](artifacts/aligned-paired-review.pdf)) remain available. Independent
review of its frame/rank transfer, dirty-scratch restoration, fixed-tape
recurrence and retained downstream interfaces remains pending.

## Citation and license

Use [CITATION.cff](CITATION.cff), cite the individual contributions used and
include the repository version or commit. [CONTRIBUTORS.md](CONTRIBUTORS.md),
[NOTICE](NOTICE) and source-specific manifests preserve the dependency credits.

The project is [Apache-2.0](LICENSE). Bundled RaD sources retain their separate
CC0 license and notices. The pinned original OpenAI manuscript remains unchanged
under `upstream/`; its source hashes are in [upstream/manifest.json](upstream/manifest.json).
This project is not an official OpenAI release or endorsement.
