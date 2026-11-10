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
    assert not app.sidebar.button and not app.title
    assert [field.key for field in app.text_input]==['query','stat1','stat2','stat3']
    assert [field.label for field in app.text_input]==['이름','스탯1','스탯2','스탯3']
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


def test_gem_toggle_and_both_filters_in_real_entrypoint(tmp_path,monkeypatch):
    import your_app.common.remote_data as remote
    root=Path(__file__).resolve().parents[1]
    catalog=json.loads((root/'resources/item_catalog.json').read_text(encoding='utf-8'))
    item=next(r for r in catalog if '네쉐르' in r['itemName'])
    code=item['itemCode']
    pd.DataFrame([
        row(itemCode=code,sheet='활',total_PAD=116,quantity=1),
        row(itemCode=code,sheet='활',total_PAD=113,gem_PAD=3,option_codes='26000,26011,26008',quantity=2),
    ]).to_parquet(tmp_path/'packet_active.parquet')
    pd.DataFrame([row(itemCode=code,sheet='활',total_PAD=116,status='completed',quantity=3)]).to_parquet(tmp_path/'packet_completed.parquet')
    (tmp_path/'gem_prices.json').write_text('{}',encoding='utf-8')
    monkeypatch.setattr(remote,'ensure_data_snapshot',lambda *a,**k:DataSnapshot('filter-fixture','2026-11-10',tmp_path))
    app=AppTest.from_file(str(root/'streamlit_app.py'),default_timeout=30).run()
    app.text_input(key='query').set_value(item['itemName'])
    app.text_input(key='stat1').set_value('공116')
    next(b for b in app.button if b.label=='검색').click().run()
    assert not app.exception and len(app.session_state['rows'])==2
    generation=app.session_state['generation']
    app.toggle(key='packet_include_gems').set_value(True).run()
    assert not app.exception and len(app.session_state['rows'])==3
    assert app.session_state['generation']>generation and app.session_state['page']==1
    app.button_group(key='gem_filter').set_value('유보석').run()
    assert not app.exception and any(c.value.startswith('1건') for c in app.caption)
    app.button_group(key='status_filter').set_value('판매완료').run()
    assert not app.exception and any(c.value.startswith('0건') for c in app.caption)
    app.button_group(key='gem_filter').set_value('전체').run()
    assert any(c.value.startswith('1건') for c in app.caption)
    app.button(key='history_1').click().run()
    assert not app.exception and not app.toggle(key='packet_include_gems').value
    assert len(app.session_state['rows'])==2

    # Changing a field (the same commit used by Tab/blur) searches without a
    # submit button, resets both filters, and preserves widget identities.
    input_ids=[field.id for field in app.text_input]
    app.button_group(key='status_filter').set_value('판매완료').run()
    app.button_group(key='gem_filter').set_value('무보석').run()
    app.text_input(key='stat1').set_value('공113').run()
    assert not app.exception and len(app.session_state['rows'])==1
    assert app.button_group(key='status_filter').value=='전체'
    assert app.button_group(key='gem_filter').value=='전체'
    assert app.session_state['page']==1
    assert [field.id for field in app.text_input]==input_ids
    app.text_input(key='query').set_value('없는품목이름').run()
    assert not app.exception and app.session_state['rows'].empty
    assert any('조건에 맞는 매물' in i.value for i in app.info)

    next(b for b in app.button if b.label=='보석값').click().run()
    assert not app.exception
    html=[node.proto.body for node in app.get('html') if 'gem-price-table' in node.proto.body and '<table' in node.proto.body]
    assert len(html)==1 and html[0].count('<tr>')==13
    assert all(label in html[0] for label in ['상급(만)','중급(만)','하급(만)','인트','덱','마력'])
