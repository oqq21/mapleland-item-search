"""Streamlit parquet-only item search. Production data is read-only."""
from __future__ import annotations
import json
import os
import tempfile
import time
from pathlib import Path
import pandas as pd
import streamlit as st
from your_app.common.remote_data import ensure_data_snapshot
from your_app.common.query_utils import mask_for_item_query, _ensure_cache_columns
from your_app.common.stat_query import parse_tokens
from your_app.common.site_links import search_page_url
from your_app.domain.search_rules import context_for_query, decode_gems, number
from your_app.processing.packet_search import search_packet_data, packet_view, format_stat_text, GEM_OPTION_LABELS, BASE_COLUMNS
from your_app.gui.search_table import render_table

ROOT=Path(__file__).resolve().parent
APP_BUILD="2026-11-10-search-rules-v1"
st.set_page_config(page_title="메랜 아이템검색",layout="wide",initial_sidebar_state="expanded")
st.html("""<style>.block-container{padding-top:1.5rem;padding-bottom:1rem;max-width:100%}h1{font-size:1.7rem!important}section[data-testid=stSidebar]{min-width:245px;max-width:310px}div[data-testid=stHorizontalBlock]{gap:.7rem}@media(max-width:850px){.block-container{padding:1rem}.stHorizontalBlock{flex-wrap:wrap}}.hint{color:#53627a;font-size:13px}</style>""")

@st.cache_resource
def load_catalog():
    records=json.loads((ROOT/'resources/item_catalog.json').read_text(encoding='utf-8'))
    frame=pd.DataFrame(records).astype('object').fillna('');_ensure_cache_columns(frame)
    return frame,{int(r['itemCode']):r for r in records}

@st.cache_data(max_entries=3,show_spinner=False)
def run_search(directory,version,codes,tokens,include_gems):
    _,catalog=load_catalog()
    return search_packet_data(Path(directory)/'packet_active.parquet',Path(directory)/'packet_completed.parquet',codes,list(tokens),include_gems,catalog)

items,catalog=load_catalog()
try:
    cache=Path(os.environ.get('PP213_DATA_CACHE_DIR',str(Path(tempfile.gettempdir())/'mapleland-item-search-data')))
    snapshot=ensure_data_snapshot(cache,check_interval=3600)
    prices=json.loads(snapshot.path('gem_prices.json').read_text(encoding='utf-8'))
except Exception as exc:
    st.error(f'검색 자료를 열지 못했습니다: {exc}');st.stop()

for key,value in {'query':'','stat1':'','stat2':'','stat3':'','packet_include_gems':False,'history':[],'page':1,'generation':0,'searched':False,'request_search':False}.items():
    if key not in st.session_state:st.session_state[key]=value

def restore_history(index):
    h=st.session_state.history[index]
    for k in ('query','stat1','stat2','stat3','packet_include_gems'):st.session_state[k]=h[k]
    st.session_state.request_search=True

def request_search():st.session_state.request_search=True

with st.sidebar:
    st.subheader('검색 기록')
    if not st.session_state.history:st.caption('검색하면 최근 9개가 여기에 남아요.')
    for i,h in enumerate(st.session_state.history):
        label=' · '.join(str(h[k]) for k in ('query','stat1','stat2','stat3') if h[k]) or '전체 검색'
        st.button(label,key=f'history_{i}',on_click=restore_history,args=(i,),width='stretch')
    with st.expander('검색 조건 안내'):
        st.write('궁수13은 정확히13, 궁수~13은 이하, 궁수13~는 이상, 궁수13~15는 구간입니다.')
        st.write('줄임말: 명·이·전·궁·도·단. 작 방향은 항상 보석을 뺀 추가치입니다.')
        st.write('법사=인트+럭+마력, 마·인·인트=합마. 법신은 추가 인트+럭+마력입니다.')
        st.write('노작은 기본 업횟과 남은 업횟이 같은 장비입니다. 완작·업6·작5도 검색할 수 있습니다.')
    st.caption('보석 글자: 필수 상급 파랑·굵게 / 보조 상급 보라 / 무효옵 회색 / 상급 미만 황갈색')
    st.caption('확인된 2분 이하 판매는 빨강. 시각·등록기간이 불확실하면 판매소요를 표시하지 않습니다.')

st.title('메랜 아이템검색')
st.caption('본체 총스탯과 보석을 나누어 보는 검색 · '+APP_BUILD)
with st.form('search_form'):
    columns=st.columns([3,1,1,1])
    columns[0].text_input('아이템명 또는 직업·부위',key='query',placeholder='네쉐르 / 도적신발 / 신망토')
    columns[1].text_input('스탯1',key='stat1',placeholder='공116')
    columns[2].text_input('스탯2',key='stat2',placeholder='덱4~5')
    columns[3].text_input('스탯3',key='stat3',placeholder='업0')
    submitted=st.form_submit_button('검색',type='primary',width='stretch')

opts=st.columns([2,1,1])
opts[0].toggle('보석 포함 스탯으로 검색',key='packet_include_gems',on_change=request_search,help='검색 판정에만 보석을 더합니다. 본체 표시는 보석 제외 총스탯입니다.')
status_filter=opts[1].selectbox('거래 상태',['전체','판매완료','판매중·만료'],key='status_filter')
gem_filter=opts[2].selectbox('보석 장착',['전체','무보석','유보석'],key='gem_filter')

