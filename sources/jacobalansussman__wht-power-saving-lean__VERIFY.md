# How to rebuild this repository and re-run the checks

The AI agents I directed ran everything below on one machine, on 2026-10-09: Apple M4 (10 cores, 16 GB
memory), macOS 26.6.2, the copy on an external SSD. What was run and what was not is said in each section; the
section "Limits" at the end collects the caveats. Linux commands are given where they differ; **none of these
runs was on Linux.** Section 9 keeps the measurements of the first publication (2026-10-09, 194 modules).

**State of the checks of the second result when this text was written.** The theorem passed the official
comparator three times (section 5) and `tools/Compare.lean` twice (section 4): in the project's working tree, on
Lean files that are byte for byte those of this repository, and then in a copy of the repository built with the
`lakefile.lean` of this repository, partly from compiled files of the working build (section 3). A build of this
revision from nothing has not been made (section 8, point 12).

**State of the checks of the third result.** Both theorems passed the official comparator three times
(section 5): twice in the project's working tree (18:27 and 18:55 UTC) and once in a copy of the repository
(19:20 UTC), on Lean files that are byte for byte those of this repository. `tools/Compare.lean` passed in the
working tree and in the copy (19:23 UTC). No build of this revision from nothing has been made (section 8,
point 13).

## 1. What is checked

| theorem (namespace `OAI.PowerSaving.WHT` unless written out) | statement | challenge module | solution module | comparator config |
|---|---|---|---|---|
| `OAI.PowerSaving.transform_mainZ` and `OAI.PowerSaving.convolution_mainZ` (third result) | `DFTGoalZ` and `ConvGoalZ`: OpenAI's `DFTGoal` and `ConvGoal` with `decimalExponentZ := 1 - 7474546/(10^(10:ℕ))` | `Work.Fourier.UniformFourierChallenge` | `Work.Fourier.Main` | `comparator/UniformFourier.json` |
| `wht_main_block_B2Gp193x` (second result) | `∃ solve W, WHTProgram solve W ∧ WHTTimeBoundsAt (1 - 7474547/(10:ℝ)^10) W` | `Work.GCert.Data.ChallengeB2Gp193x` | `Work.GCert.Data.SolutionB2Gp193x` | `comparator/B2Gp193x.json` |
| `wht_main_block_B2Ke16x` (first result) | the same with `1 - 5399225/(10:ℝ)^10` | `Work.CarrierCheck.ChallengeB2Ke16x` | `Work.CarrierCheck.SolutionB2Ke16x` | `comparator/B2Ke16x.json` |
| `wht_main_rank_B2Ke16x` (first result, per-rank) | the same with `1 - 3155781/(10:ℝ)^10` | `Work.CarrierCheck.ChallengeB2Ke16xR` | `Work.CarrierCheck.SolutionB2Ke16xR` | `comparator/B2Ke16xR.json` |

A challenge module states the theorem with `sorry` and imports only Mathlib: it is the text to read to see what
is claimed (331 lines; the cost model, `wht`, `WHTProgram`, `WHTTimeBoundsAt`). The three
Walsh-Hadamard challenge modules differ in the exponent, in the name of the theorem and in the comments that quote the two
and the module names, and in nothing else. A solution module proves a theorem of the same name. Two tools compare the two:

* **comparator** (github.com/leanprover/comparator): the solution proves the same statement as the challenge, uses
  only the permitted axioms `propext`, `Quot.sound`, `Classical.choice`, and is accepted by the Lean kernel.
* **`tools/Compare.lean`** (this repository, about 220 lines): an independent second check of "same statement
  as a kernel term, every definition the statement depends on identical, permitted axioms only".

The challenge module of the third result (348 lines) is OpenAI's challenge file with three
changes, which its first comment lists: that comment, the exponent, and the suffix `Z` on seven names. To see
them (the first file is OpenAI's, unchanged; ORIGIN.md, last section, says how to compare it with a checkout
of openai/math):

    diff third-party/openai-math/lean/ComparatorChallenges/UniformFourier.lean Work/Fourier/UniformFourierChallenge.lean

