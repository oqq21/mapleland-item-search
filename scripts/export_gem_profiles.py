"""Export equipment gem profiles from the collector's calculated criteria JSON."""
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

ALIASES={
    '공':'PAD','마력':'MAD','인':'INT','인트':'INT','힘':'STR','덱':'DEX','럭':'LUK',
    '명중':'ACC','명':'ACC','회피':'EVA','HP':'HP','MP':'MP','이속':'SPEED','점프':'JUMP',
}


def parse_profile(text):
    if text in {'','없음','대상 아님'}:
        return ()
    return tuple(sorted(ALIASES[name] for name in text.split('·')))


def export(source, destination):
    rows=json.loads(source.read_text(encoding='utf8'))['criteria']
    profiles=defaultdict(Counter)
    for row in rows:
        profile=tuple(parse_profile(row[key]) for key in ('required','optional'))
        if any(profile):
            for code in row['codes']:
                profiles[code][profile]+=1
    groups=defaultdict(list)
    for code, choices in sorted(profiles.items()):
        groups[choices.most_common(1)[0][0]].append(code)
    payload=[json.dumps([*profile,codes],separators=(',',':')) for profile,codes in sorted(groups.items())]
    destination.write_text('[\n'+',\n'.join(payload)+'\n]\n',encoding='utf8')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parents[1]/'resources/collection_gem_profiles.json')
    args=parser.parse_args()
    export(args.source,args.output)
