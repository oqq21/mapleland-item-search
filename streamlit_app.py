"""Streamlit parquet-only item search. Production data is read-only."""
from __future__ import annotations
import json
from html import escape
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
from your_app.domain.search_rules import context_for_query, number
from your_app.processing.packet_search import search_packet_data, packet_view, format_stat_text, GEM_OPTION_LABELS, BASE_COLUMNS, filter_display_rows
from your_app.gui.search_table import render_table
from your_app.gui.compact_layout import COMPACT_CSS

ROOT=Path(__file__).resolve().parent
APP_BUILD="2026-11-10-search-v3"
st.set_page_config(page_title="메랜 아이템검색",layout="wide",initial_sidebar_state="collapsed")
st.html(COMPACT_CSS)

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

for key,value in {'query':'','stat1':'','stat2':'','stat3':'','packet_include_gems':False,'history':[],'page':1,'generation':0,'searched':False,'request_search':False,'status_filter':'전체','gem_filter':'전체'}.items():
    if key not in st.session_state:st.session_state[key]=value
for key,allowed in {'status_filter':{'전체','판매중','판매완료','만료'},'gem_filter':{'전체','유보석','무보석'}}.items():
    if st.session_state[key] not in allowed:st.session_state[key]='전체'

def restore_history(index):
    h=st.session_state.history[index]
    for k in ('query','stat1','stat2','stat3','packet_include_gems'):st.session_state[k]=h[k]
    request_search()

def request_search():
    st.session_state.status_filter='전체'
    st.session_state.gem_filter='전체'
    st.session_state.request_search=True

# Keep the workspace at the same delta path during input blur searches.
# A transient top-level spinner would remount the inputs and lose Tab focus.
search_feedback=st.empty()
if st.session_state.request_search:
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
        with search_feedback.container():
            with st.spinner('조건에 맞는 매물을 찾는 중…'):
                rows,duplicates=run_search(str(snapshot.directory.resolve()),snapshot.version,codes,tuple(tokens),st.session_state.packet_include_gems)
        st.session_state.rows=rows;st.session_state.duplicates=duplicates
        st.session_state.matched=matched;st.session_state.applied_query=query;st.session_state.applied_tokens=tokens
        st.session_state.elapsed=time.perf_counter()-started
        st.session_state.searched=True;st.session_state.page=1;st.session_state.generation+=1
        saved={k:st.session_state[k] for k in ('query','stat1','stat2','stat3','packet_include_gems')}
        st.session_state.history=([saved]+[h for h in st.session_state.history if h!=saved])[:9]
        st.session_state.pop('search_error',None)
    except (ValueError,KeyError,IndexError) as exc:
        st.session_state.search_error=str(exc)
    except Exception as exc:
        st.session_state.search_error=f'검색 중 오류가 발생했습니다: {exc}'
search_feedback.empty()

@st.dialog('보석값 · 재료 시세',width='large')
def show_gem_prices():
    header='<tr><th>보석</th><th>상급(만)</th><th>중급(만)</th><th>하급(만)</th></tr>'
    rows=[]
    for suffix,(label,_) in GEM_OPTION_LABELS.items():
        cells=''.join('<td>'+f'{number(prices.get(str(base+suffix)))/10000:,.2f}'.rstrip('0').rstrip('.')+'</td>' for base in (26000,16000,6000))
        rows.append('<tr><td>'+escape(label)+'</td>'+cells+'</tr>')
    st.html('<table class="gem-price-table"><thead>'+header+'</thead><tbody>'+''.join(rows)+'</tbody></table>')
    st.caption('보석 재료값 기준 · 단위: 만 메소')


