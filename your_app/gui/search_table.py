"""Escaped, paginated HTML table: partial gem colors without per-row widgets."""
from html import escape
import pandas as pd
from your_app.domain.search_rules import NAME_COLORS

COLUMNS=['상태','시간','판매소요','아이템','총스탯','추가옵 합','업횟','작횟','판매가(만)','보석제외가(만)','보석','인정보석원가(만)','무효 사유','만료 예정','남은 시간']
COLOR_NAMES={'white':'흰색','gray':'회색','blue':'파랑','purple':'보라','yellow':'노랑','lime':'연두','red':'빨강'}
STYLE='''<style>
.search-grid {overflow:auto;max-height:70vh;min-height:150px;border:1px solid #d9dfeb;border-radius:9px;background:#fff;scroll-behavior:auto;}
.search-grid table {border-collapse:separate;border-spacing:0;width:100%;font-size:14px;line-height:1.5;color:#202733;white-space:nowrap;}
.search-grid th {position:sticky;top:0;z-index:2;background:#edf2fa;padding:11px 12px;text-align:left;border-bottom:1px solid #ccd5e4;font-weight:700;}
.search-grid td {padding:10px 12px;border-bottom:1px solid #e7ebf2;vertical-align:middle;}
.search-grid tr:hover td {box-shadow:inset 0 0 0 999px #00000004;}
.search-grid .completed {background:#f1eafa;}.search-grid .fast {background:#ffe0e0;}
.search-grid .gem-red {background:#ffdede;}.search-grid .gem-green {background:#e5f4dd;}
.search-grid .fast td {background:#ffe0e0;}
.search-grid .num {text-align:right;font-variant-numeric:tabular-nums;}.search-grid .name {font-weight:800;}
.search-grid .warning {color:#9e2929;white-space:normal;min-width:160px;max-width:260px;}
.search-grid .stats {white-space:normal;min-width:210px;max-width:360px;}
@media(max-width:850px){.search-grid table{font-size:13px}.search-grid td,.search-grid th{padding:8px}.search-grid{max-height:65vh}}
</style>'''

def render_table(view):
    rows=[]
    for r in view.to_dict('records'):
        css='fast' if r['_빠른판매'] else 'completed' if r['상태']=='판매완료' else ''
        cells=[]
        for col in COLUMNS:
            value=r.get(col,'');cls='';title=''
            if col=='보석':value=r['_보석HTML'];cls='gem-'+r['_보석셀']
            elif col=='아이템':
                prefix=''
                if r['_예상색']:
                    k=r['_예상색'];prefix=f'<span style="color:{NAME_COLORS[k]}">({COLOR_NAMES[k]})</span> '
                value=prefix+f'<span style="color:{NAME_COLORS[r["_아이템색"]]}">{escape(str(value))}</span>';cls='name'
            else:
                if col.endswith('(만)') and isinstance(value,(int,float)):value=f'{value:,.2f}'.rstrip('0').rstrip('.')
                value=escape(str(value))
            if col.endswith('(만)') or col in {'추가옵 합','업횟','작횟'}:cls+=' num'
            if col=='총스탯':cls+=' stats'
            if col=='무효 사유':cls+=' warning'
            if col=='판매소요':title=r['_시간설명'] or '패킷 원본 시각으로 계산'
            if col=='시간':title='연결된 완료 매물은 판매중 자료의 수집 시각, 그 외는 자기 수집 시각'
            cells.append(f'<td class="{cls}" title="{escape(title,quote=True)}">{value}</td>')
        rows.append(f'<tr class="{css}">'+''.join(cells)+'</tr>')
    header=''.join(f'<th scope="col">{escape(c)}</th>' for c in COLUMNS)
    return STYLE+'<div class="search-grid" tabindex="0" role="region" aria-label="아이템 검색 결과"><table><thead><tr>'+header+'</tr></thead><tbody>'+''.join(rows)+'</tbody></table></div>'