Expected: 9 hunks. One block of 12 added lines after line 2 (an empty line and the comment), and 8 changed
lines, OpenAI's lines 269, 274, 317, 319, 321, 323, 326 and 330: the exponent, and the seven names where they
are defined or used. So 20 lines are marked `>` and 8 are marked `<`, and nothing else differs.

## 2. What you need

* Linux or macOS, `git`, `curl`, and `elan` (the Lean version manager, github.com/leanprover/elan). The file
  `lean-toolchain` selects Lean v4.34.1; `lakefile.lean` pins Mathlib at `d13f23b723b8a846827a245b89c10fc7d3f11612`.
* Disk: about 10.2 GB. Measured: `.lake/packages` 7.6 GB (Mathlib and its dependencies with compiled files),
  `.lake/build` 2.0 GB (this repository), Mathlib's download cache 0.45 GB (in `~/.cache/mathlib` unless
  `MATHLIB_CACHE_DIR` is set; the agents set it to an empty directory).
* Memory: 16 GB was enough here when the modules that load a certificate are built one at a time (as below).
  Largest resident size of one process measured here: 7.0 GB (in the project's working tree) for a Lean process during the build,
  7.2 GB for `tools/Compare.lean`, 9.6 GB during a comparator run. These figures include
  the mapped Mathlib files. Less than 16 GB was not tried.
* Python 3 (standard library only) for section 6; the agents used Python 3.9.6.
* For section 5: the comparator and its helper programs, see there.

## 3. Rebuild

    lake exe cache get

downloads the compiled Mathlib files for the pinned revision (Lake first clones Mathlib and its 8 dependencies).
Measured at the first publication: 59 s, 8908 files, exit code 0. Then, on a 16 GB machine, first the modules
that load no certificate:

    LEAN_NUM_THREADS=4 lake build Work.CarrierCheck.B2 Work.CarrierCheck.RateB2Ke16 Work.CarrierCheck.RateB2Ke16x \
        Work.FoldRate.SharpTools Work.CarrierCheck.ChallengeB2Ke16x Work.CarrierCheck.ChallengeB2Ke16xR \
        Work.GFrame.Top.All Work.GCert.Chain.End Work.GCert.Scalar.Main Work.GCert.Data.Glue \
        Work.GCert.Data.Price Work.GCert.Data.InstB2Gp193 Work.GCert.Data.ChallengeB2Gp193x

and then the modules that load a certificate, one at a time, so that two kernel checks of a certificate never
run together:

    for m in CarrierCheck.Gen.Cr2h16 CarrierCheck.Gen.Cr2h16Hist CarrierCheck.Gen.Cr2h16Lab \
             CarrierCheck.Gen.Cr2h16Scal CarrierCheck.Gen.Cr2h16Shape CarrierCheck.Cr2h16Cert \
             CarrierCheck.InstB2Ke16 CarrierCheck.B2Ke16 CarrierCheck.SolutionB2Ke16x \
             CarrierCheck.SolutionB2Ke16xR GFrame.Top.Regress \
             GCert.Data.Gen.P193.S0 GCert.Data.Gen.P193.S1 GCert.Data.Gen.P193.S2 GCert.Data.Gen.P193.S3 \
             GCert.Data.Gen.P193.S4 GCert.Data.Gen.P193.S5 GCert.Data.Gen.P193.S6 GCert.Data.Gen.P193.S7 \
             GCert.Data.Gen.P193 GCert.Data.Gen.P193Par \
             GCert.Data.Gen.P193Tab0 GCert.Data.Gen.P193Tab1 GCert.Data.Gen.P193Tab2 GCert.Data.Gen.P193Tab3 \
             GCert.Data.Gen.P193Seg0 GCert.Data.Gen.P193Seg1 GCert.Data.Gen.P193Seg2 GCert.Data.Gen.P193Seg3 \
             GCert.Data.Gen.P193Seg4 GCert.Data.Gen.P193SegF GCert.Data.Gen.P193End GCert.Data.Gen.P193Hist \
             GCert.Data.Gen.P193YChk GCert.Data.Gen.P193Scal0 GCert.Data.Gen.P193Scal1 \
             GCert.Data.P193Price GCert.Data.P193Cert GCert.Data.P193ScalOK \
             GCert.Data.B2Gp193 GCert.Data.B2Gp193Main GCert.Data.SolutionB2Gp193x; do
      lake build Work.$m || break
    done

The first command builds 285 modules (89 from openai/math, the others of this project, the three
challenge modules among them); the loop builds the other 42. Every `lake build` must end with
`Build completed successfully`, and no line may start with `error`. The build prints many linter warnings
(deprecated lemma names, unused `simp` arguments); they do not touch correctness. The warning "declaration uses
`sorry`" must appear for the three challenge modules and for no other module (a challenge states its theorem
with `sorry` on purpose). The builds of the three solution modules print

    'OAI.PowerSaving.WHT.wht_main_block_B2Gp193x' depends on axioms: [propext, Classical.choice, Quot.sound]
    'OAI.PowerSaving.WHT.wht_main_block_B2Ke16x' depends on axioms: [propext, Classical.choice, Quot.sound]
    'OAI.PowerSaving.WHT.wht_main_rank_B2Ke16x' depends on axioms: [propext, Classical.choice, Quot.sound]

