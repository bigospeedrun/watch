# Integer multiplication with conditional saving 1.2523415e-5

$$
T(n)=O\!\left(n(\log n)^{1-\kappa}\right),\qquad
\kappa=\frac{2504683}{200000000000}=1.2523415\times10^{-5}.
$$

The selected bit network uses dimensions `(32,30,36)`, refined contiguous
boundary blocks, and a fixed middle-axis basis `I+J` with exact bounded-minor
CRT certificates. The complex network uses `(30,30,40)`, mixed dyadic centers
and complete physical-data batching.

The assembly adapts **Zhihao Chen (jacklightChen)**'s PR #23 composition of
**RaD (hipotures)**'s semantic precision, coordinate routing, phase-cell
inverse and bulk resampling. It uses linear precision exponent `C1=1` and
pays the product of the nested row reserves.

The result remains conditional on the retained multiplication framework,
the attributed analytic and tape interfaces, and their eventual thresholds.
Finite arithmetic checks support these written proofs; they are not a formal
verification or an implementation of the complete multiplication machine.

## Proof and reproduction

- [Current proof source](notes/structured-bulk-note.tex).
- [Exact certificate](certificates/structured-bulk-network.json): recursive
  moments, semantic precision, product row stock and 47 strict constraints.
- [Producer and CRT reconstruction](scripts/structured_bulk_producer.py).
- [Adopted proof sources](references/semantic-bulk/README.md),
  [reproduction instructions](docs/reproducibility.md) and [provenance](SOURCES.json).

```sh
make structured-bulk-verify
```

The incremental target verifies new constructions and reuses unchanged
previously verified inputs. `make verify` also runs all inherited checks.
Large intermediate DAGs are regenerated in temporary storage.

The strict component savings are `1252373/100000000000` (bit) and
`131/5000000` (complex). The final absorption gap exceeds `9.4453e-13`.

The immediate parent is [PR #24](https://github.com/CrocSwap/integer-mult-bounds/pull/24),
with its [endpoint-gauge proof](artifacts/endpoint-gauge-note.pdf),
commit `ed90fd940279c336ebc45968631bdebfb087b505`, retaining PR #10 and
partial-swap ancestry. The [combined manuscript patch](patches/batched-23.patch)
remains the #10 baseline; the current extension is in its standalone proof.

## Attribution

The new selected construction and integration are contributed by **icekylinx**,
with substantial OpenAI GPT-6 Astra and Codex assistance. Adopted PR #21 and
#23 contributions are credited to **Zhihao Chen (jacklightChen)**; the
semantic and analytic machinery is credited to **RaD (hipotures)**.

The retained framework and finite constructions build on **Douglas Colkitt**,
**Zhihao Chen**, **eumemic**, **Bortlesboat**, **dleen**, and the other
contributors recorded in [NOTICE](NOTICE). OpenAI's manuscript remains pinned
at `adc7f1241b42e322a6451854ab7e4b4c146bf78a`.

The repository retains Apache-2.0. Imported RaD proof sources retain their
separate CC0 terms and notices in [references/semantic-bulk/rad20](references/semantic-bulk/rad20).
