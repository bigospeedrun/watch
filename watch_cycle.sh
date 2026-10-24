#!/bin/bash
# One watch cycle. Started by the runbook as the transient systemd user unit bos-watch-cycle, under
# .git/poll.lock, so that it finishes even when the Isomux cronjob session that started it ends
# (2026-10-22 19:05Z: the cron agent backgrounded the >10 min block, ended its turn, and the
# session release killed the cycle in pivot_watch.py with no alert).
cd "$(dirname "$(readlink -f "$0")")"
set -eu
# The systemd timer bos-watch-cycle.timer and the agent session both start this script, under the same lock.
date -u +%Y-%m-%dT%H:%M:%SZ > .git/cycle-started.txt
# A step that stops the cycle alerts Lead once (cycle_alert.py dedupes by step
# until it passes again). STEP and LOG name the running command.
STEP=preflight;LOG=.git/watch-preflight.log;ALERTED=0
trap 'rc=$?; if [ "$rc" -ne 0 ] && [ "$ALERTED" = 0 ]; then python3 cycle_alert.py fail "$STEP" "$LOG" "$rc" >> .git/cycle-alert.log 2>&1 || echo "Cycle failure alert not delivered; see .git/cycle-alert.log" >&2; fi' EXIT
if test "$(git branch --show-current)" != main; then
  echo 'Watch cycles require branch main; stop without changing branches.' | tee "$LOG" >&2
  exit 1
fi
if test -n "$(git status --porcelain)"; then
  { echo 'Worktree has edits; leave them untouched and stop.'; git status --porcelain; } > "$LOG"
  echo 'Worktree has edits; leave them untouched and stop.' >&2
  exit 1
fi
cp people-watch.json .git/watch-previous-people.json
cp pivot-watch.json .git/watch-previous-pivot.json
STEP=tests;LOG=.git/watch-tests.log
python3 -m unittest test_people_watch test_pivot_watch test_watch_policy test_other_bounds_watch test_crocswap_pr_watch test_refresh_health test_discord_watch test_discord_ack test_problem_selection_watch test_cycle_alert test_deadman test_lean_target_watch test_pwn_watch test_discord_signals test_digest_size test_comment_watch > "$LOG" 2>&1
if python3 discord_watch.py > .git/discord-watch.log 2>&1; then
  python3 cycle_alert.py ok discord-intake >> .git/cycle-alert.log 2>&1 || true
else
  echo "Discord intake incomplete; retain sanitized progress and retry next cycle." >&2
  python3 cycle_alert.py fail discord-intake .git/discord-watch.log 1 --continued >> .git/cycle-alert.log 2>&1 || true
fi
if python3 problem_selection_watch.py > .git/problem-selection.log 2>&1; then
  python3 cycle_alert.py ok problem-selection >> .git/cycle-alert.log 2>&1 || true
else
  echo "Problem selection digest incomplete; cursor kept, retry next cycle." >&2
  python3 cycle_alert.py fail problem-selection .git/problem-selection.log 1 --continued >> .git/cycle-alert.log 2>&1 || true
fi
if python3 lean_target_watch.py > .git/lean-target-watch.log 2>&1; then
  python3 cycle_alert.py ok lean-target >> .git/cycle-alert.log 2>&1 || true
else
  echo "Lean target watch incomplete; retry next cycle." >&2
  python3 cycle_alert.py fail lean-target .git/lean-target-watch.log 1 --continued >> .git/cycle-alert.log 2>&1 || true
fi
# Cross-check the hourly dead-man timer once it is installed: its state file
# must be fresher than 2 h.
if test -f "$HOME/.config/systemd/user/bigospeedrun-deadman.timer"; then
  if test -n "$(find .git/deadman-state.json -mmin -120 2>/dev/null)"; then
    python3 cycle_alert.py ok deadman >> .git/cycle-alert.log 2>&1 || true
  else
    echo 'deadman-state.json older than 2 h or missing; see journalctl --user -u bigospeedrun-deadman.service' > .git/deadman-check.log
    python3 cycle_alert.py fail deadman .git/deadman-check.log 1 --continued >> .git/cycle-alert.log 2>&1 || true
  fi
fi
STEP=people-watch;LOG=.git/people-watch.log
python3 people_watch.py > "$LOG" 2>&1
STEP=pivot-watch;LOG=.git/pivot-watch.log
python3 pivot_watch.py > "$LOG" 2>&1
STEP=alert-candidates;LOG=.git/watch-alert-candidates.log
python3 - > "$LOG" 2>&1 <<'PY'
import json
from pathlib import Path
from pivot_watch import alert_candidate
previous=json.loads(Path('.git/watch-previous-pivot.json').read_text())
watch=json.loads(Path('pivot-watch.json').read_text())
known={r['repo'] for r in previous.get('candidates',[])
       if r.get('likely_new_race') or r.get('likely_pivot') or r.get('likely_tracked_source')}
changed={r['repo'] for r in watch.get('watched_repositories',[]) if r['new_commit']}
alerts=[r for r in watch['candidates'] if alert_candidate(r,known,changed)]
Path('.git/watch-alert-candidates.json').write_text(json.dumps(alerts,indent=2)+'\n')
# The agent session reviews candidates later and may miss a cycle (usage limit): keep each cycle's own
# list until the session has reviewed it, because the next cycle counts these repos as known.
if alerts:
    pending=Path('.git/watch-candidates-pending');pending.mkdir(exist_ok=True)
    (pending/(watch['checked_at'].replace(':','')+'.json')).write_text(json.dumps(alerts,indent=2)+'\n')
print('Checked',watch['checked_at'],'candidate alerts',len(alerts))
PY
cat "$LOG"
STEP=commit;LOG=.git/watch-git.log
git diff --check > "$LOG" 2>&1
if ! git diff --quiet -- people-watch.json pivot-watch.json discord-submissions.json; then
  git add -- people-watch.json pivot-watch.json discord-submissions.json
  git commit -m "Update GitHub watches $(date -u +%Y-%m-%dT%H:%M:%SZ)" -- people-watch.json pivot-watch.json discord-submissions.json >> "$LOG" 2>&1
fi
STEP=push;LOG=.git/watch-push.log
# The push alert goes through cycle_alert.py too: once, until a push succeeds.
git -c push.followTags=false push origin main:refs/heads/main > "$LOG" 2>&1
python3 cycle_alert.py ok preflight tests people-watch pivot-watch alert-candidates commit push cycle >> .git/cycle-alert.log 2>&1 || true