Measured (327 modules; "declaration uses `sorry`" for the three challenge modules only). The commands
above were not run in this form for this revision: each row says where and how its part was built.

| part | time | largest resident size of one Lean process |
|---|---|---|
| the 285 modules that load no certificate | 184 of them at the first publication: 403 s (section 9). The 101 new ones, compiled from source in the copy: 470 s for 90 of them (nine `lake build` calls of ten modules), 8 to 169 s per call for the other 11 in separate calls; a later change of one source file recompiled it and what imports it (71 s) | 5.8 GB (section 9); 5.7 GB for the new ones |
| the 10 certificate modules of the first result | section 9 (first publication; not rebuilt for this revision) | section 9 |
| `Work.GFrame.Top.Regress` (the first result once more, through the generalised engine; loads the first certificate), compiled from source in the copy | 220 s | not sampled |
| `Gen.P193.S0` to `S7`, `Gen.P193`, `Gen.P193Par` (the data of the second certificate, 7.5 MB of Lean text). This row and the next five: measured in the project's working tree, one module per `lake build`; in the copy the compiled files were cloned (below) | 72 s for the eight data modules | 1.9 GB |
| `Gen.P193Tab0` to `Tab3` (frame table, 4 evaluations) | 39 to 54 s each | 0.74 GB |
| `Gen.P193Seg0` to `Seg4` (replay of the gates, 5 evaluations) | 6, 17, 55, 156 and 186 s | up to 3.8 GB |
| `Gen.P193SegF`, `Gen.P193End`, `Gen.P193YChk` | 10 s, 9 s, 2 s | up to 1.7 GB |
| `Gen.P193Hist` (63 block counts) | 54 s | 1.2 GB |
| `Gen.P193Scal0`, `Gen.P193Scal1` (scalar replay, 660 sources each) | 122 to 180 s each | 7.0 GB each |
| `P193Price`, `P193Cert`, `P193ScalOK`, `B2Gp193`, `B2Gp193Main`, `SolutionB2Gp193x` | working tree: 5, 5, 24, 8, 42 and 10 s. In the copy, from source, in one `lake build` with `LEAN_NUM_THREADS=3`: 276 s | not sampled in the copy |
| **whole build** | **not run as one build for this revision** | |

**How the copy of this revision was built.** It was not built from nothing. It started from the compiled files
of the first publication's rebuild from scratch (section 9: Mathlib from its cache, the 194 published modules
compiled from source), cloned into a new copy that holds the files of this revision. Then, in the copy, the 101
new modules that load no certificate and `Work.GFrame.Top.Regress` were compiled from source (table). For the 31
modules that load the certificate of the second result the fast path was used: their compiled files were cloned
from the project's working build (same source bytes), and a `lake build` of the eight roots accepted the 25
modules under `Work/GCert/Data/Gen/` by their traces ("Replayed") and compiled the 6 modules above them from
source. Finally `lake build --no-build` of the eight roots (the four published ones, `Work.GFrame.Top.All`,
`Work.GFrame.Top.Regress`, the new challenge and the new solution) reported "All targets up-to-date (9250 jobs)"
at 15:48, exit code 0, no line starting with `error`, with the axiom lines above. The times of the certificate
modules in the table are therefore those of the working tree, where the agent that built the proof compiled each
of them from source. A build of the whole revision from nothing, with the commands above, has not been made. The
runs of sections 4 and 5 in this copy came after these steps.

