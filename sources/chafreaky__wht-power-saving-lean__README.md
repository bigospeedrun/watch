# Discrete Fourier transform of every length in O(n (log n)^z), z = 1 - 7.474546e-4, checked in Lean

Author: Jacob Sussman. Repository: https://github.com/jacobalansussman/wht-power-saving-lean. Licence: Apache-2.0 ([LICENSE](LICENSE), [NOTICE](NOTICE)).
Text of 2026-10-09, third revision. The first text is commit `024f763`; the second is commit `fdfb781`, with its
note on open directions in `e0bbe1c`; all of 2026-10-09.

A Lean 4 proof that one fixed program computes the discrete Fourier transform of every length n in
O(n (log n)^z) operations with z < 1, in the exact-arithmetic RAM cost model of OpenAI's "Exact Fourier
transforms below n log n" ([openai/math](https://github.com/openai/math), family 130, commit `fd4aeeb`).
This is OpenAI's own headline statement. The saving 1 - z proved here is 7.474546e-4, where OpenAI's
statement has 10^-13. The statement file is OpenAI's challenge file with the exponent replaced (section 1
names the two other differences, a comment and one letter on seven names). The same file states convolution,
and that is proved as well. The step from the lengths 2^k to every length is OpenAI's reduction, repeated here
with one constant changed ("Whose reduction this is", below).

**This is the third result of this repository. The first two are its siblings.** They are for the
Walsh-Hadamard transform of the lengths n = 2^k: saving 7.474547e-4 (the second result) and 5.399225e-4 (the
first), both published here on 2026-10-09. They are still in the repository and still stand (section 1). The
Fourier theorem and the second result are two corollaries of one kernel program, a program that applies the
k-fold tensor power of one fixed 2-by-2 matrix to an array of length 2^k, and they rest on the same
certificate. The first result comes from a kernel program of the same kind with an earlier network.

**This is not an OpenAI project.** OpenAI did not write, review or endorse it. The 89 files under `OAI/` are
OpenAI's, unmodified. Under `Work/Fourier/` there are copies of OpenAI's files with changes: each says so in
its first lines, and [NOTICE](NOTICE), section 7, lists them. The Lake package name `OAI` and the namespace
`OAI.PowerSaving` are theirs and are kept only because the new modules extend their development.

I built this on 8 and 9 October 2026 with a team of AI agents (Claude) that I directed (section 4): the first
result in about a day, the second in the hours after it, the third later the same day. Every proof here is
checked by
Lean's kernel. The new proofs have not yet had a line-by-line human review, and I would welcome one. Please
read section 2 before quoting the number. Credits and the relation to other work: [RELATED-WORK.md](RELATED-WORK.md).

## Fourth result (pull request, 2026-10-10): the same theorems with the circuit of pull request #233, saving 7.547361e-4

Contributed by Chafik Boukhalfa (CrocSwap/integer-mult-bounds pull requests #200, #233, #256; Anthropic Claude
assistance), as a pull request to this repository. Nothing of the first three results is changed; the new files
are listed in ORIGIN.md ("Files added in the fourth revision").

The helper circuit of the second result with the reuse pairing of pull request #233 in place of the pairing of
#193 (operation frames unchanged; R = 9,412 slots, N = 262,944 unit moves, 69,683 blocks per invocation against
70,169) is `tools/certificate/gcert1-p11-pr233-flow.json.gz`, in the same format gcert/1, made by
`tools/emit/gcert_emit.py` from the published data of the outside repository (`tools/emit/ORIGIN.md`). With
the generators of this repository unchanged (`tools/gx/gxgen.py`, `tools/gx/gxrate.py`: `tools/gx/regen_check.py
tools/certificate/gcert1-p11-pr233-flow.json.gz P233 B2Gp233`) it gives, all proved in Lean (kernel; axioms
`propext`, `Classical.choice`, `Quot.sound`; `tools/Compare.lean` passed for both):

    theorem OAI.PowerSaving.WHT.wht_main_block_B2Gp233x :
        ∃ solve W, WHTProgram solve W ∧ WHTTimeBoundsAt (1 - 7547361/(10:ℝ)^10) W
    theorem OAI.PowerSaving.transform_mainY : DFTGoalY        -- decimalExponentY = 1 - 7547360/10^10
    theorem OAI.PowerSaving.convolution_mainY : ConvGoalY

