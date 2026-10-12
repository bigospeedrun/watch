"""Read-only GitHub API helpers. No upstream code is imported or executed."""
import base64, json, subprocess, time
from urllib.parse import urlencode, quote

def api(path, params=None, *, deadline=None):
    """A bounded caller gets one attempt; ordinary reads retain three attempts."""
    if params:
        path += ('&' if '?' in path else '?') + urlencode(params)
    attempts=1 if deadline is not None else 3
    for attempt in range(attempts):
        remaining=deadline-time.monotonic() if deadline is not None else 120
        if remaining<=0:raise RuntimeError('GitHub GET time budget exhausted')
        try:
            result = subprocess.run(['gh', 'api', '--method', 'GET', path], capture_output=True, text=True, timeout=min(120,remaining))
        except subprocess.TimeoutExpired as error:
            raise RuntimeError(f'GitHub GET timed out: {path.split("?")[0]}') from error
        if result.returncode == 0:
            return json.loads(result.stdout)
        if attempt < attempts-1 and any(s in result.stderr for s in ('429', '502', '503', 'rate limit')):
            time.sleep(20)
            continue
        raise RuntimeError(f'GitHub GET failed: {path.split("?")[0]} (exit {result.returncode})')

def pages(path, params=None, limit=30):
    out = []
    for page in range(1, limit + 1):
        data = api(path, {**(params or {}), 'per_page': 100, 'page': page})
        out.extend(data)
        if len(data) < 100:
            return out
    raise RuntimeError(f'Pagination limit reached: {path}')

def content(repo, path, sha, *, deadline=None):
    data = api(f'repos/{repo}/contents/{quote(path, safe="/")}', {'ref': sha},deadline=deadline)
    if data.get('encoding') != 'base64':
        raise ValueError(f'Unsupported content: {repo}/{path}')
    return base64.b64decode(data['content'], validate=False)
