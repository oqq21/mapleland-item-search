"""Search-only rules. Raw totals, additional values and gem values stay separate."""
from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Mapping

STATS = ('STR','DEX','INT','LUK','HP','MP','PAD','MAD','PDD','MDD','ACC','EVA','SPEED','JUMP')
LABELS = dict(zip(STATS, ('힘','덱','인트','럭','HP','MP','공','마력','물방','마방','명','회피','이속','점프')))
SUFFIXES = ('PAD','MAD','ACC','EVA','SPEED','JUMP','HP','MP','STR','INT','LUK','DEX')
GEM_VALUES = ((1,2,3),(1,2,3),(2,3,5),(2,3,5),(2,3,5),(1,2,3),(10,20,30),(10,20,30),(2,3,5),(2,3,5),(2,3,5),(1,3,5))
WEAPONS = {'한손검','한손도끼','한손둔기','두손검','두손도끼','두손둔기','창','폴암','단검','아대','활','석궁','완드','스태프','너클','총'}
ARMOR = {'신발','장갑','전신','상의','하의','모자','방패'}
YELLOW_UMBRELLA = 1302016
GEM_PROFILE_PATH = Path(__file__).resolve().parents[2]/'resources/collection_gem_profiles.json'
GEM_FEES = (750_000,1_500_000,2_250_000)
GEM_COLORS = {'required':'#0052cc','optional':'#006b3c','invalid':'#6b7280','recognized':'#6b7280'}
GEM_ERROR_COLORS = {'required':'#00235f','optional':'#00351e','invalid':'#302b33','recognized':'#302b33'}
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

def gem_costs(gems, prices, *, reverse=False):
    materials=sum(number(prices.get(str(g.code),prices.get(g.code,0))) for g in gems)
    fee=0 if not gems or reverse else 2_250_000+sum(GEM_FEES[g.grade] for g in gems)
    return materials, fee

def parse_calculator_gems(text):
    aliases={LABELS[stat]:stat for stat in SUFFIXES}
    aliases.update(인='INT',마='MAD',명중='ACC',피='HP',회='EVA',이='SPEED')
    pattern=r'([가-힣A-Za-z]+)\s*\+?\s*(\d+)'
    if re.sub(pattern,'',text).strip(' ,/\t\n') or not text.strip():
        raise ValueError('보석 옵션과 수치를 입력하세요. 예: 공3 덱5 럭5')
    options=re.findall(pattern,text)
    if not 1<=len(options)<=3:
        raise ValueError('보석은 1~3개까지 입력할 수 있습니다.')
    result=[]
    for label,raw in options:
        stat=aliases.get(label.upper(),aliases.get(label));value=int(raw)
        if stat is None:
            raise ValueError(f'{label}은 지원하는 보석 옵션이 아닙니다.')
        suffix=SUFFIXES.index(stat)
        if value not in GEM_VALUES[suffix]:
            allowed=' / '.join(map(str,GEM_VALUES[suffix]))
            raise ValueError(f'{label}의 보석 수치는 {allowed} 중 하나를 입력하세요.')
        grade=GEM_VALUES[suffix].index(value)
        result.append(Gem((6000,16000,26000)[grade]+suffix,stat,grade,value))
    return tuple(result)

@lru_cache(maxsize=1)
def collection_profiles():
    groups=json.loads(GEM_PROFILE_PATH.read_text(encoding='utf-8'))
    return {code:(frozenset(required),frozenset(optional)) for required,optional,codes in groups for code in codes}

def collection_profile(row, sheet, job, gems, context):
    applicable=sheet in WEAPONS | ARMOR
    code=number(row.get('itemCode'))
    if not code:
        return gem_profile(sheet,job,gems,context)
    if code==YELLOW_UMBRELLA:
        return frozenset({'INT','MAD'}),frozenset({'LUK','EVA','SPEED','HP'}),True
    required,optional=collection_profiles().get(code,(frozenset(),frozenset()))
    if code in {1050018,1051017} and not all(number(row.get('total_'+s))>0 for s in ('DEX','LUK')):
        return frozenset(),frozenset(),applicable
    if code==1082002 and sum(number(row.get('total_'+s)) for s in ('STR','DEX','ACC'))<16:
        return frozenset(),frozenset(),applicable
    return required,optional,applicable

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
    required, optional, applicable=collection_profile(row,sheet,job,gems,context)
    unrestricted=not (required or optional)
    reverse=str(row.get('itemName','')).replace(' ','').startswith('리버스')
    recognized=[g for g in gems if applicable and (unrestricted or g.stat in required | optional)]
    materials,fee=gem_costs(recognized,prices,reverse=reverse);cost=materials+fee
    price=number(row.get('unit_price'))
    weapon=sheet in WEAPONS
    physical_weapon=weapon and sheet not in {'완드','스태프'} and number(row.get('itemCode'))!=YELLOW_UMBRELLA
    attack_only=physical_weapon and price<=100_000_000
    effective_required={'PAD'} if attack_only else required
    upper_required=effective_required if price>=100_000_000 or attack_only else frozenset()
    option_reasons=[];missing=set();lower=set()
    if reverse and not gems:option_reasons.append('리버스 무보석')
    if gems and applicable and not unrestricted:
        missing=set(effective_required)-{g.stat for g in gems}
        lower={g.stat for g in gems if g.stat in upper_required and g.grade<2}
    if gems and physical_weapon:
        attacks=[g for g in gems if g.stat=='PAD']
        if not attacks:missing.add('PAD')
        elif not any(g.value==3 and g.grade==2 for g in attacks):lower.add('PAD')
    if missing:option_reasons.append('필수 누락: '+'·'.join(LABELS[s] for s in STATS if s in missing))
    if lower:option_reasons.append('필수 상급 부족: '+'·'.join(LABELS[s] for s in STATS if s in lower))
    ratio_reason=''
    if gems and price>0:
        if weapon and cost*10>=price*6: ratio_reason='무기 보석 비중 60% 이상'
        if sheet in ARMOR and cost*5>=price*4: ratio_reason='방어구 보석 비중 80% 이상'
    perfect=len(gems)==len(recognized)==3 and all(g.grade==2 for g in gems)
    cell_style='red' if option_reasons else 'green' if perfect else 'white'
    colors=GEM_ERROR_COLORS if option_reasons else GEM_COLORS
    spans=[]
    roles={'required':0,'optional':1,'invalid':2,'recognized':2}
    tokens=[('required' if g.stat in required else 'optional' if g.stat in optional else
             'recognized' if unrestricted and applicable else 'invalid',g) for g in gems]
    for kind,g in sorted(tokens,key=lambda pair:roles[pair[0]]):
        grade=('하급','중급','상급')[g.grade]
        label=html.escape(LABELS[g.stat])
        grade_class='gem-upper' if g.grade==2 else 'gem-lower'
        value=f'<b class="{grade_class}">{g.value}</b>'
        token=f'{label}{value}'
        if g.grade<2 or kind not in {'required','optional'}:token=f'({token})'
        spans.append(f'<span class="gem-token" style="color:{colors[kind]}" title="{grade}">{token}</span>')
    reasons=option_reasons+[ratio_reason] if ratio_reason else option_reasons
    return {'has_gems':bool(gems),'recognized_gem_cost':cost,'gem_html':' / '.join(spans),
            'gem_text':' / '.join(LABELS[g.stat]+'+'+str(g.value) for g in gems),
            'invalid_reasons':' / '.join(reasons),'gem_valid':not reasons,
            'gem_cell_style':cell_style,'gem_ratio_warning':bool(ratio_reason)}

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
