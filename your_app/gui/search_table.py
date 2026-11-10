"""Escaped, paginated HTML table: partial gem colors without per-row widgets."""
from html import escape
import pandas as pd
from your_app.domain.search_rules import NAME_COLORS

COLUMNS=['상태','시간','판매소요','아이템','총스탯','판매가(만)','보석제외가(만)','보석','인정보석원가(만)','무효 사유']
COLUMN_WIDTHS={'상태':72,'시간':60,'판매소요':66,'아이템':180,'총스탯':216,'판매가(만)':90,'보석제외가(만)':100,'보석':200,'인정보석원가(만)':100,'무효 사유':144}
HEADER_LABELS={'인정보석원가(만)':'보석원가(만)'}
COLOR_NAMES={'white':'흰색','gray':'회색','blue':'파랑','purple':'보라','yellow':'노랑','lime':'연두','red':'빨강'}
STYLE='''<style>
.search-grid {overflow:auto;max-height:70vh;min-height:150px;border:1px solid #d9dfeb;border-radius:9px;background:#fff;scroll-behavior:auto;}
.search-grid table {border-collapse:separate;border-spacing:0;table-layout:fixed;max-width:100%;min-width:920px;font-size:16px;line-height:1.4;color:#202733;white-space:nowrap;}
.search-grid th {position:sticky;top:0;z-index:2;background:#edf2fa;padding:7px 6px;text-align:left;border-bottom:1px solid #ccd5e4;font-size:14px;font-weight:750;}
.search-grid td {padding:6px;border-bottom:1px solid #e7ebf2;vertical-align:middle;font-weight:550;}
.search-grid tr:hover td {box-shadow:inset 0 0 0 999px #00000004;}
.search-grid .completed {background:#f1eafa;}.search-grid .fast {background:#ffe0e0;}
.search-grid .gem-red {background:#ffdede;}.search-grid .gem-green {background:#e5f4dd;}
.search-grid .fast td {background:#ffe0e0;}
.search-grid .num {text-align:right;font-variant-numeric:tabular-nums;font-weight:750;}
.search-grid .name {font-weight:750;white-space:normal;overflow-wrap:anywhere;}
.search-grid .warning {color:#9e2929;white-space:normal;overflow-wrap:anywhere;font-size:14px;}
.search-grid .stats {white-space:normal;overflow-wrap:anywhere;font-weight:650;}
.search-grid .minor {font-size:14px;font-weight:500;}
.search-grid .gem-cell {white-space:normal;line-height:1.35;}
.search-grid .gem-cell span {display:inline-block;white-space:nowrap;}
.search-grid .gem-marker {color:#111111;margin-right:2px;font-weight:800;}
@media(max-width:850px){.search-grid table{font-size:15px}.search-grid td,.search-grid th{padding:8px}.search-grid{max-height:65vh}}
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
            if col in {'상태','시간','판매소요'}:cls+=' minor'
            if col=='무효 사유':cls+=' warning'
            if col=='판매소요':title=r['_시간설명'] or '패킷 원본 시각으로 계산'
            if col=='시간':title='연결된 완료 매물은 판매중 자료의 수집 시각, 그 외는 자기 수집 시각'
            cells.append(f'<td class="{cls}" title="{escape(title,quote=True)}">{value}</td>')
        rows.append(f'<tr class="{css}">'+''.join(cells)+'</tr>')
    header=''.join(f'<th scope="col" title="{escape(c,quote=True)}">{escape(HEADER_LABELS.get(c,c))}</th>' for c in columns)
    colgroup='<colgroup>'+''.join(f'<col style="width:{COLUMN_WIDTHS[c]/total_width*100:.3f}%">' for c in columns)+'</colgroup>'
    return STYLE+f'<div class="search-grid" tabindex="0" role="region" aria-label="아이템 검색 결과"><table style="width:{total_width}px">'+colgroup+'<thead><tr>'+header+'</tr></thead><tbody>'+''.join(rows)+'</tbody></table></div>'