The certificate of the second result is checked by the kernel in segments (`Work/GCert/Data/Gen/`, one
module for each large evaluation):
13 evaluations for the label half (4 for the frame table, 5 for the replay of the gates and 1 for its final
segment, 3 for the end conditions and the frames of the copies; two of the last three are in `P193Cert`), 3 for
the scalar half (2 for the replay, 660 sources each, and 1 for the outputs), and 63 block counts in
`Gen.P193Hist`.
One of these modules needs up to 7.0 GB and about 3 minutes (table). Build them one at a time.

`lake build` without a module name builds nothing: `lakefile.lean` declares no default target. (With one, a
plain `lake build` would start several kernel checks of a certificate at the same time.) Always name the
modules, as above.

**Third result.** The modules of `Work/Fourier` hold no certificate data and make no kernel evaluation of a
certificate. They import the final module of the second result, so they are built after the loop above:

    lake build Work.Fourier.UniformFourierChallenge Work.Fourier.Main Work.Fourier.Axioms

The warning "declaration uses `sorry`" then appears for a fourth module, the challenge
`Work.Fourier.UniformFourierChallenge`. The build of `Work.Fourier.Axioms` prints, among other lines:

    'OAI.PowerSaving.transform_mainZ' depends on axioms: [propext, Classical.choice, Quot.sound]
    'OAI.PowerSaving.convolution_mainZ' depends on axioms: [propext, Classical.choice, Quot.sound]
    'OAI.PowerSaving.RAM.hillsZ_program' depends on axioms: [propext, Classical.choice, Quot.sound]

Measured in the project's working tree, on the compiled modules of the second result: `Work.Fourier.Seam` 35 s;
the other 14 modules in one `lake build`, 58 s (9238 jobs, exit code 0). Memory was not sampled.

## 4. Check with `tools/Compare.lean`

    lake env lean --run tools/Compare.lean Work.GCert.Data.ChallengeB2Gp193x \
        Work.GCert.Data.SolutionB2Gp193x OAI.PowerSaving.WHT.wht_main_block_B2Gp193x
    lake env lean --run tools/Compare.lean Work.CarrierCheck.ChallengeB2Ke16x \
        Work.CarrierCheck.SolutionB2Ke16x OAI.PowerSaving.WHT.wht_main_block_B2Ke16x
    lake env lean --run tools/Compare.lean Work.CarrierCheck.ChallengeB2Ke16xR \
        Work.CarrierCheck.SolutionB2Ke16xR OAI.PowerSaving.WHT.wht_main_rank_B2Ke16x

Expected last lines (exit code 0); the first run says `38678 constants`, the second `36438 constants`,
the third `33452 constants`:

    OK: every statement dependency is identical in the solution
    solution proof reaches 38678 constants; axioms: #[Classical.choice, Quot.sound, propext]
    OK: only permitted axioms

    RESULT: PASS

Measured: for the second result `RESULT: PASS`, exit code 0, twice: 227 s, 4.3 GB by an auditing agent in the
project's working tree (15:43 to 15:47), and 148 s, 7.2 GB in the build copy (16:13 to 16:15). The two runs for
the first result were not repeated for this revision (section 9).

**Third result.** `tools/Compare.lean` takes both theorems in one run:

    lake env lean --run tools/Compare.lean Work.Fourier.UniformFourierChallenge \
        Work.Fourier.Main OAI.PowerSaving.transform_mainZ OAI.PowerSaving.convolution_mainZ

It passed for the third result in the project's working tree and, at 19:23 UTC, in a copy of the repository (163 s).

## 5. Check with the official comparator

The comparator needs three programs on `PATH`: `comparator` itself (github.com/leanprover/comparator),
`lean4export` (github.com/leanprover/lean4export) built for the Lean version of this repository, and the Linux
sandbox `landrun` (github.com/Zouuup/landrun). Its README says how to install them and under which assumptions
its verdict can be trusted. Used here: comparator at commit `d03acab154d269c06e60e4de7e4cc85deebff94b`,
lean4export at `076e8e57707e813375e8f9da8bf989799ace9680`, in both checkouts `lean-toolchain` changed from
v4.34.0 to v4.34.1 (the Lean version of this repository) and nothing else.

    lake env comparator comparator/UniformFourier.json
    lake env comparator comparator/B2Gp193x.json
    lake env comparator comparator/B2Ke16x.json
    lake env comparator comparator/B2Ke16xR.json

