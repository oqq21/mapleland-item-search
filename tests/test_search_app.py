"""Run the real Streamlit entrypoint with a small local snapshot and no network."""
import json
from pathlib import Path
import pandas as pd
from streamlit.testing.v1 import AppTest
from your_app.common.remote_data import DataSnapshot
from tests.test_search_v2 import row

def test_search_history_pagination_and_no_market_api(tmp_path,monkeypatch):
    import your_app.common.remote_data as remote
    import requests
    root=Path(__file__).resolve().parents[1]
    catalog=json.loads((root/'resources/item_catalog.json').read_text(encoding='utf-8'))
    item=next(r for r in catalog if '네쉐르' in r['itemName'])
    code=item['itemCode']
    pd.DataFrame([row(itemCode=code,itemName=item['itemName'],sheet='활',total_PAD=116,quantity=i+1) for i in range(105)]).to_parquet(tmp_path/'packet_active.parquet')
    pd.DataFrame([row(itemCode=code,itemName=item['itemName'],sheet='활',total_PAD=117,status='completed')]).to_parquet(tmp_path/'packet_completed.parquet')
    (tmp_path/'gem_prices.json').write_text('{}',encoding='utf-8')
    monkeypatch.setattr(remote,'ensure_data_snapshot',lambda *args,**kw:DataSnapshot('fixture','2026-11-10',tmp_path))
    def no_network(*args,**kw):raise AssertionError('Search must not call a market API')
    monkeypatch.setattr(requests,'get',no_network)
    app=AppTest.from_file(str(root/'streamlit_app.py'),default_timeout=30).run()
    assert not app.exception
    assert all('판매 API' not in b.label and '구매 API' not in b.label for b in app.button)
    def search(value):
        app.text_input(key='query').set_value(item['itemName'])
        app.text_input(key='stat1').set_value(value)
        next(b for b in app.button if b.label=='검색').click().run()
        assert not app.exception
    search('공116')
    assert len(app.session_state['rows'])==105
    next(b for b in app.button if b.label=='다음').click().run()
    assert app.session_state['page']==2
    search('공117')
    assert app.session_state['page']==1 and len(app.session_state['rows'])==1
    app.button(key='history_1').click().run()
    assert app.session_state['page']==1 and len(app.session_state['rows'])==105
    search('공>116')
    assert app.error and not app.exception