with st.container(key='workspace',gap='xxsmall'):
    top=st.columns([2.5,1.05,.8,.8,.8,3.1],vertical_alignment='center',wrap=False)
    top[0].html('<div class="app-title">메랜 아이템검색</div>')
    with top[1].popover('최근 검색',width='stretch'):
        if not st.session_state.history:st.caption('최근 9개 검색이 여기에 남아요.')
        for i,h in enumerate(st.session_state.history):
            label=' · '.join(str(h[k]) for k in ('query','stat1','stat2','stat3') if h[k]) or '전체 검색'
            if h['packet_include_gems']:label+=' · 보석 포함'
            st.button(label,key=f'history_{i}',on_click=restore_history,args=(i,),width='stretch')
    with top[2].popover('기본옵',width='stretch'):
        matched=st.session_state.get('matched',pd.DataFrame())
        if matched.empty:st.caption('검색 후 일치 품목의 기본옵을 볼 수 있어요.')
        else:
            names=matched[['itemCode','itemName','sheet','직업','reqLevel']].copy()
            names['기본업횟']=matched['업횟']
            names['기본스탯']=matched.apply(lambda r:format_stat_text({'base_'+s:number(r.get(label)) for s,label in BASE_COLUMNS.items()},'base'),axis=1)
            st.dataframe(names.rename(columns={'itemCode':'코드','itemName':'품목','sheet':'부위','reqLevel':'레벨'}),hide_index=True,width='stretch',height=300)
    if top[3].button('보석값',width='stretch'):show_gem_prices()
    with top[4].popover('도움말',width='stretch'):
        st.write('궁수13: 정확값 / 궁수~13: 이하 / 궁수13~: 이상 / 궁수13~15: 구간')
        st.write('줄임말: 명·이·전·궁·도·단. 작 방향은 항상 보석 제외 추가치입니다.')
        st.write('법사=인트+럭+마력. 마·인·인트=합마. 법신=추가 인트+럭+마력.')
        st.write('노작=남은 업횟이 기본 업횟과 같음. 완작·업6·작5도 검색할 수 있습니다.')
        st.write('필수 상급: 파랑·굵게 / 보조 상급: 보라 / 무효옵: 회색 / 상급 미만: 황갈색')
        st.write('확인된 2분 이하 판매만 빨강. 판매소요가 미확인이면 마우스를 올려 사유를 볼 수 있습니다.')
        st.write('완료와 연결된 매물은 판매중 수집시각으로 정렬합니다. 새 검색·기록 선택은 목록 맨 위부터 시작합니다.')
        st.write('외부 검색페이지는 메랜지지가 지원하는 조건 범위로 열립니다.')
        st.caption('자료 갱신 시각: '+snapshot.updated_at+' · GitHub 읽기 전용')
        st.caption(APP_BUILD)
    top[5].html('<div class="app-meta">본체 총스탯 / 보석 분리 · '+APP_BUILD+'</div>')

    search_area,filter_area=st.columns([3.4,4.6],vertical_alignment='top',wrap=False)
    with search_area.container(key='search_fields',gap='xxsmall'):
        st.text_input('이름',key='query',placeholder='아이템명 / 도적신발 / 신망토',on_change=request_search)
        fields=st.columns([1,1,1,.75],vertical_alignment='bottom',wrap=False)
        fields[0].text_input('스탯1',key='stat1',placeholder='공116',on_change=request_search)
        fields[1].text_input('스탯2',key='stat2',placeholder='덱4~5',on_change=request_search)
        fields[2].text_input('스탯3',key='stat3',placeholder='업0',on_change=request_search)
        fields[3].button('검색',type='primary',width='stretch',on_click=request_search)
    with filter_area.container(key='filter_fields',gap='xxsmall'):
        trade=st.columns([.5,4],vertical_alignment='center',wrap=False)
        trade[0].html('<div class="filter-label">거래</div>')
        status_filter=trade[1].segmented_control('거래 상태',['전체','판매중','판매완료','만료'],key='status_filter',required=True,label_visibility='collapsed')
        gem=st.columns([.5,4],vertical_alignment='center',wrap=False)
        gem[0].html('<div class="filter-label">보석</div>')
        gem_filter=gem[1].segmented_control('보석 장착',['전체','유보석','무보석'],key='gem_filter',required=True,label_visibility='collapsed')
        options=st.columns([1.6,1.3,2],vertical_alignment='center',wrap=False)
        options[0].toggle('보석 포함 검색',key='packet_include_gems',on_change=request_search,help='검색 조건에만 보석을 더합니다. 본체 숫자와 보석은 나누어 표시합니다.')
        external_slot=options[1].empty()
        applied_slot=options[2].empty()

    if st.session_state.get('search_error'):st.error(st.session_state.search_error)
    matched=st.session_state.get('matched',pd.DataFrame())
    if not matched.empty:
        link=search_page_url(matched,st.session_state.get('applied_tokens',[]))
        if link:external_slot.link_button('검색페이지 열기',link,width='stretch')
        applied=' · '.join([st.session_state.get('applied_query','') or '전체 품목',*st.session_state.get('applied_tokens',[])])
        applied_slot.html('<div class="applied-query" title="'+escape(applied,quote=True)+'">'+escape(applied)+f' · {len(matched):,}품목</div>')

    rows=st.session_state.get('rows',pd.DataFrame())
    if not rows.empty:
        visible=filter_display_rows(rows,status_filter,gem_filter)
        signature=(status_filter,gem_filter)
        if st.session_state.get('filter_signature')!=signature:
            st.session_state.page=1;st.session_state.generation+=1;st.session_state.filter_signature=signature
        count=len(visible);pages=max(1,(count+99)//100)
        st.session_state.page=min(st.session_state.page,pages)
        nav=st.columns([.65,.65,8],vertical_alignment='center',wrap=False)
        if nav[0].button('이전',disabled=st.session_state.page<=1):st.session_state.page-=1;st.rerun()
        if nav[1].button('다음',disabled=st.session_state.page>=pages):st.session_state.page+=1;st.rerun()
        nav[2].caption(f'{count:,}건 · {st.session_state.page}/{pages}페이지 · 중복제외 {st.session_state.duplicates:,}건 · 검색 {st.session_state.elapsed:.2f}초')
        start=(st.session_state.page-1)*100
        context=context_for_query(st.session_state.get('applied_query',''))
        if any(c.name=='단도' for c in parse_tokens(st.session_state.get('applied_tokens',[]))):context='섀도어'
        view=packet_view(visible.iloc[start:start+100],prices=prices,context=context)
        with st.container(key=f'results_{st.session_state.generation}_{st.session_state.page}',gap=None):
            st.html(render_table(view))
    elif st.session_state.searched:st.info('조건에 맞는 매물이 없습니다.')
    else:st.info('아이템명 또는 스탯을 입력하고 검색해주세요.')