On Linux the comparator's README recommends to run it as

    systemd-run --property=RestrictAddressFamilies=~AF_UNIX --user --pty -E PATH="$PATH" \
        --working-directory $(pwd) -- bash -c 'lake env comparator comparator/B2Gp193x.json'

Expected last lines of each run, exit code 0:

    Running Lean default kernel on solution.
    Lean default kernel accepts the solution
    Your solution is okay!

The comparator starts with `lake build` of the challenge and of the solution inside the sandbox. After section 3
nothing is left to build, so it only replays and then exports and re-checks the proof in the kernel.

**macOS.** `landrun` does not exist for macOS. The agents ran the comparator with `tools/landrun-macos-shim.sh`
installed under the name `landrun` in a directory on `PATH` (it translates the sandbox request into a
`sandbox-exec` profile: no network, writes only where the comparator allows them, in the system's temporary
directories and in `/dev`). For example:

    mkdir -p "$HOME/landrun-shim" && cp tools/landrun-macos-shim.sh "$HOME/landrun-shim/landrun"
    chmod +x "$HOME/landrun-shim/landrun" && export PATH="$HOME/landrun-shim:$PATH"

Measured (macOS, the stand-in above, `enable_nanoda` false; each row says where the run was made):

| config | verdict lines | exit | time | largest resident size |
|---|---|---|---|---|
| `comparator/UniformFourier.json` (third result, both theorems), in the working tree, by the agent that built the proof, ended 18:27 | "Lean default kernel accepts the solution" / "Your solution is okay!" | 0 | 1528 s | 9.0 GB (9,660,301,312 bytes, the largest process as `time -l` reports it) |
| `comparator/B2Gp193x.json`, in the working tree, by the agent that built the proof, ended 15:14 | "Lean default kernel accepts the solution" / "Your solution is okay!" | 0 | 1814 s | 9.1 GB |
| the same, in the working tree, by an auditing agent with its own copy of the configuration, 15:25 to 15:43 | the same two lines | 0 | 1116 s | 9.4 GB (all Lean processes together) |
| the same, in the build copy of this repository, 15:55 to 16:13 (every module replayed, none built) | the same two lines | 0 | 1058 s | 9.6 GB |
| `comparator/B2Ke16x.json`, `comparator/B2Ke16xR.json` | not re-run for this revision; section 9 | | | |

## 6. Regenerate the generated files (no Lean needed)

    python3 tools/regen_check.py
    python3 tools/gx/regen_check.py

run the generators into a temporary directory and compare the result with the files of this repository. The
first covers the first result (certificate `tools/certificate/c2-combine-best-h16.json`), the second the second
result (certificate `tools/certificate/gcert1-p11-pr193.json.gz`). Expected last lines, exit code 0:

    RESULT: REPRODUCED (16 of 16 repository files reproduced byte for byte)
    RESULT: REPRODUCED (36 repository files reproduced byte for byte, 0 different, 3 generated files not in the repository)

Both lines were obtained on the files of this revision (15:22, and again at 16:11). The three generated files
that are not in the repository are the eight-decimal variant of the second result (`ChallengeB2Gp193`,
`SolutionB2Gp193` and its comparator configuration). It compiles in the working tree and has not been put
through the comparator, so it is not published.

For the third result, the copies of OpenAI's files under `Work/Fourier/`:

    python3 tools/fourier/regen_check.py

makes the 11 copies, `Goal.lean`, the challenge and the comparator configuration again, in a temporary
directory, from the unmodified files under `OAI/` and `third-party/openai-math/`, and compares them with the
files of this repository. It needs Python 3 and no Lean. Expected last line, exit code 0:

    RESULT: REPRODUCED (14 repository files reproduced byte for byte, 0 different, 0 generated files not in the repository)