The Walsh-Hadamard statement is `Work/GCert/Data/ChallengeB2Gp233x.lean` (the challenge of the second result
with the exponent replaced); the Fourier statement is `Work/Fourier233/UniformFourierChallenge.lean`, OpenAI's
challenge file with the exponent `1 - 7547360/(10^(10:ℕ))` and the letter `Y` on the same seven names (`Z` in
the third result, so that both chains can live in one repository). The copies under `Work/Fourier233/` are made
by `tools/fourier/mkchain233.py`, which differs from `mkchain.py` only in its constants (`diff` the two), and
`Work/Fourier233/Seam.lean` is `Work/Fourier/Seam.lean` with the certificate and the exponent replaced.
Price of the circuit by the Python mirror (`tools/gx/gxdry.py`): whole-block 7547361/10^10 (7547364 holds,
7547365 fails), per-rank unchanged at 4058344/10^10. The outside repository's own figure for this word in its
three-stage layout is 7.0990740e-4 (pull request #233, certified by its scripts); in the five-stage layout of
this repository the pairing alone is worth +0.97 percent over the circuit of #193. The official comparator was
not run for this result (VERIFY.md, section 10).

## What is new here

- **A machine-checked proof of OpenAI's own headline statement, the discrete Fourier transform of every
  length, with saving 7.474546e-4.** OpenAI's statement has 10^-13. The statement file is OpenAI's challenge
  file with the exponent replaced (section 1). As far as my scans found at the time of writing, the largest
  saving in an outside Lean proof of that statement was 3.2e-6
  ([danadran01/exact-dft-power-saving](https://github.com/danadran01/exact-dft-power-saving); not built
  here), and the largest in an outside written argument was 6.7e-4 (shea256; conditional, not
  formalised).
- **The largest saving for the kernel program and for the Walsh-Hadamard transform that I could find anywhere
  at the time of writing, and it is machine-checked:** 7.474547e-4. The largest outside figure for the same
  quantity (the "complex side" of the community's networks) was 7.009184e-4
  (pull request #193; read again at 18:11 UTC), certified by scripts.
- **A five-stage "bridged" layout that, as far as my scans found at the time of writing, is in no other
  work.** The same helper circuit gives 7.009e-4 in the three-stage layout its authors use and 7.474547e-4 in
  this one.
- **As far as my scans found at the time of writing, the first Lean proof of the general frame lemma for this
  machine model**, including the cost of its "adapter" steps, which until now was argued on paper only.
- **A certificate checker with soundness proofs.** A better circuit in its format is now a data file for it,
  not a new proof.
- **As far as my scans found at the time of writing, the first complete machine check of the community's
  circuit of pull request #193**, the one with the largest complex-side saving I know of, as rebuilt here
  from their published data (section 3 says what that rests on). Its own validation was local; its author's
  words are quoted in the next section.

Two things behind this list are not mine. The step from the kernel program to every length is OpenAI's
reduction, and the helper circuit is the community's. The next two sections give the credit. Section 5 says in
plain words what each of these items is. "My scans" are the read-only looks at public sources by the AI agents
I directed; RELATED-WORK.md says what they covered and when, the last one at 18:11 UTC on
2026-10-09.

## Whose reduction this is

The step from the kernel program to the Fourier transform of every length is OpenAI's, in every part. Their
Lean proof uses the network through one theorem (`hills_program` in their `TensorProgram.lean`), and that
theorem is used in one place. The generalised engine of this repository proves the same sentence with my
exponent in place of theirs. So the third result needed no new mathematics after the kernel program:

- **OpenAI's 11 files between that theorem and their final statement are repeated here with one constant
  changed: the exponent.** The files are `SectorAlgorithm`, `SynchronizedAlgorithm`, `WorkingTransform`,
  `WorkingCompiler`, `WorkingPreparation`, `ArbitraryLength`, `TransformProgram`, `ConvolutionProgram`,
  `UniformBounds`, `Asymptotics` and `Main` (1,825 lines in OpenAI's repository). The copies are under
  `Work/Fourier/`. In them OpenAI's exponent `alpha` = 1 - 2/10^11 is `alphaZ` = 1 - 7474547/10^10, the work
  bound `hills` that is defined from it is `hillsZ`, the one use of `hills_program` is `hillsZ_program`, and
  the exponent of the final statement, 1 - 1/10^13, is 1 - 7474546/10^10. Every declaration of the copies has
  the letter `Z` in its name (115 of the 167 at the end of their own name, the other 52 on the name of the
  declaration they belong to, as in `WeftZ.transfer`), so that Lean cannot take OpenAI's original for the copy, and the
  import lines point to the copies. Two further edits were needed, and the first comment of each file names its
  own: in the copy of `Main` the same constant stands once as a literal number, 2/10^11, and is replaced there
  too (the two final theorems of that copy also received a comment of their own); and in the copy of
  `SynchronizedAlgorithm` the name `canopy` is written out as `Grove.canopy` in 5 places, because in the larger
  environment of the copy the short name would mean another declaration. The script also put the letter on three
  names inside OpenAI's comments; the comments are otherwise OpenAI's and describe OpenAI's network. The proofs
  are OpenAI's. A script made the copies
  (`tools/fourier/mkchain.py`). A twelfth small file, `Work/Fourier/Goal.lean`, repeats the five definitions
  of OpenAI's `Goal.lean` that contain the exponent of the statement.
- **The copies are marked as modified.** Each begins with a comment that names the OpenAI file it is derived
  from and says what was changed, as the Apache-2.0 licence asks, and [NOTICE](NOTICE), section 7, lists
  them. OpenAI's own files under `OAI/` are unmodified, as before, and the proof still imports them.
- **New Lean for the third result: one file, `Work/Fourier/Seam.lean` (245 lines), written by the
  agents.** It states the kernel program of the generalised engine in the form that OpenAI's reduction asks
  for, and proves the few facts about the work bound that the reduction uses.

The price of the reduction is a factor (log log n)^2 at the kernel's own exponent. That is why the Fourier
saving is 7.474546e-4, just below the kernel's 7.474547e-4 (section 2, point 4).

Others reached this statement before me, and the credit for that is theirs:

- **danadran01**, [danadran01/exact-dft-power-saving](https://github.com/danadran01/exact-dft-power-saving)
  (commit `1a7b25e`, 2026-10-09 03:48 UTC). As far as my scans found, the first Lean proof that improves
  OpenAI's Fourier statement: saving 3.2e-6 on OpenAI's own `DFTProgram` and `TimeBounds`, with whole-block
  recursion in Lean under the name "grouped recursion". Their development changes three of OpenAI's files,
  all three at the theorem named above, and by their record the rest of OpenAI's chain then goes through as
  it is. Their record reports a clean build, the standard axioms and `leanchecker`, and no comparator run.
  It was not built here.
- **shea256**, [shea256/fourier-transform-below-nlogn](https://github.com/shea256/fourier-transform-below-nlogn).
  The first written transfer of a community network to this statement (first commit 8 October 2026; eumemic
  writes of it: "That work has priority for the idea of the transfer"). Its figure was 6.7e-4 when
  it was last read (18:11 UTC on 2026-10-09, commit `a2840b1`): "a proposed conditional transfer, supported by a
  written argument and
  finite checks". Not formalised.
- **eumemic**, [eumemic/exact-dft-bounds](https://github.com/eumemic/exact-dft-bounds) (commit `6f87d1a`). A
  written transfer with batched recursion: every saving below 4.856e-4, with an extra log log factor; in
  their words "a paper proof with an exact finite certificate, and it is not formally verified". Their
  README also states in writing the observation that the route here rests on: OpenAI's later sections use
  the kernel theorem "only through three things: the bound O(2^k (k+1)^θ), the fact that only rational
  constants and i are needed (their §5.3), and its word-size accounting".
- The helper circuit behind the kernel program is the community's (next section), and the accounting is
  their whole-residual batching (RELATED-WORK.md, section 1).

What is mine in the third result: the kernel program at this exponent with its machine check (the second
result), the seam file, and the machine check of the whole against OpenAI's statement.

7.474546e-4 is 233 times danadran01's Lean figure, 1.54 times eumemic's written figure and 1.12
times shea256's. The two written figures rest on other networks, and they were moving within hours while this
was written.

## Whose circuit this is

The helper circuit (section 6) is the part of the network that decides the size of the saving. In the second
result, and so in the third, it is the community's in every part:

- the paired-cube construction: icekylinx, [#144](https://github.com/CrocSwap/integer-mult-bounds/pull/144)
  (in their main branch since 2026-10-09 05:06 UTC). Its notice credits an664 (#128) for the workspace-sharing
  principle and eumemic (#117) for the producer that its modules restrict;
- the modules, carrier links, frames and physical layer at p = 11: eumemic,
  [#168](https://github.com/CrocSwap/integer-mult-bounds/pull/168) ("PR168 v4");
- the local circuit inside each cube that takes a + b and a - b from the same two arrays, and the frame flow
  that goes with it: icekylinx, [#184](https://github.com/CrocSwap/integer-mult-bounds/pull/184);
- that construction on #168's newer modules: ikeboy, [#191](https://github.com/CrocSwap/integer-mult-bounds/pull/191);
- the choice of hand-over pairs with which that step runs in place and erases nothing: ikeboy,
  [#193](https://github.com/CrocSwap/integer-mult-bounds/pull/193). In their accounting this last step is the
  whole jump from 6.6307e-4 to 7.009184e-4.

#193 states its own credits so: "icekylinx (PR184, with GPT-6 Astra and Codex assistance) for the method, the
tools and the bit supplier. eumemic (PR168 v4, with Claude assistance) for the query modules and the physical
layer. Package by Avi Eisenberg with Claude assistance." Techniques of other authors that reach the circuit
through these pull requests (slot reuse at birth, frame descent) are credited in RELATED-WORK.md, section 1.

The agents rebuilt the circuit from the files that these pull requests publish (the module files, carrier
links and frames of #168 and the pair list of #193; [NOTICE](NOTICE) names each file), with a generator of their
own, as one explicit list of additions. No outside program was run. That repository is under Apache-2.0.

What is mine: the Lean proof of the general frame lemma for this RAM model, the generalised engine, the
extended certificate checker (section 5), the bridged five-stage layout in which their circuit is placed
(section 6), and the machine check of the whole.

As far as my scans found at the time of writing, this is the first full machine check of that circuit. The
author of #193 states the
scope of that pull request's own validation in these words: "The exact lift and the contract checks establish
the local maps and the flow ledger. There is no globally renumbered scalar transcript of the new complex word
and no full Clifford/router replay." What is checked here is the circuit inside my statement. Their theorem is
about integer multiplication and has further parts that this repository does not touch (section 2, point 1).

7.474547e-4 is above the 7.009184e-4 that #193 states for the same circuit because the layout differs: their word
has three stages, mine has five. By the agents' computation the same circuit in a three-stage word gives 7.0091e-4.

## 1. The results

### The Fourier transform of every length (third result)

One fixed program, in the RAM model of OpenAI's proof, computes the discrete Fourier transform of every length
n >= 1 in O(n (log n)^z) operations with z = 1 - 7474546/10^10, and in o(n log n). The saving 1 - z is
7.474546e-4. The logarithm is the natural one, as in OpenAI's statement. A second fixed program does the same
for convolution.

    theorem OAI.PowerSaving.transform_mainZ : DFTGoalZ
    theorem OAI.PowerSaving.convolution_mainZ : ConvGoalZ

    def DFTGoalZ : Prop := ∃ order solve W, DFTProgram order solve W ∧ TimeBoundsZ W
    def ConvGoalZ : Prop := ∃ order solve W, ConvProgram order solve W ∧ TimeBoundsZ W
    def TimeBoundsZ (W : ℕ → ℕ) : Prop :=
      let W' := fun n : ℕ => (W n : ℝ)
      W' =O[atTop] paperTime ∧ W' =O[atTop] decimalTimeZ ∧ W' =o[atTop] nlogn
    def decimalTimeZ (n : ℕ) : ℝ := (n:ℝ) * (Real.log (n:ℝ)) ^ decimalExponentZ
    def decimalExponentZ : ℝ := 1 - 7474546/(10^(10:ℕ))

Proof: module `Work.Fourier.Main`. The statement with every definition it depends on: module
`Work.Fourier.UniformFourierChallenge` (`Work/Fourier/UniformFourierChallenge.lean`, 348 lines, imports only
Mathlib). It is
OpenAI's challenge file `lean/ComparatorChallenges/UniformFourier.lean` (336 lines) with three changes, which
its first comment lists: that comment; the exponent, `1 - 1/(10^(13:ℕ))` in OpenAI's file; and the letter `Z`
at the end of seven names (`decimalExponent`, `decimalTime`, `TimeBounds`, `DFTGoal`, `ConvGoal`,
`transform_main`, `convolution_main`). The letter is forced: the proof imports OpenAI's unmodified files, in
which these names carry OpenAI's values. Every other byte of the file is OpenAI's.

- `DFTProgram order solve W`: `order` and `solve` are two programs of the RAM, `solve` in the mode without
  general products. For every n >= 1, `order` computes from n a number d with 0 < d < 1024 n^3. For every
  complex vector x of length n, the run of `solve` on (n, exp(2 pi i / d), x) is valid (no division by zero)
  and returns exactly `dft n x` (entry j is the sum over k of exp(2 pi i j k / n) x_k). The work of `order`,
  one unit for the root, and the work of `solve` are together at most W(n). Every integer the two programs
  produce, and W(n) + 10(n+2), is at most (n+2)^c for one constant c. The root of unity is an input because
  the RAM has no instruction that produces it.
- `ConvProgram order solve W`: the same for the convolution of two vectors of length n (`conv n x y`, of
  length 2n - 1), with `solve` in the mode with general products and a root of order below 1024 (2n-1)^3.
- `TimeBoundsZ W`, three bounds as n grows: W(n) = O(n (log n)^(1 - d)) with d = 7.474546e-4
  (`decimalTimeZ`; the one line whose value differs from OpenAI's, where d = 10^-13); W(n) =
  O(n (log n)^theta (log log n)^(4 - theta)), the bound of OpenAI's manuscript with its own theta, about
  1 - 2.1e-13 (`paperTime`, unchanged); and W(n) = o(n log n).

The cost model and its caveats are the same for all three results. The paragraph "The cost model is OpenAI's,
with its caveats" below states them.

**Whose statement this is.** OpenAI's, with one number replaced. No definition in it was written for this
repository.

**Where the exponent comes from.** The kernel program runs at saving 7.474547e-4; the theorem of the second
result rests on it. OpenAI's reduction turns it into a Fourier program whose work is
O(n (log n)^z (log log n)^2) at that z. A pure power of log n therefore needs an exponent slightly above z,
and the statement has the saving 7.474546e-4 (section 2, point 4).

### The Walsh-Hadamard transform (second and first results)

One fixed program, in the RAM model of OpenAI's proof, computes the Walsh-Hadamard transform of every length
n = 2^k in O(n (log2 n + 1)^z) operations with z = 1 - 7474547/10^10 = 0.9992525453, and in o(n log n).
The saving 1 - z is 7.474547e-4.

    theorem OAI.PowerSaving.WHT.wht_main_block_B2Gp193x :
        ∃ solve W, WHTProgram solve W ∧ WHTTimeBoundsAt (1 - 7474547/(10:ℝ)^10) W

Proof: module `Work.GCert.Data.SolutionB2Gp193x`. The statement with every definition it depends on: module `Work.GCert.Data.ChallengeB2Gp193x`
(`Work/GCert/Data/ChallengeB2Gp193x.lean`, 331 lines, imports only Mathlib). It is the statement of the first result
with the exponent replaced and nothing else: the theorem has a new name, and the comments of the file quote
the new names and the new exponent.

- `WHTProgram solve W`: `solve` is one program of the RAM, in the mode without general products. For every k
  and every complex vector x of length N = 2^k, its run on (k, i, x) is valid (no division by zero), returns
  exactly `wht k x` (Sylvester order: entry j is the sum over l of (-1)^(number of common 1-bits of j and l) x_l),
  costs at most W(k) units of work, and every integer it produces, and W(k) + 10(N+2), is at most (N+2)^c for
  one constant c. The imaginary unit i is an input because the RAM has no instruction that produces it.
- `WHTTimeBoundsAt β W`: W(k) = O(2^k (k+1)^β) and W(k) = o(2^k k) as k grows.

**The cost model is OpenAI's, with its caveats.** Numbers are exact complex numbers. One addition, one
subtraction or one multiplication by a prepared scalar costs one unit of work, whatever the size of the numbers.
Index arithmetic and array access are charged too. The coefficients are unrestricted. Only the integers
(indices, lengths) are bounded, by a polynomial in n. OpenAI describes its own result in these words: "the model
permits exact complex arithmetic and unrestricted coefficients, while integer values and indices remain
polynomially bounded in n" (their `lean/docs/130.md`). So the theorem says nothing about bit complexity, about
computations with bounded coefficients, or about numerical stability (section 2, point 6).

**Whose statement the Walsh-Hadamard one is.** OpenAI's repository states and proves the discrete Fourier transform of every
length (`DFTProgram`, `TimeBounds`, stated saving 10^-13). Its family 130 has no Walsh-Hadamard statement. The RAM
cost model in my statement (challenge lines 22-270) is OpenAI's, byte for byte (their
`lean/ComparatorChallenges/UniformFourier.lean`, lines 9-257). The about 60 lines after it (271-331), which
define `wht`, `WHTProgram` and `WHTTimeBoundsAt`, are my project's, written on the pattern of OpenAI's
`DFTProgram`, and should be read. The agents first proved the statement with the exponent 1 - 2/10^11 of OpenAI's
tensor engine (`alpha` in their `TensorSaving.lean`) as a corollary of that engine (`WHTCheck/Solution.lean`).
Here only the exponent is replaced.

**The first result.** `wht_main_block_B2Ke16x`, saving 5.399225e-4 (z = 1 - 5399225/10^10), with my project's
own helper circuit and the first engine. Proof: `Work.CarrierCheck.SolutionB2Ke16x`; statement:
`Work/CarrierCheck/ChallengeB2Ke16x.lean` (331 lines). It was published on 2026-10-09 (commit `024f763`) and its
files are in this repository as they were published. So is its companion with OpenAI's own recursion,
`wht_main_rank_B2Ke16x`, the same statement with 1 - 3155781/10^10 (`Work.CarrierCheck.SolutionB2Ke16xR`). The two
figures of the first result are two accountings of the same network. Per-rank: every single move is one
recursive call on 1/m of the coordinates, as in OpenAI's proof. Whole-block: r consecutive moves of one array
are one call on r/m of the coordinates. That idea is the community's "whole-residual batching"
(RELATED-WORK.md). Its Lean proof for this RAM model is in this repository. The second result exists in
whole-block accounting only (section 2, point 3).

## 2. What is not claimed

1. **It is not a better circuit, and it does not verify the community's theorem.** The second result places
   their circuit in my layout and checks it for my statement. Nothing here is about integer multiplication.
   Their headline figure, kappa, also needs a second ingredient (the "bit side") and analytic and routing
   interfaces that their authors call assumptions. None of that is checked or used here. The third result
   uses the same circuit and has no circuit of its own.
2. **The outside figures are a different quantity, and they keep moving.** The titles of the pull requests to
   CrocSwap/integer-mult-bounds give kappa, the saving for integer multiplication: roughly the smaller of the
   "complex side" saving, which is the quantity of my theorem, and the bit side. For #193: complex side
   7.009184e-4, kappa 6.647872e-4.
   - At 16:06 UTC on 2026-10-09 pull requests up to #207 existed. The largest kappa in a title was 6.831905e-4
     (#207, Dugongue, open, 16:00). The largest complex-side saving stated in any of the bodies of #193 to #207
     was still 7.009184e-4: the circuit of #193, which #194, #197, #202, #204, #205, #206 and #207 keep while
     they change the bit side. The front page of the hub's main branch (`3b6b668`) named #186 as its reviewed
     result (kappa 6.61885549e-4).
   - At 18:11 UTC on 2026-10-09 pull requests up to #215 existed. The largest kappa in a title was 6.839217e-4
     (#210, eumemic, open, 16:58). The largest complex-side saving stated as a result in the bodies of #208 to
     #215 was still 7.009184e-4, the circuit of #193, which #210, #211 and #213 keep. #208 prices further steps,
     up to kappa 1.226488e-3, and its title calls them "target, not built".
   - Their authors call each figure conditional. The figures are certified by Python scripts, are not peer
     reviewed and are not Lean theorems.
   - [#192](https://github.com/CrocSwap/integer-mult-bounds/pull/192) (DaysSky) states a ceiling of 7.010e-4
     "for every frame layout of #168's word". #193 says of it: "The PR192 frame ceiling covers only PR168's
     fixed word and pairs, so it does not apply to this word." My figure is above it for one more reason, the
     five-stage layout.
3. **Whole-block accounting only.** The generalised engine has a whole-block theorem and no per-rank theorem.
   So the second result has no companion with OpenAI's own recursion. In per-rank accounting the result of this
   repository is still 3.155781e-4, from the first network. The third result rests on the same whole-block
   kernel program, so it has no such companion either: in OpenAI's own recursion the Fourier statement
   stands where OpenAI proved it.
4. **The Fourier saving is strictly below the kernel's.** The final statement of the third result carries
   no extra factor: it is O(n (log n)^(1 - d)) with d = 7.474546e-4. Behind it, OpenAI's reduction costs a
   factor (log log n)^2 on top of the kernel program. At the kernel's own exponent, z = 1 - 7.474547e-4, the
   chain therefore gives O(n (log n)^z (log log n)^2), and a pure power of log n needs an exponent a little
   above z. The same argument would give every saving below 7.474547e-4. The theorem here states
   7.474546e-4, and it does not state 7.474547e-4 itself.
   - Outside figures for the same statement, none of them built or checked for this repository: 3.2e-6 in
     Lean ([danadran01/exact-dft-power-saving](https://github.com/danadran01/exact-dft-power-saving));
     in written arguments that are not formalised, 6.7e-4, conditional
     ([shea256/fourier-transform-below-nlogn](https://github.com/shea256/fourier-transform-below-nlogn)),
     and every saving below 4.856e-4 with an extra log log factor
     ([eumemic/exact-dft-bounds](https://github.com/eumemic/exact-dft-bounds)). They rest on other networks.
   - The Walsh-Hadamard results are for the lengths 2^k only. The first of them, with my project's own
     circuit, has not been carried over to the Fourier statement.
   - The statement is OpenAI's `DFTProgram` and `ConvProgram`: transforms over the complex numbers, with a
     root of unity supplied to the program. Nothing is claimed for other transforms or other models.
5. **It is a statement about growth, not a usable algorithm.** (c) marks numbers computed from a formula, not in
   Lean. The figures are those of the kernel program of the second and third results; the first result's
   are in brackets.
   - The proof works with a table of 2^a arrays indexed by all orthogonal matrices of a 110-dimensional space
     over F_2 [80-dimensional]. The table is never written down. a = 6049 (c) [3213], and 2^a has
     1821 digits (c) [968].
   - Below log2 n = m (a + 1) = 665,500 (c) [257,120] the program is the ordinary n log n algorithm.
     Nothing changes for any input whose length has fewer than 200,336 digits (c) [77,401].
   - The constant is huge. As one of the agents read in the Lean proofs, the program fills all 2^a arrays with
     the input, which puts a factor 2^a into the constant. With it the bound is below n log2 n only when
     log2 log2 n exceeds a/(1 - z), about 8e6 (c) [6e6]. A second explicit factor is 1 + 1/slack of the
     rate inequality, with slack 6e-10 (the auditing agent's arithmetic; the rational bounds of the Lean proof leave 2e-12)
     here [2e-10 to 4e-10]. Machine constants were never computed, here or by OpenAI.
   - With every constant set to 1, a gain of 1% over the ordinary algorithm needs log2 n near 2^39
     (c, heuristic) [2^45].
   - For the third result these are figures of the kernel program, not of the Fourier program. The
     Fourier program calls the kernel program on arrays whose lengths it chooses itself: by the agents'
     reading of OpenAI's files, about (log log n)^2 sweeps on arrays of total length at most 8n. The
     lengths n at which the saving starts, and the constants of the reduction, were not computed, here
     or by OpenAI.

   In Lean: `tableExp n s = Nat.clog 2 n + s`, `threshold u a = u * (a + 1)`, m = 110, s = 40, 14,692
   arrays per unit [m = 80, s = 40, 9362], one unit per orthogonal matrix. Not in Lean: the order of that group,
   which gives a and so every (c).
6. **It is not a statement about bit complexity or about numerical computation.** One unit of work is one exact
   operation on complex numbers of any size, and the coefficients are unrestricted (section 1). OpenAI writes of
   its circuit result that it makes "no all-length, bounded-coefficient, conditioning, or bit-complexity claim".
   The last three limits hold here as well. The classical lower bound of order n log n for linear computations
   with bounded constants (Morgenstern, 1973) is not contradicted: this model does not bound the constants.
   All of this holds for the third result too. Its root of unity is an exact input.

What is real is the exponent: a theorem about growth for all n in this model, machine-checked.

## 3. How it was checked, and the limits

All times are UTC. The AI agents ran every check, on one machine.

**Third result.**

- **Comparator.** The comparator (described under the second result, below) was run with the configuration
  `comparator/UniformFourier.json`. Its challenge is `Work/Fourier/UniformFourierChallenge.lean`, OpenAI's
  challenge file with the exponent replaced
  (section 1), and it checks both theorems, `transform_mainZ` and `convolution_mainZ`. Its verdict "Lean
  default kernel accepts the solution" / "Your solution is okay!" was obtained twice, in the project's working
  tree, on Lean files that are byte for byte those of this repository: by the agent that built the proof, at
  18:27 (1528 s), and by an auditing agent with its own configuration, at 18:55 (1236 s).
- **Audit by a separate agent** (another Claude session with its own scripts; not a human). Besides its own
  comparator run it ran the second comparison script (`tools/Compare.lean`): pass, on the three standard
  axioms. Both tools reject the same proof against a statement whose saving is one unit larger. It compared
  the eleven repeated files with OpenAI's originals token by token: apart from the renames, the differences are
  the seam, one constant, and one name written out in full in five places, which keeps OpenAI's meaning. It
  walked both proofs: they reach every kernel check of the certificate and no `sorryAx`. It did not read the
  repeated proofs line by line and did not rebuild from source.
- **What the kernel replays.** The Fourier theorem rests on the certificate of the second result. The
  comparator replays the whole proof in the kernel, the segmented evaluations of that certificate included.
- **Build.** The modules of `Work/Fourier` were compiled from source in the project's working tree, on the
  compiled modules of the second result (under two minutes; VERIFY.md, section 3). What is said below about the
  build of the second result holds here too: no build from nothing has been made. In a copy of the
  repository the 15 new modules were compiled from source on the compiled modules of the second revision; the
  comparator and `tools/Compare.lean` were then run in that copy and both passed (comparator 19:01 to 19:20,
  1137 s; `tools/Compare.lean` 19:23).
- **The repeated files.** `tools/fourier/mkchain.py` (242 lines of Python) makes the 11 copies, `Goal.lean`, the
  challenge and the comparator configuration from OpenAI's unmodified files. `python3
  tools/fourier/regen_check.py` runs it again and compares the result with the files of this repository: all 14
  were reproduced byte for byte (VERIFY.md, section 6). So every difference between a copy and its OpenAI
  original is one that the script makes, and the script can be read. A second comparison, by another agent's own
  script, of each copy with its original line by line made the table in ORIGIN.md. Beyond the renamed names, the
  import lines and the added comments it found the two edits named in "Whose reduction this is", the exponent
  line of the challenge, and no other change to the code.
- **Audits by separate agents** (other Claude sessions; not humans). I had an auditing agent compare the new
  statements with OpenAI's as kernel terms, not as text. In the seam file, `hillsZ_program` has the type of
  OpenAI's `hills_program` with `hills` replaced by `hillsZ`; `hillsZ` is OpenAI's `hills` with `alpha` replaced
  by `alphaZ`; `alphaZ` is OpenAI's `alpha` with 2/10^11 replaced by 7474547/10^10; and the six side facts have
  OpenAI's statements. A walk of the proof term of `hillsZ_program` reached 38,544 constants: all 106 names of
  the certificate of the second result and of its soundness chain that the audit of the second result had listed
  (every kernel check of the certificate among them), no other certificate, none of OpenAI's `hills_program`,
  `hills` or `alpha`, no `sorryAx`, and the three permitted axioms only. The agent compared statements and
  walked proof terms; it did not read the proofs.

**Second result.**

- **Comparator.** The [comparator](https://github.com/leanprover/comparator), which OpenAI's repository uses
  for its own results, was run with the configuration `comparator/B2Gp193x.json`. It checks that the solution module proves
  exactly the challenge statement with identical definitions, replays the proof in the Lean kernel, and admits
  only the axioms `propext`, `Classical.choice`, `Quot.sound`, so a `sorry` or a `native_decide` is rejected.
  Its verdict "Lean default kernel accepts the solution" / "Your solution is okay!" was obtained three times:
  twice in the project's working tree, on Lean files that are byte for byte those of this repository, by the
  agent that built the proof at 15:14 (1814 s) and by an auditing agent with its own copy of the configuration
  at 15:43 (1116 s); and in the build copy of the repository at 16:13 (1058 s; next item).
- **Build in a copy of the repository.** A copy with the Lean files, `lakefile.lean`, `lean-toolchain`,
  `lake-manifest.json` and `comparator/` of this revision was built on the compiled files of the first
  publication's rebuild from scratch (Mathlib from its cache, the 194 published modules compiled from nothing).
  The 102 new modules that do not load the new certificate were compiled from source in the copy. For the 31
  modules that load it, the compiled files of the project's working build were cloned: Lake accepted the 25 data
  and check modules by their traces and compiled the 6 modules above them from source. `lake build --no-build`
  of all eight roots then reported every target up to date (9250 jobs, 15:48), with the three permitted axioms
  for the theorem and "declaration uses `sorry`" for the three challenge modules only. So the kernel evaluations
  of the certificate in those 25 modules were made by the compiler in the working tree, not in the copy, and the
  second result has not yet had a build from nothing. The comparator was then run in the copy and passed, with
  the same two verdict lines (16:13, 1058 s): it replays the whole proof in the kernel, those evaluations
  included. `tools/Compare.lean` then said `RESULT: PASS` there as well (16:15, 148 s).
  [VERIFY.md](VERIFY.md) has every command, time and memory figure, and its own list of limits.
- **Certificate.** The certificate is literal data in `Work/GCert/Data/Gen/`: the 43,036 gates of one
  invocation, each a group of single additions at one frame, and the table of its 18,248 frames. It is too large
  for one evaluation, so the Lean kernel checks it in segments (each `by decide +kernel`, axiom `propext` only):
  13 evaluations for the label half (4 for the frame table, 5 for the replay of the gates and 1 for its final
  segment, 3 for the end conditions and the frames of the copies), 3 for the scalar half (2 for the replay, 660
  sources each, and 1 for the outputs), and 63 block counts.
  Lean theorems, written by the agents and not generated from the certificate, join the segments and say that
  every certificate accepted by them gives the network at the counted price. Five files of `Work/GCert/Chain/`,
  which carry the bridged network over to the generalised engine, were made by a script from the corresponding
  files of the first result; ORIGIN.md names them.
- **Audits by separate agents** (other Claude sessions with their own scripts; not humans).
  I had one auditing agent read the statements of the new theorems before the run (the statements, not the
  proofs): it found every hypothesis of the end theorem discharged inside the proof, by a kernel evaluation on
  the certificate, by the rate inequality or by a size fact. I had a second one re-run the comparator with its
  own copy of the configuration and the second comparison script (`tools/Compare.lean`); both passed, and both
  reject the same proof against a statement whose saving is one unit larger. It walked the proof term: 38,678
  constants, among them every kernel check of this certificate, and no `sorryAx`, no compiler axiom and no
  constant of the first certificate. It scanned the 124 new modules that the proof imports for `sorry`, `axiom`,
  `native_decide`, `unsafe`, macros and similar: none, apart from one file-local notation in two proof files;
  the statement file contains one `sorry`, on purpose. It recomputed the rate arithmetic with independent
  integer code: 7474547 holds; 7474548 and 7474549 would also hold but are neither proved nor claimed; 7474550
  fails (also a Lean lemma). The packaging agent ran the generators again on the certificate and got all 36
  generated files of this repository byte-identical. Not examined by the auditing agents: the proof texts, the
  Python generators, the conversion from the community's files, and whether the statement is vacuous (it is the
  text of the earlier challenges; see the limits).

**First result** (the record of the first publication, 2026-10-09; nothing in it has changed).

- **Comparator**, with the configurations `comparator/B2Ke16x.json` and `comparator/B2Ke16xR.json`. Its verdict
  "Lean default kernel accepts the solution" / "Your solution is okay!" was obtained
  - by the agent that built the proof: whole-block theorem 09:59, per-rank companion 10:03;
  - by an auditing agent with its own configuration: whole-block theorem 10:09;
  - in a rebuild from scratch: whole-block theorem 11:32, per-rank companion 11:35.
- **Rebuild from scratch.** A copy of exactly the files of the first publication, with no build directory, was
  built from nothing: the compiled Mathlib files were downloaded from Mathlib's cache and the 194 modules were
  compiled (11 minutes). Then `tools/Compare.lean` and the comparator were run in that copy for both theorems.
  All four runs passed.
- **Certificate.** The certificate is 3.9 MB of literal data in `Work/CarrierCheck/Gen/Cr2h16.lean`: the
  addition circuit of one invocation (section 6). Three Boolean checks of it and 43 block counts are evaluated
  by the Lean kernel (`by decide +kernel`, axiom `propext` only). Lean theorems, written by the agents and not
  generated, say that every certificate accepted by the three checks gives the network.
- **Audits by separate agents.** For the whole-block theorem I had an auditing agent re-run the comparator with
  its own configuration and a second comparison script (`tools/Compare.lean`); both passed, and both reject the
  same proof against a statement whose saving is one unit larger. It walked the proof term: 36,438 constants,
  resting on the kernel checks of this certificate and on no `sorryAx` or compiler axiom. It scanned the modules
  written here that the two proofs import (102 for the whole-block theorem, and the per-rank solution module)
  for `sorry`, `axiom`, `native_decide`, `unsafe`, macros and similar (none); the two statement files contain
  one `sorry` each, on purpose. It ran the generators again and got all 21 files that they write,
  byte-identical (16 of them are in this repository). It recomputed the rate arithmetic with independent
  integer code: 5399225 holds, 5399226 would also hold but is neither proved nor claimed, and 5399227 fails
  (also a Lean lemma). The 180 older files of the proof, with the checker and its soundness proofs, belong to
  proofs examined by two earlier audits of the same kind.

**Limits. Please weigh them.**
- The new proofs are checked by the Lean kernel but have not yet had a line-by-line human review; the
  auditing agents checked statements, not proof texts. So the claim rests on the kernel and on the statement
  being the right one. I would be glad to have both read.
- New in the third revision: the Fourier theorem adds no independent check of the kernel program. It rests
  on the certificate, the generalised engine and the checker of the second result, and every limit stated
  here for the second result holds for the third.
- New in the third revision: the 11 repeated files are OpenAI's proofs with every declaration renamed by a
  script. The kernel checks the result as it is. That the copies differ from OpenAI's files only as their
  first comments and NOTICE say rests on the file comparison named above, not on Lean.
- New in the third revision: the statement of the third result is OpenAI's challenge file with three
  changes (section 1). `diff` shows them in a few lines (VERIFY.md, section 1). The one that carries the
  claim is the exponent.
- New in the third revision: the third result has had three comparator runs, two in the project's working tree
  and one in a copy of the repository. `tools/Compare.lean` passed in both places, and the negative control (the
  checkers must reject this proof against a statement whose saving is one unit larger) was run in the working
  tree. A build of this revision from nothing has not been made.
- The comparator ran on macOS with a stand-in for its Linux sandbox `landrun`. The second kernel (`nanoda`) was
  off, as in OpenAI's configuration of its own Fourier challenge. `leanchecker` was not run on these modules.
- In every comparator run the modules of the proof had been compiled beforehand, outside the sandbox, so the
  comparator replayed existing build products. Mathlib was not rebuilt from source, and the Lean toolchain and
  the comparator programs were the ones already installed. See VERIFY.md, section 8.
- New in this revision: the second result has not yet had the rebuild from nothing that the first result had.
  The copy of the repository in which the comparator passed took the compiled files of its 25 certificate
  modules from the project's working tree ("Build in a copy of the repository", above), and the other two
  comparator passes were in that working tree.
- New in this revision: the certificate of the second result is checked by the kernel in segments. The theorems
  that join the segments are Lean proofs and are replayed by the comparator like everything else. The frame
  lemma, the generalised engine, the checker and its segmentation were all written on 2026-10-09; they are the
  larger part of what has not yet been read by a person.
- New in this revision: the circuit is the outside authors' design, and it was rebuilt from their published
  data by Python programs of the agents. That the rebuilt list of additions is the circuit #193 describes
  rests on that Python conversion and on equal counts (9,412 helper arrays, the same histogram of block
  ranks), not on Lean. The theorem does not depend on this: the kernel checks the certificate as it is.
  The programs that rebuilt the circuit from the community's files are not in this repository;
  `tools/gx/ORIGIN.md` names the outside files and commits they read. The last step, the conversion to the
  certificate format, is `tools/gx/gxconv.py`.
- New in this revision: the second result exists in whole-block accounting only (section 2, point 3), and the
  Lean checker covers the certificate format without its extension rule (unused by this certificate) and with
  every scratch copy at a frame of dimension at least 1.
- For the per-rank companion of the first result the comparator and `tools/Compare.lean` passed (the two runs
  above), but no negative control and no walk of the proof term were run. Its files were covered by the text
  checks and the arithmetic.
- A check that the statement is not vacuous was run for an earlier package (same text, other exponent), not
  for the published ones. It showed that `wht` at lengths 2 and 4 is the Sylvester matrix and that
  W(k) = 2^k k fails.
- The Python programs that searched for the first certificate and that rebuilt the second are not part of the
  trusted base. The search programs were not audited. The kernel checks the certificates, not the programs.

**I welcome re-runs**, most of all on Linux with `landrun` and with `nanoda` switched on. See VERIFY.md.

## 4. How it was made

I made this on 8 and 9 October 2026, in about a day, by directing a team of AI agents (Claude). I began by
having them verify OpenAI's proof independently, and then kept pushing on one question: how much larger can
the saving be made while every step stays machine-checked? I set the goals, chose which ideas to pursue,
and decided at each stage what to do next. The agents wrote the Lean proofs, designed the network, found
the certificate by computer search, and audited one another's work. Several of the design ideas were found
and published independently by other people during the same hours; RELATED-WORK.md gives the public record
and the credit.

The second result came in the hours after the first was published. The first text named the next thing to
try: a Lean proof of the community's general frame lemma in this framework. I had the agents attempt it, and
it went through the same day, together with an engine and a checker that use it. From then on the best
circuit the community had published could be checked as it stands, so I chose to check theirs. The agents
rebuilt it from the published data, wrote the Lean proofs and ran the checks.

The third result came later the same day. The note on open directions had named it as a lead: carry the exponent
over
to the statement OpenAI headlines. I had the agents scope it before anything was built. They found that
OpenAI's proof uses the network through a single theorem and that the generalised engine already proves that
theorem's sentence at my exponent, and they recommended the route that leaves OpenAI's files unmodified and
repeats OpenAI's reduction in this repository. I took that route and asked for speed. The agents wrote the
seam file, repeated the 11 files by script, and ran the checks.

## 5. What is new in the second and third revisions, in plain words

Words. An *array* is one working copy of the data, of length n. Its *frame* is the coordinate system it is
written in at a given moment. A *move* takes an array to a larger frame, and a *block* is a run of moves of one
array; blocks are the only thing that costs, a block of rank r being one recursive call on r/m of the
coordinates. An addition between two arrays is free and is allowed only when both stand at the same frame.

- **The general frame lemma.** In the first result a frame is given by a set of mutually orthogonal unit
  directions of the label space F_2^m, and a block adds such directions. The lemma says that every subspace U of
  F_2^m can serve as a frame, and that an array goes from the frame of U to the frame of any larger subspace V
  in one block of rank dim V - dim U. "Every" includes the *degenerate* subspaces, those that contain a non-zero
  vector orthogonal to the whole subspace; they have no basis of orthogonal unit directions. The community
  states the lemma in a written note (`notes/general-clifford-frames.tex` in the CrocSwap repository), and
  every one of their figures above 7.4e-5 rests on it. `Work/GFrame` proves it in Lean for the family-130 RAM
  model (`frame_lemma`; 54 modules; by the auditing agent's reading the final proof uses it in the form
  `SMv.of_sub`, `Work/GFrame/Labels/StageBSem.lean`). Also proved there: two frames of the same subspace
  differ by a free step, and a block between two subspaces of which neither contains the other has rank
  dim U + dim V - 2 dim(U ∩ V).
- **The generalised engine.** The engine is the part of the proof that turns a schedule of blocks and free
  additions into one RAM program with a time bound. OpenAI's engine, and the first engine here, know frames of
  orthogonal unit directions. The generalised engine accepts every frame of the lemma. For that it has two more
  free steps on a single array (the "adapter" steps), a permutation of addresses and a multiplication by a
  power of i that depends on the address, and it proves that each is one linear pass, like the free steps that
  existed before. It has a whole-block theorem only.
- **The extended checker.** A certificate is now one ordered list of single additions "target += c * source",
  each with the frame at which it happens, and a table of the frames, each a subspace given by a basis. The
  checker is a Lean function with two halves. The label half follows every array through the list: its frames
  must be nested, the arrays of an addition must stand at the same frame, and every climb is counted as one
  block of its rank. The scalar half replays the additions in exact arithmetic and tests that they compose to
  the exchange the network needs, whatever old content the helper arrays hold. Theorems in `Work/GCert` say
  that a certificate accepted by both halves gives one invocation at the counted price, and they carry the
  bridged five-stage network of the first result over to the generalised engine.
- **The circuit.** The community's paired-cube circuit at p = 11 ("Whose circuit this is", above; sizes in
  section 6), written as a certificate in that format. By the agents' count 91 percent of its moves pass
  through frames that the first engine cannot use. That is why the three items above had to exist first.
- **The seam and the repeated reduction (third result).** OpenAI's route from the kernel program to every
  length asks one thing of the network: a kernel program within a work bound. In their files the bound is the
  fixed function `hills`, the ceiling of (k+1)^alpha. `Work/Fourier/Seam.lean` states the kernel program of
  the generalised engine in exactly that form, with the bound `hillsZ` at my exponent (`hillsZ_program`), and
  proves what the reduction uses of the bound: it is at least 1, it grows with k, it is at most k + 1 and at
  most 2 (k+1)^z, and z lies between 0 and 1 and below the exponents of OpenAI's statement. The 11 files
  after it are OpenAI's, repeated with that bound ("Whose reduction this is", above).

## 6. The design

OpenAI's proof reduces the saving to a finite network. In the form used here: W arrays, each to be transformed
along all m directions of a label space F_2^m. One *move* transforms one array along one direction and is what
costs. Additions between arrays with equal labels are free. The plain schedule needs W m moves. A network that
needs only W m - D moves gives a positive saving, larger when D / (W m) is larger. The steps to the network of
the first result:

- **Bank pairs and the helper circuit.** A bank pair is two data arrays that exchange their contents through
  additions. The exchanges are what saves moves. One *invocation* serves v pairs and needs R *helper* arrays
  that hold the partial sums. Helpers make all m moves and save nothing, so R is the main cost. In the first
  result v = C(h,3), one pair per 3-subset of h points, and the circuit started from the outside circuit NStar3
  with carrier links.
- **Folded layout.** Earlier layouts index the pairs by a grid, which forces m = h^2. Indexing pairs and
  invocations by a group of isometries needs only m of about s h for s stages of invocations, linear in h.
- **One helper set for all stages.** The same R helpers serve one invocation in every stage. A re-framing lemma
  lets an invocation start with helpers that still hold old values.
- **Bridged five-stage word.** Every pair gets a twin, a second pair whose labels equal its own at three moments.
  Free additions between twins then exchange two pairs with five invocations in place of six. m = 5h, W = 4v + R.
- **Carrier certificates.** A wider certificate format in which the data arrays themselves take part in the
  additions, carry intermediate values and are read in place. This removes helpers. It needed a new invocation
  theorem, a checker and its soundness proof.
- **Searched addition order.** The order and grouping of the additions in the helper circuit was optimised by
  computer search. Together with the carrier format this brought R from 11,500 to 7,122.

Who published which of these ideas, and when, is in RELATED-WORK.md, sections 1 and 2.

**The second result** keeps the bridged five-stage word and replaces the helper circuit by the community's
paired-cube circuit ("Whose circuit this is", above). There the h = 2p coordinates come in p = 11 pairs. A
*port* takes one coordinate from each of three pairs, so v = 8 C(p,3). The 8 ports on the same three pairs form
a *cube*, and the circuit is 165 cubes, each with the same small local circuit on its 8 inputs, and the sums
that connect the cubes. Helper arrays that are no longer needed are handed to new users, and inside a cube two
arrays that hold a and b are turned into a + b and a - b in place.

| | h | v | m | R | W = 4v + R | D | moves per unit, in place of W m | one invocation |
|---|---|---|---|---|---|---|---|---|
| second result | 22 | 1320 | 110 | 9412 | 14,692 | 3080 | 1,613,040 of 1,616,120 | 70,169 blocks, 262,944 moves |
| first result | 16 | 560 | 80 | 7122 | 9362 | 1035 | 747,925 of 748,960 | 37,286 blocks, 130,993 moves |

The blocks of one invocation are counted by the kernel, rank by rank. For the second result the two totals
are the Lean theorems `inv_count` and `inv_moves` (`Work/GCert/Data/P193Price.lean`).

## 7. An open direction: the scratch copies

My weekly Claude limits ran out before I could chase this one, so here it is for anyone who wants it.

**What the copies are.** Every run of the helper circuit hands h totals to all the outputs at one moment (the
scatter). For that, each total is copied into a scratch array, and the copy has to make moves of its own: 22
copies of 20 moves in the circuit of the second result (cst = 440 moves per invocation), 15 copies of 15 moves
and one of 16 in my circuit of the first (cst = 241). These moves buy nothing. In the five-stage word the number of moves
saved per unit is D = 4v - 5 cst: the exchanges could save 4v, and the copies of the five invocations take
5 cst of it back.

**What they cost.** Between two fifths and a half of the saving this design could reach is eaten by the
scratch copies that every run of the helper circuit needs. A what-if computation says that removing them
entirely would raise the second result by a factor 1.71 and would roughly double the first:

| circuit | 4v | 5 cst | share eaten | saving proved | WHAT-IF: no copies |
|---|---|---|---|---|---|
| second result (community circuit, h = 22) | 5280 | 2200 | 41.7 % | 7.474547e-4 | 1.28147e-3 (x1.71) |
| first result (my circuit, h = 16) | 2240 | 1205 | 53.8 % | 5.399225e-4 | 1.16867e-3 (x2.16) |

The last column is a what-if and not a result. It is the block list of the same network with the copy blocks
and their loss deleted and everything else unchanged, priced by the rate calculator (whole-block accounting,
eight decimals, truncated; the same calculator gives 7.4745e-4 and 5.3992e-4 for the two networks as they
are). No circuit is known that reaches it. `python3 tools/whatif_copies.py tools/certificate/gcert1-p11-pr193.json.gz tools/certificate/c2-combine-best-h16.json` recomputes both rows.

**What is known.**

- One unit of copy rank costs 5 units of D. In the first network that is 0.48 percent of the saving per unit,
  as much as 41 helper arrays.
- Small steps exist. Retaining a different total in my circuit brings cst from 241 to 240 (worth 151 units of
  10^-8; found by the agents, not in Lean). The community's star rule, h copies of h - 2 moves, is already
  below the (h-1)^2 + h of my circuit.
- An earlier round of this project settled one class negatively. If the copies move along coordinate
  directions and are read only by the outputs, every identity over triples (the kind my circuit uses) needs cst
  of at least h(h-3), and the identity of my circuit needs at least h(h-1). Even the floor h(h-3) would give at
  most a factor 1.25 at h = 16 (computed for the three-stage word). Halving the loss is excluded in that class.
  This is a derivation on paper with computer checks at small sizes, and one step quotes an outside theorem.
  It is not a Lean theorem.
- That finding predates the general frame lemma in this repository. The copies may now stand at any subspace,
  degenerate ones included. What that allows for the copies has not been examined in this project.

No design for that is known yet. If you find one, the checker and pipeline in this repository will take it as
data: a circuit in the certificate format of section 5 is a data file. The note `notes/scratch-copies.md` has the
formulas and says where each of the four points above comes from.

### The other open directions

I expect to leave this project alone for a while, so [notes/open-directions.md](notes/open-directions.md) hands
it on: every lead I know of, with what is known, what it might give, how to start, and what already failed.

- **Major leads.** The scratch copies above (what-if 1.28147e-3, no design known); a per-rank theorem for the
  generalised engine (its rate inequality at 4.058344e-4 is a Lean lemma already); the room under the
  outside ceilings (#201, DaysSky, claims 2.5657e-3 and covers neither this circuit nor this layout); the
  Lean frame lemma and the checker, for what the multiplication project still assumes. The Fourier transform
  of every length was on this list and is now the third result; the note says what remains of it (A3).
- **Minor leads** (fourteen, each with its computed size and its label), **the checks I would welcome most**,
  **seventeen things that were tried and did not work**, and **how a better circuit becomes a theorem here**.

## 8. Layout

    OAI/          89 files of openai/math (lean/OAI/Computability), unmodified
    WHTCheck/     the first Walsh-Hadamard corollary; defines `wht` and `WHTProgram`
    Work/         252 modules: 237 written here for the first two results, and Work/Fourier.
                  First result: recursion engines and rate arithmetic (Scratch, Block*, FoldRate), invocation
                  and network theorems (SharedSumStructured, Combine, Reframe, Bridge, BridgeGeom, Carrier),
                  certificate checkers, data and final theorems (SharedSumChecker, CarrierCheck).
                  Second result: GFrame (frame lemma, generalised engine, 54 modules, 48 of them imported
                  by the final proof), GCert (extended checker in the parts Labels, Scalar and Chain; Data
                  with the certificate and the final theorem)
                  Third result: Fourier (15 modules: the seam file written here, the modified
                  copies of 11 OpenAI files and of five definitions of a twelfth, the challenge, and a file that prints the axioms of the final theorems;
                  the final theorems are in the copy of `Main`)
    comparator/   the comparator configurations
    tools/        `Compare.lean`, the certificates as JSON (`tools/certificate/`), their reference checkers,
                  the generators (`tools/gen/` first result, `tools/gx/` second), `whatif_copies.py` (section 7),
                  `tools/fourier/` (the script that made the copies of the third result, and its check)
    lakefile.lean, lean-toolchain, lake-manifest.json    Lean v4.34.1 and the Mathlib commit pinned by openai/math
    VERIFY.md     how to rebuild everything and re-run every check
    ORIGIN.md     where every file comes from (with MANIFEST.sha256); `tools/gx/ORIGIN.md` for the tools and
                  the certificate of the second result
    RELATED-WORK.md, NOTICE, LICENSE
    notes/, third-party/    the notes of section 7 (scratch copies; all open directions); the NOTICE file of CrocSwap/integer-mult-bounds (NOTICE, section 6);
                  OpenAI's challenge file `UniformFourier.lean`, unmodified, to compare the challenge of the third result with

The comments inside the Lean files were not edited for this release, so that the files are byte for byte the
ones that were checked. They still use path names and working titles of the tree they were written in ("Scratch
file", `checks/...`, "(key: ...)"). ORIGIN.md translates them.
