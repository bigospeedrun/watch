The 2499/1250 baseline passed the scored Comparator gate on 2026-10-08 UTC.
Both the Lean and nanoda kernels accepted it. See verification.json,
comparator.log, and comparator.time in this folder.

The check reused 5776 upstream proof artifacts. It built a fresh core statement,
score challenge, and submission wrapper. Comparator exported and checked the
proof again. The current gate rejects this equal score as a new record.

source_commit identifies the local commit that contains this wrapper.
predecessors identifies Anthropic's pinned formalization. The source URL is
intended for publication; this work has not pushed the repo. The dates record
local creation and observation. A site importer records its own ingestion time.
upstream_status is not-applicable because this is a seeded baseline, not a PR.

This is local proof-check evidence. It is not a signed receipt or public badge.