Reference checkers of the two certificates, written without Lean:

    python3 -I -B tools/ccheck.py tools/certificate/c2-combine-best-h16.json general
    python3 -I -B tools/ccheck.py tools/certificate/c2-combine-best-h16.json lpc
    python3 -B tools/gx/refcheck.py tools/certificate/gcert1-p11-pr193.json.gz

Expected first lines `ACCEPTED (general): ...`, `ACCEPTED (lpc): ...` and `ACCEPTED by gx.check1: h=22 v=1320 R=9412 N=262944 gates A=12158 B=30878; ...`
(17 to 19 s here; this script needs its own directory on the module path, so it is run without `-I`, and
it creates the empty directory `tools/gx/out/`, which git ignores).

    python3 tools/whatif_copies.py tools/certificate/gcert1-p11-pr193.json.gz tools/certificate/c2-combine-best-h16.json

recomputes the what-if of the README, section 7. It is a what-if and no part of any proof.

None of the Python is part of the proof. The theorems rest on the Lean data modules, which the Lean kernel
checks; the scripts only show where those modules come from. **Where the chain starts:** for the second result
the repository starts from the rebuilt certificate `tools/certificate/gcert1-p11-pr193.json.gz`.
The programs that rebuilt the circuit from the community's files are not in this repository;
`tools/gx/ORIGIN.md` names the outside files and commits they read. The last step, the conversion to the
certificate format, is `tools/gx/gxconv.py`.

## 7. File integrity

    shasum -a 256 -c MANIFEST.sha256        # Linux: sha256sum -c MANIFEST.sha256

`MANIFEST.sha256` lists every file of the repository except itself.

## 8. Limits

Read these before relying on the result.

1. **The sandbox on macOS was a stand-in.** The comparator runs the build inside `landrun` (Linux Landlock).
   Here it ran inside `tools/landrun-macos-shim.sh`, which forbids network access and writes outside the allowed
   directories but, unlike `landrun`, does not restrict what can be read. The sandbox protects the checker
   against a solution file that attacks the build; it is not part of the logical check. None of the comparator
   runs here was on Linux.
2. **One kernel only.** Every configuration has `"enable_nanoda": false`: the proof was checked by Lean's own
   kernel (when the modules were compiled, and again by the comparator on the exported proof), not by a second,
   independent kernel. `leanchecker` was not run either. A re-run with `"enable_nanoda": true` is welcome.
3. **The comparator replayed files that were already compiled.** Section 3 compiles the solution modules before
   the comparator runs, outside its sandbox. The comparator's README lists as an assumption that the solution
   was not compiled before. To meet it, run section 5 directly after `lake exe cache get`: the comparator then
   builds every module itself. It was not run in that order here; it compiles several kernel checks of a
   certificate at the same time and may need more than 16 GB.
4. **Mathlib was not rebuilt from source.** Its compiled files came from Mathlib's cache server for the pinned
   revision (`lake exe cache get`), as is usual.
5. **Not fetched fresh for this test:** the Lean toolchain v4.34.1 and the `comparator` and `lean4export`
   programs were already installed on the machine. For this revision nothing was fetched: the copy started from
   the packages and compiled files of the first publication's rebuild, for which Lake had cloned Mathlib and its
   dependencies and downloaded the compiled Mathlib files into an empty directory.
6. **One machine.** Every run was on the machine named at the top.
   Each step was run once, except the comparator on the second result (twice in the working tree, by the agent
   that built the proof and by an auditing agent, and once in the copy) and `tools/Compare.lean` on it (once in
   the working tree, once in the copy). The negative control (a challenge whose saving is one unit larger, which
   must be rejected) was run once, by the auditing agent in the working tree: the comparator and
   `tools/Compare.lean` both rejected it. It was not repeated in the copy.
   Times and memory are single measurements; "resident size" is what `ps` reports once a second and includes
   mapped files.
