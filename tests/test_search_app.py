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
    monkeypatch.setattr(remote,'get_search_snapshot',lambda *args,**kw:DataSnapshot('fixture','2026-11-10',tmp_path))
    def no_network(*args,**kw):raise AssertionError('Search must not call a market API')
    monkeypatch.setattr(requests,'get',no_network)
    app=AppTest.from_file(str(root/'streamlit_app.py'),default_timeout=30).run()
    assert not app.exception
    assert not app.sidebar.button and not app.title
    assert [field.key for field in app.text_input]==['query','stat1','stat2','stat3','calculator_gems']
    assert [field.label for field in app.text_input]==['이름','스탯1','스탯2','스탯3','보석 계산기']
    app.text_input(key='calculator_gems').set_value('공3 덱5 럭5').run()
    assert any('가공비 900만' in element.value for element in app.get('html'))
    assert app.button_group(key='status_filter').options==['전체','판매완료']
    assert all('판매 API' not in b.label and '구매 API' not in b.label for b in app.button)
    def search(value):
        app.text_input(key='query').set_value(item['itemName'])
        app.text_input(key='stat1').set_value(value)
        next(b for b in app.button if b.label=='검색').click().run()
        assert not app.exception
    search('공116')
    assert len(app.session_state['rows'])==105
    assert not app.sidebar.button
    assert app.button(key='history_0').label.endswith('공116')
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
    monkeypatch.setattr(remote,'get_search_snapshot',lambda *a,**k:DataSnapshot('filter-fixture','2026-11-10',tmp_path))
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


def test_stat_marker_applies_gems_to_all_fields_and_restores_from_history(tmp_path,monkeypatch):
    import your_app.common.remote_data as remote
    root=Path(__file__).resolve().parents[1]
    catalog=json.loads((root/'resources/item_catalog.json').read_text(encoding='utf-8'))
    item=next(r for r in catalog if r['itemName'].replace(' ','')=='블루아이젠')
    base=row(itemCode=item['itemCode'],total_DEX=12,total_LUK=8,total_ACC=4,total_upgrade_left=5)
    gemmed=dict(base,total_DEX=7,total_ACC=1,gem_DEX=5,gem_ACC=3,option_codes='26011,16002',quantity=2)
    pd.DataFrame([base,gemmed]).to_parquet(tmp_path/'packet_active.parquet')
    pd.DataFrame([dict(base,status='completed',total_DEX=0)]).to_parquet(tmp_path/'packet_completed.parquet')
    (tmp_path/'gem_prices.json').write_text('{}',encoding='utf-8')
    monkeypatch.setattr(remote,'get_search_snapshot',lambda *a,**k:DataSnapshot('marker-fixture','2026-11-18',tmp_path))
    app=AppTest.from_file(str(root/'streamlit_app.py'),default_timeout=30).run()
    app.text_input(key='query').set_value(f"@{item['itemName']}@")
    app.text_input(key='stat1').set_value('도적20')
    app.text_input(key='stat2').set_value('명4')
    next(b for b in app.button if b.label=='검색').click().run()
    assert not app.exception and not app.error
    assert not app.session_state['applied_include_gems']
    assert app.session_state['rows']['quantity'].tolist()==[1]

    for field,value in (('stat1','@도적20'),('stat1','도적20@'),('stat2','명4@'),('stat3','@업5@')):
        app.text_input(key='stat1').set_value('도적20')
        app.text_input(key='stat2').set_value('명4')
        app.text_input(key='stat3').set_value('')
        app.text_input(key=field).set_value(value).run()
        assert not app.exception and not app.error
        assert app.session_state['applied_include_gems']
        assert set(app.session_state['rows']['quantity'])=={1,2}
        assert app.button_group(key='gem_filter').value=='유보석'
        assert any(c.value.startswith('1건') for c in app.caption)
        assert not app.toggle(key='packet_include_gems').value

    app.text_input(key='stat3').set_value('업5').run()
    assert not app.session_state['applied_include_gems']
    assert app.button_group(key='gem_filter').value=='전체'
    assert app.session_state['rows']['quantity'].tolist()==[1]
    app.button(key='history_1').click().run()
    assert app.text_input(key='stat3').value=='@업5@'
    assert app.session_state['applied_include_gems']
    assert app.button_group(key='gem_filter').value=='유보석'
    assert set(app.session_state['rows']['quantity'])=={1,2}
    app.text_input(key='stat3').set_value('@').run()
    assert not app.error and not app.exception
    assert app.session_state['applied_include_gems']
    assert app.button_group(key='gem_filter').value=='유보석'
    assert '@' not in app.session_state['applied_tokens']


def test_search_markers_combine_gems_and_completed_filters(tmp_path,monkeypatch):
    import your_app.common.remote_data as remote
    root=Path(__file__).resolve().parents[1]
    items=json.loads((root/'resources/item_catalog.json').read_text(encoding='utf-8'))
    item=next(r for r in items if '네쉐르' in r['itemName'])
    body=row(itemCode=item['itemCode'],total_PAD=116,quantity=1)
    gemmed=dict(body,total_PAD=113,gem_PAD=3,option_codes='26000',quantity=2)
    pd.DataFrame([dict(body,quantity=3),dict(gemmed,quantity=4)]).to_parquet(tmp_path/'packet_active.parquet')
    pd.DataFrame([dict(body,status='completed'),dict(gemmed,status='completed')]).to_parquet(tmp_path/'packet_completed.parquet')
    (tmp_path/'gem_prices.json').write_text('{}',encoding='utf-8')
    monkeypatch.setattr(remote,'get_search_snapshot',lambda *a,**k:DataSnapshot('combined-marker-fixture','2026-11-19',tmp_path))
    app=AppTest.from_file(str(root/'streamlit_app.py'),default_timeout=30).run()
    app.text_input(key='query').set_value(item['itemName'])
    app.text_input(key='stat1').set_value('@$공116').run()
    assert not app.exception and not app.error
    assert app.session_state['applied_include_gems']
    assert app.button_group(key='status_filter').value=='판매완료'
    assert app.button_group(key='gem_filter').value=='유보석'
    assert any(c.value.startswith('1건') for c in app.caption)

    app.text_input(key='stat1').set_value('공116#$').run()
    assert not app.exception and not app.error
    assert not app.session_state['applied_include_gems']
    assert app.button_group(key='gem_filter').value=='무보석'
    assert any(c.value.startswith('1건') for c in app.caption)

    app.text_input(key='query').set_value(f'#{item["itemName"]}$')
    app.text_input(key='stat1').set_value('공116').run()
    assert not app.exception and not app.error
    assert any(c.value.startswith('1건') for c in app.caption)
    app.button(key='history_2').click().run()
    assert app.text_input(key='stat1').value=='@$공116'
    assert app.button_group(key='gem_filter').value=='유보석'
    assert any(c.value.startswith('1건') for c in app.caption)
