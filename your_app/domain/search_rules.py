"""Search-only rules. Raw totals, additional values and gem values stay separate."""
from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import Mapping

STATS = ('STR','DEX','INT','LUK','HP','MP','PAD','MAD','PDD','MDD','ACC','EVA','SPEED','JUMP')
LABELS = dict(zip(STATS, ('힘','덱','인트','럭','HP','MP','공','마력','물방','마방','명','회피','이속','점프')))
SUFFIXES = ('PAD','MAD','ACC','EVA','SPEED','JUMP','HP','MP','STR','INT','LUK','DEX')
GEM_VALUES = ((1,2,3),(1,2,3),(2,3,5),(2,3,5),(2,3,5),(1,2,3),(10,20,30),(10,20,30),(2,3,5),(2,3,5),(2,3,5),(1,3,5))
WEAPONS = {'한손검','한손도끼','한손둔기','두손검','두손도끼','두손둔기','창','폴암','단검','아대','활','석궁','완드','스태프','너클','총'}
ARMOR = {'신발','장갑','전신','상의','하의','모자','방패'}
COLORS = {'required':'#174EA6','optional':'#7030A0','invalid':'#595959','lower':'#8A4B08'}
NAME_COLORS = {'gray':'#595959','white':'#202733','blue':'#1677ff','purple':'#9333ea','yellow':'#a77800','lime':'#368b11','red':'#d41f46'}

def number(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError, OverflowError):
        return default

@dataclass(frozen=True)
class Gem:
    code: int
    stat: str
    grade: int
    value: int

def decode_gems(value) -> tuple[Gem, ...]:
    result = []
    for raw in re.findall(r'\d+', str(value or '')):
        code = int(raw)
        for grade, base in enumerate((6000,16000,26000)):
            if base <= code <= base+11:
                suffix=code-base
                result.append(Gem(code,SUFFIXES[suffix],grade,GEM_VALUES[suffix][grade]))
                break
    return tuple(result)

def context_for_query(query: str) -> str:
    for text in ('섀도어','단도','나로','전사','법사','궁수','도적','해적'):
        if text in query:
            return '섀도어' if text=='단도' else text
    return ''

def gem_profile(sheet: str, job: str, gems: tuple[Gem,...], context=''):
    if sheet not in WEAPONS | ARMOR:
        return frozenset(), frozenset(), False
    if sheet in WEAPONS:
        if sheet in {'완드','스태프'}: pair=({'MAD','INT'},{'LUK','EVA'})
        elif sheet in {'활','석궁'}: pair=({'PAD','DEX'},{'STR','EVA'})
        elif sheet=='아대': pair=({'PAD','LUK'},{'DEX','EVA','HP'})
        elif sheet=='단검': pair=({'PAD','LUK'},{'STR','DEX'})
        elif sheet=='너클': pair=({'PAD','STR'},{'DEX','ACC'})
        elif sheet=='총': pair=({'PAD','DEX'},{'STR','EVA','HP'})
        else: pair=({'PAD','STR'},{'DEX','ACC'})
    else:
        # Common gear has no mandatory class: an INT build must not require LUK.
        known_job=job in {'전사','법사','궁수','도적','나로','섀도어','해적'}
        if not known_job and 'INT' in {g.stat for g in gems}:
            return frozenset({'INT'}),frozenset({'HP','EVA','LUK'}),True
        actual_job=job if known_job else context
        if actual_job=='전사': pair=({'STR','DEX','ACC'},set())
        elif actual_job=='법사': pair=({'INT','LUK'},{'HP','EVA'})
        elif actual_job in {'궁수','해적'}: pair=({'STR','DEX'},{'HP','EVA'})
        elif actual_job=='섀도어' or (actual_job=='도적' and context=='섀도어'): pair=({'STR','DEX','LUK'},set())
        elif actual_job in {'도적','나로'}: pair=({'DEX','LUK'},{'HP','EVA'})
        else:
            # Preserve build-specific common equipment; don't invent a class.
            present={g.stat for g in gems}
            if 'INT' in present: pair=({'INT'},{'HP','EVA','LUK'})
            elif present & {'STR','DEX','LUK'}: pair=(present & {'STR','DEX','LUK'},{'HP','EVA','ACC'})
            else: pair=(set(),present & {'HP','EVA'})
    return frozenset(pair[0]),frozenset(pair[1]),True

