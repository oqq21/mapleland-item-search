"""Conservative links between auction observations and completed sales."""
from bisect import bisect_left, bisect_right
from collections import Counter, defaultdict

DAY = 86_400


def infer_registration(first_seen, expires, listing_days=None):
    if first_seen is None or expires is None:
        return None
    remaining = expires - first_seen
    if listing_days in (1, 3):
        period = listing_days
    elif DAY < remaining <= 3 * DAY:
        period = 3
    else:
        return None
    if 0 < remaining <= period * DAY:
        return expires - period * DAY
    return None


def unique_links(active, completed):
    """Return mutually unique links and flag matches with competing candidates."""
    by_fingerprint = defaultdict(list)
    for index, fingerprint, seen, expires in active:
        if seen is not None and expires is not None and seen < expires:
            by_fingerprint[fingerprint].append((seen, index, expires))
    for rows in by_fingerprint.values():
        rows.sort()

    candidates = {}
    competing = set()
    active_demand = Counter()
    for index, fingerprint, sold in completed:
        rows = by_fingerprint.get(fingerprint)
        if not rows or sold is None:
            continue
        low = bisect_left(rows, (sold - 3 * DAY, -1))
        high = bisect_right(rows, (sold, float('inf')))
        possible = []
        for position in range(low, high):
            _, active_index, expires = rows[position]
            if sold < expires:
                possible.append(active_index)
        active_demand.update(possible)
        if len(possible) == 1:
            candidates[index] = possible[0]
        elif possible:
            competing.add(index)
    links = {}
    for index, active_index in candidates.items():
        if active_demand[active_index] == 1:
            links[index] = active_index
        else:
            competing.add(index)
    return links, competing
