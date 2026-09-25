import re
from rapidfuzz import fuzz, process

REPLACEMENTS = {
    'limited': 'ltd',
    'corporation': 'corp',
    'company': 'co',
    'incorporated': 'inc',
    'mechanical': 'mechanic',
    'operations': 'ops',
    'services': 'svc',
    'service': 'svc',
    'logistics': 'logistics',
}


def normalize(text):
    text = (text or '').lower().strip()
    for src, dst in REPLACEMENTS.items():
        text = text.replace(src, dst)
    text = re.sub(r'[^a-z0-9]+', ' ', text)
    return ' '.join(text.split())


def build_alias_index(pairs):
    index = {}
    for label, key in pairs:
        norm = normalize(label)
        if norm and norm not in index:
            index[norm] = key
    return index


def match_key(raw_name, alias_index, cutoff=85):
    norm = normalize(raw_name)
    if not norm:
        return None
    if norm in alias_index:
        return alias_index[norm]
    choices = list(alias_index.keys())
    if not choices:
        return None
    best = process.extractOne(norm, choices, scorer=fuzz.ratio)
    if best and best[1] >= cutoff:
        return alias_index[best[0]]
    best = process.extractOne(norm, choices, scorer=fuzz.token_sort_ratio)
    if best and best[1] >= cutoff:
        return alias_index[best[0]]
    return None
