# Integer multiplication with conditional saving 5.98615e-6

\[
T(n)=O\!\left(n(\log n)^{1-\kappa}\right),\qquad
\kappa=\frac{119723}{20000000000}=5.98615\times10^{-6}.
\]

Complementary auxiliary endpoint gauges combine the middle-stage entrance
and exit without increasing their total rank. A compatible rational basis
and positive binary producer frames give the selected dimensions `(32,30,40)`.
A general binary quadratic-phase normal form permits whole-residual complex
calls, including alternating residuals, with the same dimensions.

The result remains conditional on the pinned upstream analytic and tape
interfaces. Exact finite calculations support the written construction;
they do not constitute formal verification of the complete theorem.

## Proof and reproduction

- [Current proof](artifacts/endpoint-gauge-note.pdf) and [LaTeX source](notes/endpoint-gauge-note.tex).
- [Exact certificate](certificates/endpoint-gauge-network.json): both moments,
  the precision guard, 29 strict constraints, and seven assembly margins.
- [Producer reconstruction](scripts/endpoint_gauge_producer.py) and
  [finite input data](certificates/endpoint-gauge-input.json).
- [Reproduction instructions](docs/reproducibility.md) and [source provenance](SOURCES.json).

```sh
make endpoint-gauge-verify
make endpoint-gauge-note
```

Verification requires Python 3.11+, a C++17 compiler, Git, and Make. The new
producer graphs, carrier matches and frames are rebuilt in temporary storage.
No large binary graph dumps are committed. `make verify` additionally runs all
inherited checks; `make endpoint-gauge-certificate` runs only the new arithmetic.

The component savings are `2993093/250000000000` (bit) and `3/125000`
(complex). The final strict absorption margin exceeds `1.6569e-13`.
The corrected Gaussian input enclosure from #10 is retained with `P=34p`.

This extension inherits the [partial-swap proof](artifacts/partial-swap-note.pdf)
at commit `f2ab41aebad47861caf6316282c1793e5513845e`, which extends
[PR #10](https://github.com/CrocSwap/integer-mult-bounds/pull/10).
The [#10 proof](artifacts/batched-23-note.pdf) and
[combined manuscript patch](patches/batched-23.patch) remain historical
baselines. The current standalone proof supplies the stronger construction;
the older patch does not contain these extensions.

## Attribution

The endpoint-gauge construction and integration are contributed by **icekylinx**,
with substantial OpenAI GPT-6 Astra and Codex assistance. This work builds on
**Douglas Colkitt**'s framework, **Zhihao Chen (jacklightChen)**'s finite network
and paired producers, and contributions by **Bortlesboat**, **eumemic**, and
**dleen**. Original notices are retained in [NOTICE](NOTICE).

OpenAI's manuscript is pinned at `adc7f1241b42e322a6451854ab7e4b4c146bf78a`.
The repository uses Apache-2.0; see [LICENSE](LICENSE) and
[upstream/LICENSE](upstream/LICENSE).
