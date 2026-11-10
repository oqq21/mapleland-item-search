"""Parquet search with newitemp bases, strict conditions and conservative time linking."""
from __future__ import annotations
import bisect
from html import escape
from functools import lru_cache
from pathlib import Path
import pandas as pd
from your_app.common.stat_query import parse_tokens
from your_app.common.display_format import price_in_man
from your_app.domain.search_rules import STATS,LABELS,SUFFIXES,GEM_VALUES,decode_gems,number,color_score,color_key,additional_sum,evaluate_gems,predicted_color

ACTUAL_STATS=list(STATS)
STAT_LABELS=LABELS
GEM_OPTION_LABELS={i:(LABELS[s],GEM_VALUES[i]) for i,s in enumerate(SUFFIXES)}
TOTAL_COMPONENTS={'전사':['STR','DEX','ACC'],'궁수':['STR','DEX'],'도적':['DEX','LUK'],'단도':['STR','DEX','LUK'],'법사':['INT','LUK','MAD'],'신점':['STR','DEX','ACC'],'신민':['STR','DEX','ACC'],'법지':['INT','LUK','MAD'],'법행':['INT','LUK','MAD']}
SIMPLE_STATS={'힘':'STR','덱':'DEX','럭':'LUK','공':'PAD','명':'ACC','회피':'EVA','이속':'SPEED','점프':'JUMP','물방':'PDD','마방':'MDD','HP':'HP','MP':'MP'}
BASE_COLUMNS={'STR':'힘','DEX':'덱','INT':'인','LUK':'럭','PAD':'공','MAD':'마','PDD':'물방','MDD':'마방','ACC':'명','EVA':'회피','SPEED':'이속','JUMP':'점프','HP':'HP','MP':'MP'}
RAW_COLUMNS=['status','captured_at','internal_time','event_time','itemCode','itemName','sheet','quantity','total_price','unit_price','option_codes','total_upgrade_left','total_work_count','listing_days']+['total_'+s for s in STATS]+['gem_'+s for s in STATS]

def _numeric(frame,column):
    if column not in frame:return pd.Series(0,index=frame.index,dtype='int64')
    return pd.to_numeric(frame[column],errors='coerce').fillna(0).astype('int64')

def _components(name):
    if name in {'마','인'}:return ['INT','MAD']
    return TOTAL_COMPONENTS.get(name,[SIMPLE_STATS[name]] if name in SIMPLE_STATS else [])

def _pushdown(conditions,include_gems):
    clauses=[];args=[]
    for c in conditions:
        if c.name in {'법신','노작','완작'}:continue
        comps=_components(c.name)
        if c.name in {'업횟','작'}:expr='total_upgrade_left' if c.name=='업횟' else 'total_work_count'
        elif comps:
            terms=[f'(total_{s}+gem_{s})' if include_gems else f'total_{s}' for s in comps]
            if c.low==c.high==0 and c.name in TOTAL_COMPONENTS:
                clauses.extend(t+'=0' for t in terms);continue
            expr='('+'+'.join(terms)+')'
        else:continue
        if c.low is not None:clauses.append(expr+'>=?');args.append(c.low)
        if c.high is not None:clauses.append(expr+'<=?');args.append(c.high)
    return clauses,args

@lru_cache(maxsize=4)
def _read_packet_rows_cached(path,size,mtime,codes,tokens=(),include_gems=False):
    del size,mtime
    import duckdb
    conditions=parse_tokens(tokens);clauses,args=_pushdown(conditions,include_gems)
    with duckdb.connect(config={'threads':2,'memory_limit':'256MB'}) as conn:
        available={r[0] for r in conn.execute('DESCRIBE SELECT * FROM read_parquet(?)',[path]).fetchall()}
        cols=[c for c in RAW_COLUMNS if c in available]
        sql='SELECT '+','.join(cols)+' FROM read_parquet(?) WHERE itemCode IN ('+','.join('?' for _ in codes)+')'
        if clauses:sql+=' AND '+' AND '.join(clauses)
        return conn.execute(sql,[path,*codes,*args]).fetchdf()

def read_packet_rows(path,item_codes,tokens=(),include_gems=False):
    path=Path(path);codes=tuple(sorted(set(map(int,item_codes))))
    if not path.exists() or not codes:return pd.DataFrame()
    s=path.stat()
    return _read_packet_rows_cached(str(path.resolve()),s.st_size,s.st_mtime_ns,codes,tuple(tokens),include_gems).copy()