def evaluate_gems(row: Mapping, prices: Mapping, context='') -> dict:
    gems=decode_gems(row.get('option_codes',''))
    sheet=str(row.get('sheet',''));job=str(row.get('직업',''))
    required, optional, applicable=gem_profile(sheet,job,gems,context)
    reverse=str(row.get('itemName','')).replace(' ','').startswith('리버스')
    recognized=[g for g in gems if applicable and g.stat in required | optional]
    cost=sum(number(prices.get(str(g.code),prices.get(g.code,0))) for g in recognized)
    if recognized and not reverse:
        cost += 2_250_000 + sum((750_000,1_500_000,2_250_000)[g.grade] for g in recognized)
    reasons=[]
    if reverse and not gems: reasons.append('리버스 무보석')
    if gems and applicable:
        present={g.stat for g in gems}
        missing=required-present
        if missing: reasons.append('필수 누락: '+ '·'.join(LABELS[s] for s in STATS if s in missing))
        high_required=sheet in WEAPONS or number(row.get('unit_price'))-cost >= 100_000_000
        lower={g.stat for g in gems if g.stat in required and g.grade<2}
        if high_required and lower: reasons.append('필수 상급 부족: '+'·'.join(LABELS[s] for s in STATS if s in lower))
        if sheet in WEAPONS and number(row.get('unit_price'))>0 and cost*10 >= number(row.get('unit_price'))*6:
            reasons.append('무기 보석 비중 60% 이상')
    spans=[]
    for g in gems:
        kind='required' if g.stat in required else 'optional' if g.stat in optional else 'invalid'
        color=COLORS['lower'] if kind!='invalid' and g.grade<2 else COLORS[kind]
        label=LABELS[g.stat]+'+'+str(g.value)
        spans.append(f'<span style="color:{color};font-weight:{800 if kind=="required" else 500}" title="{("하급","중급","상급")[g.grade]}">{html.escape(label)}</span>')
    return {'has_gems':bool(gems),'recognized_gem_cost':cost,'gem_html':' / '.join(spans),
            'gem_text':' / '.join(LABELS[g.stat]+'+'+str(g.value) for g in gems),
            'invalid_reasons':' / '.join(reasons),'gem_valid':not reasons,
            'gem_cell_style':'red' if reasons else 'green' if len(gems)==3 and all(g.grade==2 for g in gems) else 'white'}

def additional_sum(row: Mapping) -> int:
    return sum(number(row.get('add_'+s)) for s in STATS if s not in {'HP','MP'}) + int(number(row.get('add_HP'))/10) + int(number(row.get('add_MP'))/10)

def color_score(row: Mapping) -> int:
    return sum(number(row.get('add_'+s))+number(row.get('gem_'+s)) for s in STATS if s not in {'HP','MP'}) + sum(int((number(row.get('add_'+s))+number(row.get('gem_'+s)))/10) for s in ('HP','MP'))

def color_key(score):
    for upper,key in ((-1,'gray'),(5,'white'),(22,'blue'),(39,'purple'),(54,'yellow'),(69,'lime')):
        if score<=upper:return key
    return 'red'

def predicted_color(row: Mapping):
    if decode_gems(row.get('option_codes','')) or str(row.get('sheet','')) not in ARMOR | WEAPONS:return ''
    score=additional_sum(row);maximum=13 if str(row.get('sheet','')) in WEAPONS else 15
    for boundary,key in ((0,'white'),(6,'blue'),(23,'purple'),(40,'yellow'),(55,'lime'),(70,'red')):
        if score<boundary:return key if boundary-score<=maximum else ''
    return ''