7. **Files added after the build.** The documentation files (`README.md`, `RELATED-WORK.md`, `NOTICE`,
   `ORIGIN.md`, this file), `tools/whatif_copies.py`, `notes/` and `third-party/` were added or edited after the
   builds and the checks; Lean does not read them. After the last edit all 327 `.lean` files, `lean-toolchain`,
   `lake-manifest.json` and `comparator/B2Gp193x.json` of this repository were compared byte for byte with the
   files of the working tree in which the comparator and `tools/Compare.lean` passed: all identical.
   `lakefile.lean` is the one of the first publication; the working tree has its own, and the copy was built
   with the published one. The build copy was compared with this repository after its comparator run: the same
   `.lean` files, `lakefile.lean`, `lean-toolchain`, `lake-manifest.json`, `comparator/` and `tools/` (without
   `tools/whatif_copies.py`).
8. **What the checks do not say.** They say that the solution proves the statement written in the challenge
   module. Whether that statement means what a reader expects has to be judged by reading the challenge module:
   the cost model in it is OpenAI's, the definitions `wht`, `WHTProgram`, `WHTTimeBoundsAt` are my project's.
   For the third result the whole challenge module is OpenAI's, with the three changes named in section 1.
   The checks say nothing about the speed of any program on inputs of realistic size.
9. **`tools/Compare.lean` is my project's own tool.** It is a second opinion written independently of the
   comparator, not an independent party. The comparator is the outside tool.
10. **The segmented kernel check is new.** The certificate of the second result does not fit into one kernel
    evaluation on this machine. It is cut into segments by a Python generator, each segment is one kernel
    evaluation, and Lean theorems join them. The joining is proved in Lean. The cut is data and is not trusted.
11. **The circuit of the second result is outside data, rebuilt.** The kernel checks the rebuilt certificate as
    it is. That it is the circuit of pull request #193 rests on a Python conversion and on equal counts, not on
    Lean (README, section 3).
12. **The copy of this revision was not built from nothing.**
    It started from the compiled files of the first publication's rebuild, and for the 25 certificate modules of
    the second result it took compiled files of the project's working build, which Lake accepted by their traces
    (section 3). So for the second result no build from nothing has been made; the comparator pass in this copy
    (section 5) replayed compiled files of that origin. A rebuild from nothing with the commands of section 3,
    followed by sections 4 and 5, closes this gap; re-runs are welcome.

13. **The third result.** The comparator passed three times: twice in the project's working tree and once in a
    copy of the repository, where the 15 new modules had been compiled from source. Every run replayed compiled
    files, those of the certificate of the second result among them (point 12). `tools/Compare.lean` passed in
    both places; the negative control was run in the working tree. No build from nothing has been made. A
    rebuild from nothing with the commands of section 3, followed by sections 4 and 5, closes this gap;
    re-runs are welcome.

## 9. Measurements of the first publication (2026-10-09, 194 modules)

Kept as a record; the commands were those of the first text of this file (commit `024f763`).

| part | time | largest resident size of one Lean process |
|---|---|---|
| the 184 modules that load no certificate (16 `lake build` calls of 12 modules each, `LEAN_NUM_THREADS=4`) | 403 s | 5.8 GB |
| `Gen.Cr2h16` (the data, 3.9 MB of Lean text) | 30 s | 2.3 GB |
| `Gen.Cr2h16Hist` (43 block counts, `decide +kernel`) | 50 s | 0.9 GB |
| `Gen.Cr2h16Lab` (`labelCheck_ok`) | 17 s | 4.5 GB |
| `Gen.Cr2h16Scal` (`scalarCheck_ok`) | 38 s | 5.4 GB |
| `Gen.Cr2h16Shape` (`shapeCheck_ok`) | 9 s | 3.1 GB |
| `Cr2h16Cert` | 63 s | 5.7 GB |
| `InstB2Ke16`, `B2Ke16`, `SolutionB2Ke16x`, `SolutionB2Ke16xR` | 8 to 9 s each | 5.3 to 5.5 GB |
| **whole build** | **644 s (about 11 minutes)** | |

`tools/Compare.lean`: both `RESULT: PASS`, exit code 0, 140 s and 117 s; a repeat of the first with a memory
sampler: 144 s, 6.2 GB. Comparator (macOS, the stand-in, `enable_nanoda` false): `comparator/B2Ke16x.json`
171 s, 6.3 GB; `comparator/B2Ke16xR.json` 178 s, 6.2 GB; both "Lean default kernel accepts the solution" /
"Your solution is okay!", exit 0. Disk then: `.lake/build` 1.3 GB, about 9.5 GB in all.