def prepare_rows(frame,catalog=None):
    if frame.empty:return frame.copy()
    frame=frame.copy();catalog=catalog or {}
    for stat in STATS:
        old=_numeric(frame,'base_'+stat)
        bases={code:number(meta.get(BASE_COLUMNS[stat])) for code,meta in catalog.items()}
        frame['base_'+stat]=frame.itemCode.map(bases).fillna(old).astype('int64')
        frame['add_'+stat]=_numeric(frame,'total_'+stat)-frame['base_'+stat]
    for column in ('sheet','itemName','직업'):
        mapped=frame.itemCode.map({c:m.get(column,'') for c,m in catalog.items()}).astype('object')
        frame[column]=mapped.where(mapped.notna(),frame.get(column,pd.Series('',index=frame.index)).astype('object')).fillna('')
    frame['base_upgrade_left']=frame.itemCode.map({c:number(m.get('업횟'),-1) for c,m in catalog.items()}).fillna(-1).astype('int64')
    frame['has_gems']=frame.get('option_codes',pd.Series('',index=frame.index)).fillna('').astype(str).str.contains(r'(?<!\d)(?:600[0-9]|601[01]|1600[0-9]|1601[01]|2600[0-9]|2601[01])(?!\d)',regex=True)
    return frame

def filter_packet_rows(frame,tokens,include_gems=False):
    conditions=parse_tokens(tokens)
    if frame.empty:return frame
    mask=pd.Series(True,index=frame.index)
    for c in conditions:
        if c.name=='노작':mask &= _numeric(frame,'base_upgrade_left').ge(0)&_numeric(frame,'total_upgrade_left').eq(_numeric(frame,'base_upgrade_left'));continue
        if c.name=='완작':mask &= _numeric(frame,'total_work_count').gt(0)&_numeric(frame,'total_upgrade_left').eq(0);continue
        if c.name in {'업횟','작'}:values=_numeric(frame,'total_upgrade_left' if c.name=='업횟' else 'total_work_count')
        else:
            comps=['INT','LUK','MAD'] if c.name=='법신' else _components(c.name)
            prefix='add_' if c.name=='법신' else 'total_'
            terms=[_numeric(frame,prefix+s)+(_numeric(frame,'gem_'+s) if include_gems else 0) for s in comps]
            if c.low==c.high==0 and c.name in TOTAL_COMPONENTS:
                for term in terms:mask &= term.eq(0)
            values=sum(terms,start=pd.Series(0,index=frame.index))
        if c.low is not None:mask &= values.ge(c.low)
        if c.high is not None:mask &= values.le(c.high)
        directions={'신점':('DEX','ACC'),'신민':('ACC','DEX'),'법지':('INT','LUK'),'법행':('LUK','INT')}
        if c.name in directions:
            a,b=directions[c.name];mask &= _numeric(frame,'add_'+a).ge(_numeric(frame,'add_'+b))
    return frame.loc[mask].copy()

def _kst_naive(series):
    v=pd.to_datetime(series,errors='coerce',format='mixed')
    return v.dt.tz_convert('Asia/Seoul').dt.tz_localize(None) if getattr(v.dt,'tz',None) else v

def add_packet_times(frame):
    if frame.empty:return frame.copy()
    work=frame.copy();cap=_kst_naive(work.captured_at)
    internal=_kst_naive(work.get('internal_time',pd.Series('',index=work.index)))
    work['_captured_time']=cap;work['_expiry_at']=internal.where(work.status.eq('active'))
    wall=internal-internal.dt.normalize();anchor=cap.dt.normalize()+wall
    anchor=anchor.where(anchor.le(cap),anchor-pd.Timedelta(days=1))
    near=(cap-anchor).between(pd.Timedelta(0),pd.Timedelta(minutes=10))
    work['_sale_at']=anchor.where(near & work.status.eq('completed'))
    work['_registered_at']=pd.NaT;work['_time_reason']='등록기간 미확인'
    work.loc[work.status.eq('completed'),'_time_reason']='연결할 판매중 자료 없음'
    # Real-time capture: infer either listing period when its reconstructed
    # registration is within one hour before or after the capture, inclusive.
    reg1=internal-pd.Timedelta(days=1);reg3=internal-pd.Timedelta(days=3)
    active=work.status.eq('active');tolerance=pd.Timedelta(hours=1)
    match1=active & (cap-reg1).abs().le(tolerance)
    match3=active & (cap-reg3).abs().le(tolerance)
    if 'listing_days' in work:
        period=pd.to_numeric(work.listing_days,errors='coerce')
        match1 &= period.isna() | period.eq(1)
        match3 &= period.isna() | period.eq(3)
    unique=match1 ^ match3
    work.loc[unique & match1,'_registered_at']=reg1[unique & match1]
    work.loc[unique & match3,'_registered_at']=reg3[unique & match3]
    work.loc[work['_registered_at'].notna(),'_time_reason']=''
    work.loc[work.status.eq('completed') & work['_sale_at'].isna(),'_time_reason']='완료 시각 미확인'
    return work

