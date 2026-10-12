# Big O Speedrun data

Checked 2026-10-08. Local static source bundle. See [NOTES.md](NOTES.md) for source links, tier limits, date rules, and open questions.

Read `registry.json`, then each `problems[].data_file`. Use each record's exact rational `score`, its `tier`, and `record_metadata[id]`. `eligible_for_record` governs record-holder labels. No site proof badge is available. Keep separate assumption tracks separate.

Run:

```sh
python3 validate.py
```

The installed `jsonschema` package is required. [validation-summary.txt](validation-summary.txt) has the dated result.

`submissions.json` preserves all observed CrocSwap PRs, including nonnumeric work. `chart-cross-check.json` records the earlier 42-point chart comparison. `sources/` retains evidence and source notices. `manifests/` contains the read-only listing manifests. `schemas/` contains the design schemas and data-wrapper schemas.

## Scheduled source refresh

Added 2026-10-09. `python3 refresh.py` reads both integer-multiplication repos
with `gh api --method GET`. It never runs their code. The current GitHub CLI
login needs read access. The script resolves each default branch to a commit,
fetches the README and selected record/certificate, and reads all CrocSwap PRs.
It keeps reviewed main-branch checkpoints separate from PR merge status.
Unknown headline formats remain unscored submissions for review. Swapnil stays
on its separate comparison track. Source checks do not grant a proof badge.

The script locks against overlapping refreshes, validates a staging copy, checks
for concurrent edits, and replaces changed files only after validation. It stops
on API, format, certificate hash, or validation errors. A source fingerprint
makes an unchanged snapshot a no-op. The JSON diff summary is printed and saved
in `.git/refresh-summary.json`. `build_data.py` is the historical snapshot builder;
do not use it for scheduled refreshes.

`python3 pivot_watch.py` searches a rolling 72-hour window by creation and push
time, plus all-time CrocSwap forks and README citations. It fetches the OpenAI
preprint directory each time and searches the algorithmic problem families found
there. The ranked results, timestamps, stars, query coverage, errors, and source
signals are in `pivot-watch.json`. These are discovery guesses, not verified new
races. GitHub search indexes can lag; capped queries are listed explicitly.

The active three-hour watch follows [WATCH_RUNBOOK.md](WATCH_RUNBOOK.md).
It runs the people and pivot watches, checks site refresh health, and commits
only watch reports. The scheduler supplies the checkout directory and local
notification routing; no previous Git commits are needed. `poll.py` is a legacy
adapter and must not run alongside the cronjob. Its local routing configuration
is `.git/watch-office.json`; this file contains no credential values.

Offline checks: `python3 -m unittest test_refresh.py` and `python3 validate.py`.

Production uses `bigospeedrun/site`, with this bundle tracked under `data/`.
Run `python3 data/refresh.py` and `python3 data/validate.py` from that checkout.
The refresh finds the containing Git repository and keeps its lock, staging
files, and summary in that repository's Git directory. It checks edits only
inside the data folder. The validator checks receipt paths within the bundle;
historical provenance paths are not opened. `poll.py` is not needed in GitHub Actions.

`registry.updated_at` and each problem's `updated_at` are required UTC date-times
ending in `Z`. They record the last normalized data update, not a proof check
or a fresh check of every source. An unchanged refresh preserves these fields.
The integer-multiplication refresh updates that problem and the registry only.
Other problems retain their own update times. The initial timestamp migration
uses the retained intake time for integer multiplication and the last data
commit time for the other problem files.

Exact DFT research entries were added on 2026-10-09. `score_relation` is optional:
absent or `attained` means the scored value; `strict-upper-bound` means every
fixed saving below the stored endpoint. Render the latter with `<`, including
in tier summaries. The endpoint itself is not an attained pure-log saving.
OpenAI's verified frontier comes from its smaller Lean tensor network and the
polylog absorption lemmas, while its selected Comparator headline is 10^-13.
The rerun remains pending. The two community drafts are claimed, with separate
source tracks, credited notes and their exact model statements. They are not
open submission races. Shea's unlicensed manuscript is linked; the bundle keeps
a derived evidence summary and source hashes.

