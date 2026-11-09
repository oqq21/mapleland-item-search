"""Strict search token parser; comparison semantics belong to packet_store."""
import re
from dataclasses import dataclass

ALIASES={'명중':'명','이':'이속','전':'전사','궁':'궁수','도':'도적','단':'단도','인트':'인','합마':'마','회':'회피','hp':'HP','mp':'MP','피':'HP','업':'업횟'}
NAMES={'힘','덱','인','럭','공','마','명','회피','이속','점프','물방','마방','HP','MP','전사','궁수','도적','단도','법사','법신','법지','법행','신점','신민','업횟','작'}
@dataclass(frozen=True)
class Condition:
    name:str
    low:int|None=None
    high:int|None=None

def parse_token(raw):
    text=re.sub(r'\s+','',str(raw or ''))
    if text in {'노작','완작'}:return Condition(text)
    match=re.fullmatch(r'([가-힣A-Za-z]+)(?:=)?([+-]?\d+)?(~)?([+-]?\d+)?',text)
    if not match:raise ValueError(f'잘못된 스탯 조건: {raw} (예: 궁수13, 궁수~13, 궁수13~, 궁수13~15)')
    name,a,span,b=match.groups();name=ALIASES.get(name,name)
    if name not in NAMES or (a is None and b is None):raise ValueError(f'지원하지 않는 스탯 조건: {raw}')
    if not span:
        if b is not None:raise ValueError(f'잘못된 조건: {raw}')
        return Condition(name,int(a),int(a))
    low=int(a) if a is not None else None;high=int(b) if b is not None else None
    if low is not None and high is not None and low>high:raise ValueError(f'범위의 시작이 끝보다 큽니다: {raw}')
    return Condition(name,low,high)

def parse_tokens(tokens):return [parse_token(t) for t in tokens if str(t or '').strip()]