def deduplicate_active_completed(active,completed,days=3):
    active=add_packet_times(active.reset_index(drop=True));completed=add_packet_times(completed.reset_index(drop=True))
    for col in ('_sale_duration_seconds','_sale_duration_minutes'):completed[col]=pd.Series(pd.NA,index=completed.index,dtype='Int64')
    completed['_linked_active_at']=pd.NaT
    if active.empty or completed.empty:return active,completed,0
    cols=['itemCode','quantity','total_price','total_upgrade_left','total_work_count']+['total_'+s for s in STATS]+['option_codes']
    def fingerprints(f):
        norm=pd.DataFrame({c:(f.get(c,pd.Series('',index=f.index)).fillna('').astype(str) if c=='option_codes' else _numeric(f,c)) for c in cols})
        return pd.util.hash_pandas_object(norm,index=False).to_numpy()
    active['_fp']=fingerprints(active);completed['_fp']=fingerprints(completed)
    groups={}
    for r in active[['_fp','_captured_time']].sort_values('_captured_time',na_position='last').itertuples():
        i,fp,cap=r
        if pd.notna(cap):groups.setdefault(fp,[]).append((cap,i))
    removed=set();gap=pd.Timedelta(days=days)
    registered_times=active['_registered_at'].tolist()
    active_reasons=active['_time_reason'].tolist()
    active_captured=active['_captured_time'].tolist()
    reasons=completed['_time_reason'].tolist()
    seconds_out=[pd.NA]*len(completed);minutes_out=[pd.NA]*len(completed);linked_out=[pd.NaT]*len(completed)
    # Scalar pandas writes are expensive with copy-on-write; collect values in
    # plain lists and assign each typed column once after linking.
    ordered=completed[['_fp','_captured_time','_sale_at']].sort_values('_captured_time',na_position='last')
    for ci,fp,cap,sold in ordered.itertuples(name=None):
        candidates=groups.get(fp,[])
        if not candidates or pd.isna(cap):continue
        hi=bisect.bisect_left(candidates,(cap,-1));lo=bisect.bisect_left(candidates,(cap-gap,-1))
        if hi<=lo:continue
        ambiguous=hi-lo>1
        _,ai=candidates.pop(hi-1);removed.add(ai)
        registered=registered_times[ai]
        if ambiguous:reasons[ci]='동일 옵션 매물 연결 불확실';continue
        if pd.isna(registered) or pd.isna(sold):
            reasons[ci]=active_reasons[ai] if pd.isna(registered) else '완료 시각 미확인';continue
        seconds=(sold-registered).total_seconds()
        if seconds<0:reasons[ci]='완료가 등록보다 빠름';continue
        seconds_out[ci]=int(seconds);minutes_out[ci]=int(seconds//60)
        linked_out[ci]=active_captured[ai];reasons[ci]=''
    completed['_sale_duration_seconds']=pd.array(seconds_out,dtype='Int64')
    completed['_sale_duration_minutes']=pd.array(minutes_out,dtype='Int64')
    completed['_linked_active_at']=pd.to_datetime(linked_out)
    completed['_time_reason']=reasons
    return active.drop(index=list(removed)).drop(columns='_fp').reset_index(drop=True),completed.drop(columns='_fp').reset_index(drop=True),len(removed)

def search_packet_data(active_path,completed_path,item_codes,tokens,include_gems=False,catalog=None):
    parse_tokens(tokens);codes=tuple(item_codes)
    active=filter_packet_rows(prepare_rows(read_packet_rows(active_path,codes,tokens,include_gems),catalog),tokens,include_gems)
    completed=filter_packet_rows(prepare_rows(read_packet_rows(completed_path,codes,tokens,include_gems),catalog),tokens,include_gems)
    active,completed,count=deduplicate_active_completed(active,completed)
    if active.empty and completed.empty:return pd.DataFrame(),count
    combined=pd.concat([f for f in (active,completed) if not f.empty],ignore_index=True)
    combined['_sort_time']=combined['_linked_active_at'].fillna(combined['_captured_time']) if '_linked_active_at' in combined else combined['_captured_time']
    return combined.sort_values('_sort_time',ascending=False,kind='mergesort').reset_index(drop=True),count


def filter_display_rows(frame,status='전체',gem='전체',now=None):
    """UI-only filters; expire active listings without changing raw trade status."""
    if frame.empty:return frame
    now=pd.Timestamp.now(tz='Asia/Seoul') if now is None else pd.Timestamp(now)
    if now.tzinfo is not None:now=now.tz_convert('Asia/Seoul').tz_localize(None)
    expiry=_kst_naive(frame.get('_expiry_at',frame.get('internal_time',pd.Series(pd.NaT,index=frame.index))))
    completed=frame.status.eq('completed')
    expired=~completed & expiry.le(now)
    mask=pd.Series(True,index=frame.index)
    if status=='판매완료':mask &= completed
    elif status=='만료':mask &= expired
    elif status=='판매중':mask &= ~completed & ~expired
    if gem=='무보석':mask &= ~frame.has_gems
    elif gem=='유보석':mask &= frame.has_gems
    return frame.loc[mask]

def format_stat_text(row,prefix='total',include_gems=False):
    parts=[]
    for s in STATS:
        if s in {'PDD','MDD','MP','EVA','MAD'}:continue
        value=number(row.get(prefix+'_'+s))
        if s=='INT':value+=number(row.get(prefix+'_MAD'));label='마'
        else:label=LABELS[s]
        if value:parts.append(f'{label}{value}')
    return ' '.join(parts)

def format_gem_text(row):return ', '.join(LABELS[g.stat]+'+'+str(g.value) for g in decode_gems(row.get('option_codes','')))
item_color_score=color_score
item_color_key=color_key

def format_packet_time(row):
    t=pd.to_datetime(row.get('_linked_active_at'),errors='coerce')
    if pd.isna(t):t=pd.to_datetime(row.get('captured_at'),errors='coerce')
    if pd.isna(t):return ''
    if t.tzinfo is None:t=t.tz_localize('Asia/Seoul')
    seconds=max(0,int((pd.Timestamp.now(tz='Asia/Seoul')-t).total_seconds()))
    return '방금전' if seconds<60 else f'{seconds//60}분전' if seconds<3600 else f'{seconds//3600}시간전' if seconds<86400 else f'{seconds//86400}일전'

def format_sale_duration(row):
    n=row.get('_sale_duration_seconds')
    if str(row.get('status',''))!='completed':return ''
    if pd.isna(n):return '미확인'
    n=number(n)
    return f'{n}초' if n<=100 else f'{max(2,n//60)}분' if n<3600 else f'{n//3600}시간' if n<86400 else f'{n//86400}일'

def packet_view(frame,include_gems=False,prices=None,context=''):
    if frame.empty:return pd.DataFrame()
    records=[];now=pd.Timestamp.now(tz='Asia/Seoul').tz_localize(None)
    for row in frame.to_dict('records'):
        gems=evaluate_gems(row,prices or {},context)
        expiry=pd.to_datetime(row.get('_expiry_at',row.get('internal_time')),errors='coerce')
        completed=row.get('status')=='completed';seconds=row.get('_sale_duration_seconds')
        fast=completed and pd.notna(seconds) and number(seconds)<=120
        state='판매완료' if completed else '만료' if pd.notna(expiry) and expiry<=now else '판매중'
        price=number(row.get('unit_price'));cost=gems['recognized_gem_cost']
        stats=format_stat_text(row);stats_html=escape(stats)
        upgrade=number(row.get('total_upgrade_left'));work=number(row.get('total_work_count'))
        if upgrade>0:
            stats+=f' 업{upgrade}'
            stats_html+=f' <span class="upgrade-left" style="color:#b42318;font-weight:700" title="남은 업횟">업{upgrade}</span>'
        if not gems['has_gems']:
            stats+=f' [ {additional_sum(row)} ]';stats_html+=f' [ {additional_sum(row)} ]'
        else:
            stats='■ '+stats
            stats_html='<span class="gem-marker" style="color:#111111" title="보석 장착">■</span> '+stats_html
        name=str(row.get('itemName',''))+(f' {work}작' if work>0 else '')
        records.append({'상태':state,'시간':format_packet_time(row),'판매소요':format_sale_duration(row),'아이템':name,
            '총스탯':stats,'_총스탯HTML':stats_html,
            '판매가(만)':price_in_man(price),'보석제외가(만)':price_in_man(price-cost),'보석':gems['gem_text'],'인정보석원가(만)':price_in_man(cost),
            '무효 사유':gems['invalid_reasons'],
            '_아이템색':color_key(color_score(row)),'_예상색':predicted_color(row),'_보석HTML':gems['gem_html'],'_보석셀':gems['gem_cell_style'],'_빠른판매':fast,'_시간설명':str(row.get('_time_reason','')),'_code':number(row.get('itemCode'))})
    return pd.DataFrame(records)
