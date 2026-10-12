"""Local discovery scope set by the project owner."""
import re

def wht_only(text):
    wht=re.search(r'\bwht\b|walsh|hadamard',text,re.I)
    other=re.search(r'\bdft\b|\bfft\b|fourier|3sum|threesum|apsp|subset.sum|shortest.path|matrix.mult|integer.mult',text,re.I)
    return bool(wht and not other)

HOURLY_REPOS={'crocswap/integer-mult-bounds','swapnil-jain/integer-mult-kappa'}

def cross_board_problems(text):
    """Classify source text, never the hosting repository's name."""
    patterns={
        'exact DFT': r'\bdft\b|\bfft\b|\bfourier\b',
        '3SUM': r'\b3sum\b|\bthreesum\b',
        'APSP': r'\bapsp\b|\ball[ -]pairs shortest paths\b',
        'subset sum': r'\bsubset[ -]sum\b',
        'matrix multiplication': r'\bmatrix[ -](?:mult|multiplication)\b',
    }
    return [name for name,pattern in patterns.items() if re.search(pattern,text,re.I)]

def hourly_imported(repo,text):
    """Only integer-multiplication scope is delegated to the hourly importer."""
    from other_bounds_watch import other_problem
    return (repo.lower() in HOURLY_REPOS and
            not cross_board_problems(text) and not other_problem(text) and
            bool(re.search(r'integer[ -]mult|\bkappa\b|κ',text,re.I)))

def board_fork(meta, board):
    return bool(meta.get('fork') and any(meta.get(key,{}).get('full_name','').lower() in board for key in ('parent','source')))


def new_research_source(row, since):
    text=(row['repo']+' '+(row.get('description') or '')).lower().replace('-',' ')
    if not row.get('created_at') or row['created_at']<since:return False
    if re.search(r'tracker|dashboard|leetcode|daily.challenge|work in progress',text):return False
    problem=row.get('problem_guess','').lower()
    return problem!='unknown; inspect source' and problem in text


def visible_problem(text):
    return bool(re.search(r'\binteger[ -](?:mult|multiplication)\b|\bfourier\b|\bdft\b|\bfft\b|\b3sum\b|\bthreesum\b|\bapsp\b|\ball[ -]pairs shortest paths\b|\bsubset[ -]sum\b|\bmatrix[ -](?:mult|multiplication)\b',text,re.I))
