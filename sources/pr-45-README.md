# A sharper exponent for integer multiplication

**Research draft by Douglas Colkitt — conditional on the upstream manuscript
and the written extensions supplied here.**

This checkpoint supplies

$$
T(n)=O\!\left(n(\log n)^{1-\kappa}\right),\qquad
\boxed{\kappa=2^{-30}\approx9.31323\times10^{-10}}
$$

in the fixed finite-alphabet Turing-machine model with a fixed number of
one-dimensional tapes used by OpenAI's
[*Integer multiplication below n log n*](https://github.com/openai/math/tree/adc7f1241b42e322a6451854ab7e4b4c146bf78a/preprints/Integer-multiplication-below-n-log-n-September-23-2026)
(result family #109). It doubles the exponent saving of this repository's
preceding local `2^-31` checkpoint. The original manuscript uses `2^-182`;
this is a `2^152` ratio of exponent savings, not a runtime speedup.

**[Proof note (PDF)](artifacts/ternary-note.pdf)** ·
[Independent manuscript patch](patches/ternary-30.patch) ·
[Exact construction certificate](certificates/ternary-side.json) ·
[Review guide](docs/research/ternary-review.md)

**Related contributions:** Zhihao Chen's earlier
[PR #7](https://github.com/CrocSwap/integer-mult-bounds/pull/7) introduces the
same ternary five-subset motif with a different circuit and stronger claimed
bound. This release records a separate implementation and conditional
checkpoint; it makes no priority or strongest-known-bound claim. Additional
stronger contributions are pending review. See the
[community contribution record](CONTRIBUTORS.md) and
[contribution-review index](docs/research/contribution-review.md).

## What changed

The bit interchange circuit now computes over **F3**, while its address
frames remain rational matrices. The fixed-alphabet extension preserves the
interchange recurrence: recursive calls move whole symbols, and completed
calls return the original bit data.

Five-subsets of 29 points label the circuit. Pair incidence over F3 supplies
the central map; shared common-pair sums supply its correction. Exact support
identification merges equal sums across groups. Their rational source spans
are nondegenerate, and a signed transparent schedule restores every arbitrary
auxiliary input. A final sign correction and first/third-stage sharing satisfy
the complete permutation and endpoint contract.

The bit saving is `a_b=467/10^11`. The retained complex network has
`a_c=5/10^9`; its precision guard and the compact-control movement proofs
remain unchanged. All final margins are strict, with minimum

$$
G_* = \frac{2332833}{2500000000000000} > 2^{-30}.
$$

The full construction is regenerated as an integer DAG; small complete
instances check every coefficient, arbitrary-input restoration, and rational
frame transition. The general proofs, rather than extrapolation from those
small tests, establish the larger construction. The full upstream theorem
remains assumed, and the new arguments have not received independent
mathematical review or full formal verification.

## Evidence and scope

| Component | Evidence |
| --- | --- |
| Finite-alphabet interchange | Written extension of the upstream recurrence |
| Ternary coefficient identity and side sharing | General proof, full DAG counts and exact support keys |
| Dirty auxiliary restoration and rational frames | General proof and complete small-instance checks |
| Parameters, logarithms and final margins | Exact rational certificate |
| Retained complex, movement and precision machinery | Earlier proofs and certificates, unchanged |
| Source integration | Independent patch, reference checks and manuscript build |
| Full upstream multiplication theorem | Assumed |
| Independent review / full formalization | Not supplied |

The [review guide](docs/research/ternary-review.md) maps each new obligation to
its evidence. [Current status](docs/research/current-status.md) supersedes
historical numerical claims in older notes. Earlier witnesses remain unchanged.

## Reproduce

With Python 3.11 or newer, Git and Make:

```sh
make verify
git diff --exit-code -- certificates patches
```

The checks use the Python standard library and require no network access.
The new full-size audit constructs about 21 million addition nodes; allow
several minutes and multiple gigabytes of memory. The second command checks
exact regeneration on a clean checkout. A focused verification is:

```sh
python3 scripts/audit_ternary_side.py
python3 scripts/make_ternary_patch.py
python3 -m unittest tests.test_prime_core tests.test_ternary_side tests.test_ternary_patch -v
git apply --check --directory=upstream patches/ternary-30.patch
```

Build the note with `make ternary-note` using Tectonic. See the
[reproduction instructions](docs/reproducibility.md) for a disposable
manuscript preview. Passing these checks does not prove the full upstream
multiplication theorem; no full multiplication-machine implementation is supplied.

## Witnesses and independent patches

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

## Attribution, citation, and license

Author: **Douglas Colkitt**. Research, implementation and drafting were performed
with assistance from OpenAI Codex. The compact-control proposal originated
with a separate research agent; the supplied note develops its tape, layout,
repair and assembly arguments. AI assistance is not independent review or
endorsement by OpenAI. No priority or unrestricted optimality claim is made. The earlier ternary
submission by Zhihao Chen (jacklightChen) in PR #7 and related complex
compression work by eumemic in PR #3 are acknowledged in the note and NOTICE.
Their pending implementations are not imported or verified by this checkpoint.
The [community contribution record](CONTRIBUTORS.md) also acknowledges parallel,
incremental and superseded submissions across this interval and subsequent work.

The original manuscript is by OpenAI, pinned at commit
`adc7f1241b42e322a6451854ab7e4b4c146bf78a`. Source URLs and SHA-256 hashes are in
[upstream/manifest.json](upstream/manifest.json). Files under `upstream/` remain
unchanged; modifications are supplied as separate patches.

Use [CITATION.cff](CITATION.cff) and also cite the
[upstream manuscript](upstream/README.md). Until a release is archived, include
the repository commit used. Licensed under [Apache-2.0](LICENSE); see
[NOTICE](NOTICE) and [CONTRIBUTING.md](CONTRIBUTING.md).
