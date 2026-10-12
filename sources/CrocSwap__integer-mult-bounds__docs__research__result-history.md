# Earlier results and research chronology

See also the [preserved intermediate research chronology](pre-community-research-history.md)
and [research index](preserved-research.md). The selected bound is recorded in
[current status](current-status.md).

This page preserves the earlier README narrative through the published `2^-59`
result and intervening research attempts. Statements such as “latest” below
refer to their historical stage. The [current status](current-status.md) and
[repository overview](../../README.md) supersede numerical targets and open
obligations that the compact-control construction has since addressed.

## Community release through PR #39

The reviewed community composition gives conditional
`kappa=971668963/25000000000000 > 2^-15`. Rohan Arun supplies the final
fixed-middle-basis contribution, building on the community work credited in
[the release notes](../releases/community-kappa-15.md). The
[maintainer audit](community-final-audit.md) records acceptance and limits.
The earlier checkpoints below remain preserved.

## Ternary checkpoint

The [ternary construction](ternary-review.md) supplies conditional kappa=2^-30
with a separate F3 five-subset implementation. The earlier related motif in
Zhihao Chen's PR #7 is acknowledged; that PR and later stronger submissions
remain in the [review queue](contribution-review.md). This is an independently
reproducible checkpoint, not a priority or frontier claim.

## Subsequent integrated checkpoints

The compact-control construction removed the layer's spacing penalty and
supported `83/10^12 > 2^-34`; its [note](../../artifacts/compact-control-note.pdf)
and [patch](../../patches/compact-control-34.patch) are preserved unchanged.

The next [complex-network construction](complex-compression.md) compresses
weighted side computations with compatible binary phase frames and shares
complete auxiliary banks. At `h=26`, its certified complex saving `5e-9`
exceeds the retained bit saving `2.96e-9`. The independent combined patch
supports `kappa=2^-31`; the bit interface now binds. See the
[integration review](complex-compression-review.md) for the current obligations.

## Paired sums and tighter downstream estimates: 2^-59

For subsequent work toward the 30s, see the
[preparation pass](../../docs/research/layer-preparation.md). It supplies reusable
recurrence estimates and complex-network headroom; its sparse-primitive
targets were subsequently discharged by the local compact-control proof linked
above. The published bound below is still `2^-59`. The following paragraphs
record the intervening research sequence.
The latest [short-guard reduction](../../docs/research/short-guard-audit.md) isolates
fast gathering as a concrete route to a smaller spacing penalty; the required
gathering algorithm remains unproved.
The [gather-schedule audit](../../docs/research/gather-schedule-audit.md) rules out
serial interval rearrangements as a sufficient shortcut and narrows the next
search to coded or direct strided operations.
The [bounded coded-carry attempt](../../docs/research/coded-carry-audit.md) found an
exact operation but no sublinear recurrence; its assessment recommends
returning the main research effort to stronger finite networks.
The first [cancellation-circuit audit](../../docs/research/cancellation-audit.md)
finds fewer scalar roles but fatal rank penalties from disjoint nonorthogonal paths;
shared corrections or changed stage frames remain unconstructed alternatives.
The [joint rational-frame audit](../../docs/research/joint-frame-audit.md) proves
local rank optimality with fixed invocation boundaries and grouped central
gates, even when copy, injection and side frames vary jointly. Further frame
optimization must change one of those structural constraints.

Three changes combine to reach `2^-59`:

1. A paired-block circuit keeps internal edge sums as vertex weights through
   the recursion. At `h=50`, cross-group sharing gives **509,194 side roles**,
   down from 694,495 for the preceding circuit at the same ground size.
2. Using the actual early stopping depth proves a **quadratic guard width**,
   replacing the conservative twentieth power.
3. The smaller Gaussian width `alpha=ceil((32*d*b)^(1/4))` meets the retained
   resampling interface and permits a larger transform dimension.

The exact minimum margin is

$$
G=\frac{272158569}{156250000000000000000000000}>2^{-59}.
$$

The [construction and dependency audit](../../docs/research/paired-network.md)
explains all three changes and the [certificate](../../certificates/paired-network.json)
checks their arithmetic, circuit coefficients, and both frame directions.
The strict margin is about 0.4%. Both motifs now use `h=50`; the complex motif
retains its original construction. The upstream theorem remains an assumption.

## Preserved cross-group sharing refinement