`pivot-watchlist.json` names repos that every watch run checks directly, even
when search indexing or the 72-hour window omits them. `watched_repositories`
in the report records pinned heads and detects new commits. The scheduled watch reviews
new heads for likely pivots. `python3 pivot_watch.py --watch-only` checks those
heads and rechecks retained candidates without repeating the broad search.
A new head triggers review; it does not silently replace a mathematical claim.

The three-hour watch runs `python3 people_watch.py`. Its configuration
is `people-watchlist.json`; `people-watch.json` stores checked identities, seen
public event IDs, ranked leads, and coverage warnings. Named people and the ten
most active CrocSwap PR authors are checked each run. The first run covers the
last 72 hours; later runs deduplicate IDs. New repos and forks, pushes outside
the registry/direct watch list, and newly opened bound PRs are leads only.
Profile/README evidence identifies GitHub accounts. X handles supplied by Nil
remain separate from confirmed profile links. This watch does not access X or
change mathematical records automatically.

X watching is disabled in the scheduled watch. The optional `x_watch.py`
reads `x-watchlist.local.json`, an ignored local file. Start from
`x-watchlist.example.json`, which has an empty accounts list, if a separate
operator authorizes X access. The script uses only `tabs`, `goto`, and `text`;
it restores the original URL and keeps a local restoration journal.

Private state and reports are in the containing Git directory as
`x-watch-state.json` and `x-watch-report.json`; they are not site data. The watch
reads at most 12 rendered posts per profile. Text-only reads cannot expose
hidden URLs, exact hidden timestamps, or unloaded posts. The watch retains
visible full links, time text and date ranges; it marks uncertain newness rather
than inventing an exact timestamp. It preserves the last complete check time when a profile read is partial or no
posts are readable. A missing article ends that profile read and the watch
continues with the next account. Unexpected profile navigation stops the watch
and restores the original tab. There is no X API access.

Only GitHub API sources and arXiv metadata are checked automatically. Other PDF
links remain for agent review. Alerts identify changed research sources for
review; an X post never supplies a normalized score. The separate site GitHub Actions importer validates data before publication. New unsupported
sources require the normal source review before any data change.

Browser safety and parsing checks: `python3 -m unittest test_x_watch.py`.

Pivot alerts suppress repositories already in the board registry unless their
configured README headline saving changes. `pivot-watchlist.json` contains the
bound patterns. The watch stores exact rational values in `board_bound_states`,
using the latest imported score for the first comparison. Commit, star, prose,
and verification changes alone do not alert. Missing headline patterns are logged
as coverage errors; they do not count as changed bounds. Known board repositories
without a configured bound pattern are suppressed. New repositories still use
pivot discovery. This filter does not alter the separate people-watch event feed.

As of 2026-10-10, people discovery also handles first-branch CreateEvents and
polls each watched user's owned repositories by last push. The inventory provides
a second path when GitHub emits no repository-create or push event. It is capped
at 300 repositories per user; caps are logged. The classifier migration rechecks
previously ignored branch events once. `threesum` is an accepted problem spelling.
Pivot discovery searches names/descriptions separately from README text and feeds
relevant people-watch repositories directly into candidate review. Broad search
caps remain visible. A watched board repository can configure `bound_patterns`
for more than one problem; a change to either exact value triggers review.

## Public snapshot

Prepared 2026-10-12 for `bigospeedrun/watch`. This tree has one initial public
commit. The local `private-history` branch retains the earlier history and must
never be pushed. Push only `main`; never use `--all` or `--mirror`.
Source snapshots with removed email addresses or local provenance paths are
listed in `public-sanitization.json`. Their public hashes refer to the scrubbed
bytes. These copies are not byte-exact upstream receipts; original evidence
remains in private history. The historical builder reads the vendored sources
and retained chart digest; it does not require private research notes.