if submitted or st.session_state.request_search:
    st.session_state.request_search=False
    query=st.session_state.query.strip()
    tokens=[st.session_state[k].strip() for k in ('stat1','stat2','stat3') if st.session_state[k].strip()]
    try:
        parse_tokens(tokens)
        if not query and not tokens:raise ValueError('아이템명 또는 스탯 조건을 입력해주세요.')
        matched=items.loc[mask_for_item_query(items,query)] if query else items
        matched=matched.loc[pd.to_numeric(matched.itemCode,errors='coerce').between(1000000,1999999)]
        if query=='단도' or any(c.name=='단도' for c in parse_tokens(tokens)):
            matched=matched.loc[pd.to_numeric(matched.get('힘',pd.Series(0,index=matched.index)),errors='coerce').fillna(0).ne(0)]
        codes=tuple(sorted(set(matched.itemCode.astype(int))))
        started=time.perf_counter()
        with st.spinner('조건에 맞는 매물을 찾는 중…'):
            rows,duplicates=run_search(str(snapshot.directory.resolve()),snapshot.version,codes,tuple(tokens),st.session_state.packet_include_gems)
        st.session_state.rows=rows;st.session_state.duplicates=duplicates
        st.session_state.matched=matched;st.session_state.applied_query=query;st.session_state.applied_tokens=tokens
        st.session_state.elapsed=time.perf_counter()-started
        st.session_state.searched=True;st.session_state.page=1;st.session_state.generation+=1
        saved={k:st.session_state[k] for k in ('query','stat1','stat2','stat3','packet_include_gems')}
        st.session_state.history=([saved]+[h for h in st.session_state.history if h!=saved])[:9]
        st.session_state.pop('search_error',None)
        st.rerun()
    except (ValueError,KeyError,IndexError) as exc:
        st.session_state.search_error=str(exc)
    except Exception as exc:
        st.session_state.search_error=f'검색 중 오류가 발생했습니다: {exc}'

if st.session_state.get('search_error'):st.error(st.session_state.search_error)
matched=st.session_state.get('matched',pd.DataFrame())
if not matched.empty:
    link=search_page_url(matched,st.session_state.get('applied_tokens',[]))
    a,b=st.columns([1,5])
    if link:a.link_button('검색페이지 열기',link,width='stretch')
    b.caption(f'일치 품목 {len(matched):,}개 · 외부 페이지의 조건은 메랜지지가 지원하는 범위로 열립니다.')
    st.caption('표시 중인 조건: '+st.session_state.get('applied_query','전체 품목')+' / '+' / '.join(st.session_state.get('applied_tokens',[])))
    with st.expander('품목과 기본옵 확인'):
        names=matched[['itemCode','itemName','sheet','직업','reqLevel']].copy()
        names['기본업횟']=matched['업횟']
        names['기본스탯']=matched.apply(lambda r:format_stat_text({'base_'+s:number(r.get(label)) for s,label in BASE_COLUMNS.items()},'base'),axis=1)
        st.dataframe(names.rename(columns={'itemCode':'코드','itemName':'품목','sheet':'부위','reqLevel':'레벨'}),hide_index=True,width='stretch',height=260)

rows=st.session_state.get('rows',pd.DataFrame())
if not rows.empty:
    visible=rows
    if status_filter=='판매완료':visible=visible.loc[visible.status.eq('completed')]
    elif status_filter=='판매중·만료':visible=visible.loc[visible.status.eq('active')]
    if gem_filter=='무보석':visible=visible.loc[~visible.has_gems]
    elif gem_filter=='유보석':visible=visible.loc[visible.has_gems]
    signature=(status_filter,gem_filter)
    if st.session_state.get('filter_signature')!=signature:
        st.session_state.page=1;st.session_state.generation+=1;st.session_state.filter_signature=signature
    count=len(visible);pages=max(1,(count+99)//100)
    st.session_state.page=min(st.session_state.page,pages)
    nav=st.columns([1,1,6])
    if nav[0].button('이전',disabled=st.session_state.page<=1):st.session_state.page-=1;st.rerun()
    if nav[1].button('다음',disabled=st.session_state.page>=pages):st.session_state.page+=1;st.rerun()
    nav[2].caption(f'{count:,}건 · {st.session_state.page}/{pages}페이지 · 중복제외 {st.session_state.duplicates:,}건 · 검색 {st.session_state.elapsed:.2f}초')
    start=(st.session_state.page-1)*100
    context=context_for_query(st.session_state.get('applied_query',''))
    if any(c.name=='단도' for c in parse_tokens(st.session_state.get('applied_tokens',[]))):context='섀도어'
    view=packet_view(visible.iloc[start:start+100],prices=prices,context=context)
    with st.container(key=f'results_{st.session_state.generation}_{st.session_state.page}'):
        st.html(render_table(view))
    st.caption('최신순 · 판매소요가 확인된 완료 매물은 연결된 판매중 시각으로 정렬 · 판매소요 빈칸에 마우스를 올리면 미확인 사유를 볼 수 있습니다.')
elif st.session_state.searched:st.info('조건에 맞는 매물이 없습니다.')
else:st.info('아이템명 또는 스탯을 입력하고 검색해주세요.')
with st.expander('보석 시세'):
    gem_rows=[]
    for suffix,(label,_) in GEM_OPTION_LABELS.items():
        gem_rows.append({'보석':label,**{grade:round(number(prices.get(str(base+suffix)))/10000,2) for base,grade in ((26000,'상급(만)'),(16000,'중급(만)'),(6000,'하급(만)'))}})
    st.dataframe(pd.DataFrame(gem_rows),hide_index=True,width='stretch')
st.caption(f'자료 갱신 시각 {snapshot.updated_at} · 원본 GitHub 자료 읽기 전용')