Equal sums can now be shared across different common-point groups. The reverse
computation uses orthogonal complements of the forward source spans, so it no
longer needs a separate positive-definiteness proof for reachable-target spans.
Every retained source span still has a common point and is positive definite.

This removes 45,706 additions and reduces side roles from **577,576 to 531,870**.
The rank deficit is unchanged. Exact checks support `a_b=203/10^11` and
`G=17661/10^23 > 13*2^-66`, with the complex saving unchanged. See the
[construction and next-search budget](../../docs/research/cross-point-sharing.md)
and [certificate](../../certificates/shared-point-network.json). With its then-retained guard and assembly bounds, that circuit fell short of
`2^-62`. The latest witness also changes those downstream bounds.

## Preserved shared-computation improvement

A cancellation-free computation graph shares intermediate sums across
outputs. Its reversible embedding uses **one role per output plus one per
binary addition**. Source supports provide nested forward frames; reachable
target supports provide nested frames for the reversed second stage.
All these spans are nondegenerate because each local circuit's triples share
a common point. Thus the new computation introduces no extra backward rank.

At `h=46`, side roles per invocation fall from **2,394,438 to 577,576**,
preserving the absolute rank deficit. The certified bit saving is
`a_b=187/10^11`; the complex saving remains `a_c=9/500000000000`. The
existing parameter recipe yields

$$
G=\frac{3a_{\rm b}^2}{70}\approx1.4987\times10^{-19}>2^{-63}.
$$

The [construction audit](../../docs/research/shared-computation.md) proves the
reversible embedding and both frame assignments. The
[exact certificate](../../certificates/dag-network.json) checks every output
coefficient at the target size, all compiled support inclusions, and the
downstream inequalities. The compiler is reusable for other compatible
cancellation-free circuits; the latest witness builds on this transfer.

## Preserved rectangle-circuit improvement

Neighboring triple pairs are partitioned into rectangles. A rectangle with
`a` sources and `b` targets uses an invertible mixer on `a+b-1` scratch roles,
instead of one role per pair. A common nondegenerate frame lets the mixer
share intermediate computations without adding backward rank. All auxiliary
roles, including centers, can then be shared between the first and third stages.

At `h=46`, this reduces side roles per invocation from **41,122,620 to
2,394,438** while preserving the absolute rank deficit. The certified bit
saving is `a_b=46/10^11`; the complex saving remains `a_c=9/500000000000`.
The existing parameter recipe gives

$$
G=\frac{3a_{\rm b}^2}{70}\approx9.0686\times10^{-21}>2^{-67}.
$$

The [construction and frame audit](../../docs/research/incidence-network.md) cover
dirty-scratch restoration, the reversed second stage, and every new frame
transition. The [exact certificate](../../certificates/incidence-network.json)
includes an exhaustive check of all 893,970 ordered disjoint pair instances
underlying the rectangle partition. This changes the scalar circuit and its
frames, so the bounds on pooling unchanged trajectories do not apply.

## Preserved stage-sharing improvement

An explicit matching lets the first and third stages share their side scratch
roles. Each invocation restores arbitrary initial scratch values. The matching
also makes the connecting frame labels nested, so sharing introduces no extra
rank loss. This removes one third of the side roles while preserving the
absolute rank deficit. The complex network is unchanged.

That witness uses bit saving `a_b = 27/10^12`, while the retained complex saving is
`a_c = 9/500000000000`. Set `tau = 1-a_b`, `sigma = 1-a_c`, and use the tuning
recipe below with `a = a_b`. The exact minimum margin is

$$
G=\frac{3a_{\rm b}^2}{70}\approx3.1243\times10^{-23}>2^{-75}.
$$

The [proof](../../notes/stage-reuse-note.tex) accounts for scalar restoration, the new
edge ranks, every role's endpoint identity, and the separate primitive
exponents. The [certificate](../../certificates/stage-reuse.json) checks counts and
all downstream parameter inequalities. Finite tests check the full h=46
matching, small rational projectors, and a complete h=6 shared-scratch circuit.
The earlier fixed-network ceiling does not apply to these changed role counts.

## Preserved parameter improvement

The new witness combines direct routing with the previously audited variable
stopping threshold. With `a = 9/500000000000`, set

$$
\epsilon=\frac1{21},\quad \beta=\frac9{10},\quad c=\frac{9a}{10},\quad
\lambda=1-\frac{19a^2}{20},\quad \lambda'=1-\frac{9a^2}{10}.
$$

