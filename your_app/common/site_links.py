"""Generate browser links only. This module performs no requests."""
from urllib.parse import urlencode
from your_app.common.stat_query import parse_tokens
from your_app.common.config import SHEET_TO_ITEMTYPE

def search_page_url(items,tokens):
    if items.empty:return ''
    row=items.iloc[0]
    exact=len(items)==1
    item_type=SHEET_TO_ITEMTYPE.get(str(row.get('sheet','')))
    if not exact and not item_type:return 'https://mapleland.gg/'
    base=f'https://mapleland.gg/item/{int(row.itemCode)}' if exact else f'https://mapleland.gg/items/{item_type}'
    values={}
    names={'공':'incPAD','마':'Hapma','인':'Hapma','힘':'incSTR','덱':'incDEX','럭':'incLUK','명':'incACC','이속':'incSpeed','점프':'incJump','업횟':'Tuc'}
    for c in parse_tokens(tokens):
        if c.name not in names:continue
        if c.low is not None:values['low'+names[c.name]]=str(c.low)
        if c.high is not None:values['high'+names[c.name]]=str(c.high)
    return base+('?' + urlencode(values) if values else '')
