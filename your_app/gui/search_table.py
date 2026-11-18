"""Escaped, paginated HTML table: partial gem colors without per-row widgets."""
from html import escape
import pandas as pd
from your_app.domain.search_rules import NAME_COLORS

COLUMNS=['상태','시간','판매소요','아이템','총스탯','판매가(만)','보석제외가(만)','보석','인정보석원가(만)','무효 사유']
COLUMN_WIDTHS={'상태':92,'시간':76,'판매소요':86,'아이템':220,'총스탯':272,'판매가(만)':112,'보석제외가(만)':130,'보석':236,'인정보석원가(만)':120,'무효 사유':184}
HEADER_LABELS={'인정보석원가(만)':'보석원가(만)'}
COLOR_NAMES={'white':'흰색','gray':'회색','blue':'파랑','purple':'보라','yellow':'노랑','lime':'연두','red':'빨강'}
STYLE='''<style>
.search-grid {overflow:auto;max-height:70vh;min-height:150px;border:1px solid #d9dfeb;border-radius:9px;background:#fff;scroll-behavior:auto;}
.search-grid table {width:100%;min-width:1100px;border-collapse:separate;border-spacing:0;table-layout:fixed;font-size:18px;line-height:1.4;color:#202733;white-space:nowrap;}
.search-grid table.has-warning {min-width:1240px;}
.search-grid th {position:sticky;top:0;z-index:2;background:#edf2fa;padding:10px;text-align:left;border-bottom:1px solid #cdd7e5;font-size:16px;font-weight:750;}
.search-grid td {height:47px;padding:9px 10px;border-bottom:1px solid #e0e6ee;vertical-align:middle;font-weight:550;}
.search-grid :is(th,td):not(:last-child) {border-right:1px solid #dfe5ee;}
.search-grid tr:hover td {box-shadow:inset 0 0 0 999px #00000004;}
.search-grid .completed {background:#f1eafa;}
.search-grid .fast {background:#ffe0e0;}
.search-grid :is(.gem-red,.gem-difference-warning) {background:#f2858b;}
.search-grid .gem-green {background:#e6f4df;}
.search-grid .gem-price-warning {color:#c0202d;}
.search-grid .gem-difference-warning.gem-price-warning {color:#650c1c;}
.search-grid .num {text-align:right;font-variant-numeric:tabular-nums;font-weight:750;}
.search-grid :is(.name,.warning,.stats,.gem-cell) {white-space:normal;word-break:keep-all;overflow-wrap:anywhere;}
.search-grid .name {font-size:19px;font-weight:750;}
.search-grid .warning {color:#9e2929;font-size:16px;}
.search-grid .stats {font-weight:650;}
.search-grid .minor {font-size:16px;font-weight:550;}
.search-grid .gem-token {display:inline-block;white-space:nowrap;font-weight:650;}
.search-grid .gem-upper {color:#0052cc;}
.search-grid .gem-lower {color:#c0202d;}
.search-grid .gem-red .gem-upper {color:#00235f;}
.search-grid .gem-red .gem-lower {color:#650c1c;}
.search-grid .gem-marker {color:#111111;margin-right:2px;font-weight:800;}
</style>'''

def render_table(view):
    has_warning=view.get('무효 사유',pd.Series(dtype='object')).fillna('').astype(str).str.strip().ne('').any()
    columns=[c for c in COLUMNS if c!='무효 사유' or has_warning]
    total_width=sum(COLUMN_WIDTHS[c] for c in columns)
    rows=[]
    for r in view.to_dict('records'):
        css='fast' if r['_빠른판매'] else 'completed' if r['상태']=='판매완료' else ''
        cells=[]
        for col in columns:
            value=r.get(col,'');cls='';title=''
            if col=='보석':value=r['_보석HTML'];cls='gem-cell gem-'+r['_보석셀']
            elif col=='총스탯':value=r.get('_총스탯HTML',escape(str(value)));cls='stats'
            elif col=='아이템':
                prefix=''
                if r['_예상색']:
                    k=r['_예상색'];prefix=f'<span style="color:{NAME_COLORS[k]}">({COLOR_NAMES[k]})</span> '
                value=prefix+f'<span style="color:{NAME_COLORS[r["_아이템색"]]}">{escape(str(value))}</span>';cls='name'
            else:
                if col.endswith('(만)') and isinstance(value,(int,float)):value=f'{value:,.0f}'
                value=escape(str(value))
            if col.endswith('(만)'):cls+=' num'
            if col in {'보석제외가(만)','인정보석원가(만)'} and r.get('_보석가격경고'):cls+=' gem-price-warning'
            if col=='보석제외가(만)' and r.get('_차액경고'):cls+=' gem-difference-warning'
            if col in {'상태','시간','판매소요'}:cls+=' minor'
            if col=='무효 사유':cls+=' warning'
            if col=='판매소요':title=r['_시간설명'] or '패킷 원본 시각으로 계산'
            if col=='시간':title='연결된 완료 매물은 판매중 자료의 수집 시각, 그 외는 자기 수집 시각'
            cells.append(f'<td class="{cls}" title="{escape(title,quote=True)}">{value}</td>')
        rows.append(f'<tr class="{css}">'+''.join(cells)+'</tr>')
    header=''.join(f'<th scope="col" title="{escape(c,quote=True)}">{escape(HEADER_LABELS.get(c,c))}</th>' for c in columns)
    colgroup='<colgroup>'+''.join(f'<col style="width:{COLUMN_WIDTHS[c]/total_width*100:.3f}%">' for c in columns)+'</colgroup>'
    table_class='has-warning' if has_warning else ''
    return STYLE+f'<div class="search-grid" tabindex="0" role="region" aria-label="아이템 검색 결과"><table class="{table_class}">'+colgroup+'<thead><tr>'+header+'</tr></thead><tbody>'+''.join(rows)+'</tbody></table></div>'