The network and routing schedule stay the same; the dimension and recursion
stopping parameters change. Exact checks give `G = 3a^2/70 > 2^-76`.
The guard remains sublinear: `epsilon C1 = 20/21 < 1`.
The [tuning note](../../artifacts/routing-tuned-note.pdf) audits composition, precision,
and setup, and gives a transferable recipe for `0 < a < 1/16` with compatible
primitive interfaces and `C1 = 20`.

A simple necessary bound under those fixed primitive exponents and layer
constraints is `kappa < a^2/(20(1-a)) < 2^-75`. This is not an exact optimum
or a ceiling for stronger primitives or improved cost accounting.

## Further search and its boundaries

The [research log](../../docs/research/network-search-log.md) records the bounded
investigation that found stage sharing. The [scoped bounds](../../docs/research/network-screens.md)
exclude improvement from thinning the original triple family or using unequal
factor sizes, and limit one shared binary aggregation hierarchy. These are
family-specific results. The [next-step roadmap](../../docs/research/next-steps.md)
distinguishes concrete search targets from speculative stronger primitives.
The [block-label feasibility audit](../../docs/research/block-label-feasibility.md)
rules out several simple models for the proposed 2^-59 target; it does not
establish a new construction or a stronger multiplication bound.
The [additive-label obstruction](../../docs/research/additive-label-obstruction.md)
and [exact small control](../../docs/research/small-block-control.md) further narrow
the search; the small control does not have a positive network deficit.
The [quick 67 screen](../../docs/research/quick-67-screen.md) also excludes that
milestone from further pooling of the unchanged scratch trajectories.

The [packed movement audit](../../docs/packed-movement-audit.md) reduces a constant
swap count and sharpens the layer recurrence, but finds no stronger exponent
certificate from those changes. The root cost still forces `c = O(a)` under
the audited estimates. It identifies the stronger sparse-bit movement bound
that would be needed to remove this restriction. The 2^-75 result comes from
the stronger network, not from that recurrence refinement.

## The routing improvement and first witness

The new routing schedules use direct nonadjacent swaps already supported by
the manuscript. CRT axis reversal needs floor(d/2) field interchanges; exposing
and restoring all resampling axes needs at most 2(d-1). This replaces the
original O(d^2) count of adjacent moves by O(d) full-field interchanges.
The finite network and numerical operations remain the same as in our earlier
h = 46 construction. The exact sequence of data-movement operations changes.

The normalized layout cost improves from `d^2(1 + ell^tau)` to
`d(1 + ell^tau)`. Its exponent margin therefore becomes

$$
g_4=(1-\tau)(1-\epsilon),
$$

which permits a fixed dimension exponent `epsilon = 1/40`. With
`a = 9/500000000000`, the other choices are

$$
\tau=\sigma=1-a,\quad \beta=\frac12,\quad c=\frac a2,\quad
\lambda=1-\frac{3a^2}{4},\quad \lambda'=1-\frac{a^2}{2},\quad
\delta=\frac1{16},\quad C_1=20.
$$

Exact rational arithmetic gives

$$
\min_i g_i=\frac{a^2}{80}=4.05\times10^{-24}>2^{-78}.
$$

The [routing audit](../../docs/nonadjacent-axis-audit.md) checks coordinate order,
padding, coefficient records, fixed tapes, descriptor costs, precision, and
all remaining parameter dependencies. The routing change itself uses primitives
already present in the source. With OpenAI's original network and recurrence
exponents unchanged, it also supports the simpler bound **kappa = 2^-107**.

## The earlier parameter-only result and its ceiling

Our [first note](../../artifacts/parameter-note.pdf) gives `kappa = 5.8e-33` under
the original layout cost accounting. Within the stated network-counting
family and those cost inequalities, it establishes `kappa < 5.838e-33`, even
allowing variable `beta` and unequal `tau` and `sigma`. The exact search covers
every admissible integer h, using a decreasing bound for the infinite tail.

That ceiling remains valid for its stated assumptions. The original layout
cost forced `epsilon < a`, yielding a cubic constraint `kappa < a^3`.
The new schedules improve that cost and remove the restriction. With a fixed
epsilon, the supplied saving instead scales quadratically in a. We do not
claim that quadratic dependence is unavoidable or that the latest bound is optimal for
the revised accounting.
