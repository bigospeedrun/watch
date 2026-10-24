"""Size rules of a digest sent through the digest rule of the bos-deadman Isomux hook.

The rule has two args (channel, text) and Isomux gives each arg an equal share of the budget (server/webhooks/block.ts),
after the note of the hook and the sender prefix. Isomux cuts a text over its share without an error, so a part past the
cut is lost while the sender counts it as sent. Measured on 2026-10-24 with the dry-run route of the hook: the longest text
that is not cut is 1827 characters, as Isomux counts them (JSON.stringify, with < > & as six characters each).
"""
import json

LIMIT = 1700  # one message, header included; under the 1827 measured, with a margin
SEPARATOR = 4  # the blank line between two entries, escaped


def escaped(text):
    """The length of the text in the webhook JSON as Isomux counts it. ASCII escaping stays conservative."""
    return len(json.dumps(text)) - 2 + 5 * sum(text.count(c) for c in '<>&')


def header_cost(header):
    """The cost of a formatted header and the line break after it."""
    return escaped(header) + 2


def fit(text, room):
    """The entry, its quoted lines cut from the end until it fits; the first line (author, channel, link) stays."""
    if escaped(text) <= room:
        return text
    head, _, rest = text.partition('\n')
    while rest and escaped(head + '\n' + rest + ' [cut]') > room:
        rest = rest[:len(rest) * 3 // 4].rstrip()
    if rest:
        return head + '\n' + rest + ' [cut]'
    # A first line that alone is over the room (long names with < or CJK): cut it, every character costs at most 6.
    return text if escaped(head) <= room else head[:room // 6 - 6].rstrip() + ' [cut]'


def chunks(entries, room):
    """Group (key, text) entries so that each group, joined by blank lines, fits the room; an entry over the room is cut."""
    group, size = [], 0
    for key, text in entries:
        text = fit(text, room)
        if group and size + escaped(text) + SEPARATOR > room:
            yield group
            group, size = [], 0
        group.append((key, text))
        size += escaped(text) + SEPARATOR
    if group:
        yield group
