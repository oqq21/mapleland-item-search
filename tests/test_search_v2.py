from pathlib import Path
import pandas as pd
import pytest
from your_app.common.stat_query import parse_token
from your_app.common.query_utils import mask_for_item_query
from your_app.common.site_links import search_page_url
from your_app.domain.search_rules import evaluate_gems, additional_sum, predicted_color, STATS
from your_app.processing.packet_search import filter_packet_rows,prepare_rows,deduplicate_active_completed,packet_view,search_packet_data
from your_app.gui.search_table import render_table

def row(**kw):
    r={'itemCode':1072000,'itemName':'테스트 신발','sheet':'신발','직업':'궁수','status':'active','captured_at':'2026-11-10 10:00:05','internal_time':'2026-11-13 10:00:00','quantity':1,'total_price':100_000_000,'unit_price':100_000_000,'option_codes':'','total_upgrade_left':0,'total_work_count':5,'base_upgrade_left':5}
    for s in STATS:r.update({'total_'+s:0,'base_'+s:0,'add_'+s:0,'gem_'+s:0})
    return {**r,**kw}

@pytest.mark.parametrize('token,name,low,high',[('궁 30~32','궁수',30,32),('도~25','도적',None,25),('전20~','전사',20,None),('인트129','인',129,129),('명중3','명',3,3),('이2','이속',2,2),('단30','단도',30,30)])
def test_aliases_and_ranges(token,name,low,high):
    c=parse_token(token);assert(c.name,c.low,c.high)==(name,low,high)

@pytest.mark.parametrize('token',['궁수','궁수10~2','공>100','도적=','없는3','공100abc','궁수~~3'])
def test_invalid_input_is_not_silently_ignored(token):
    with pytest.raises(ValueError):filter_packet_rows(pd.DataFrame(),[token])

def test_magic_sum_direction_uses_additional_not_total_or_gem():
    frame=pd.DataFrame([row(total_INT=5,total_LUK=9,total_MAD=80,add_INT=2,add_LUK=1,gem_LUK=5),row(itemCode=1072001,total_INT=5,total_LUK=9,total_MAD=0,add_INT=0,add_LUK=1)])
    assert len(filter_packet_rows(frame,['법사94','법지94']))==1
    assert len(filter_packet_rows(frame,['법지99'],True))==1
    assert filter_packet_rows(frame,['법지14']).empty

def test_zero_job_does_not_allow_canceling_components():
    f=pd.DataFrame([row(total_STR=-1,total_DEX=1),row(itemCode=2)])
    assert filter_packet_rows(f,['궁0']).itemCode.tolist()==[2]


def test_zero_direction_still_compares_additional_values():
    f=pd.DataFrame([row(total_INT=0,total_LUK=0,total_MAD=0,add_INT=-1,add_LUK=0),row(itemCode=2)])
    assert filter_packet_rows(f,['법지0']).itemCode.tolist()==[2]


def test_class_alias_includes_multi_class_items():
    f=pd.DataFrame({'itemCode':[1,2,3],'itemName':['a','b','c'],'sheet':['신발']*3,'직업':['전사,도적','궁수','전사 / 궁수']})
    assert f.loc[mask_for_item_query(f,'전사신발')].itemCode.tolist()==[1,3]

def test_newitemp_zero_overrides_old_base_and_no_work_uses_slots():
    f=prepare_rows(pd.DataFrame([row(total_INT=7,base_INT=5,total_upgrade_left=5,total_work_count=0)]),{1072000:{'인':0,'업횟':7,'itemName':'이름','sheet':'신발'}})
    assert f.iloc[0].add_INT==7
    assert filter_packet_rows(f,['노작']).empty
    assert len(filter_packet_rows(f,['업5']))==1

def test_no_gem_weapon_is_not_red_but_reverse_is_invalid():
    assert evaluate_gems(row(sheet='활',itemName='네쉐르'),{})['invalid_reasons']==''
    assert '리버스 무보석' in evaluate_gems(row(sheet='활',itemName='리버스 네쉐르'),{})['invalid_reasons']

def test_recognized_cost_excludes_useless_gem_and_includes_only_its_fees():
    prices={'26008':1_000_000,'26011':2_000_000,'26010':50_000_000}
    result=evaluate_gems(row(option_codes='26008,26011,26010'),prices)
    assert result['recognized_gem_cost']==9_750_000
    assert result['gem_valid']
    assert '#595959' in result['gem_html']

def test_all_useless_gems_mean_no_common_fee():
    r=evaluate_gems(row(option_codes='26010'),{'26010':50_000_000})
    assert r['recognized_gem_cost']==0 and '필수 누락' in r['invalid_reasons']

def test_armor_grade_boundary_uses_actual_listing_minus_full_cost():
    r=row(option_codes='16008,16011',unit_price=105_250_000)
    # 225 + 150 + 150 = 525만, materials zero. Exactly 1억 requires upper.
    assert '상급 부족' in evaluate_gems(r,{})['invalid_reasons']
    r['unit_price']-=1
    assert evaluate_gems(r,{})['gem_valid']

def test_weapon_sixty_percent_boundary_and_mage_luk_optional():
    r=row(sheet='완드',직업='법사',option_codes='26001,26009,26003',unit_price=20_000_000)
    prices={'26001':1_000_000,'26009':1_000_000,'26003':1_000_000}
    assert evaluate_gems(r,prices)['recognized_gem_cost']==12_000_000
    assert '60%' in evaluate_gems(r,prices)['invalid_reasons']
    r['unit_price']+=1
    assert evaluate_gems(r,prices)['gem_valid']

def test_reverse_has_no_extra_maker_fees():
    result=evaluate_gems(row(itemName='리버스 신발',option_codes='26008,26011'),{'26008':100,'26011':200})
    assert result['recognized_gem_cost']==300

def test_common_int_gear_does_not_force_luk_even_in_mage_search():
    r=row(직업='',option_codes='26009,26003,26006')
    result=evaluate_gems(r,{},context='법사')
    assert result['gem_valid'] and '럭' not in result['invalid_reasons']

def test_search_display_total_stats_gems_separate_and_hidden_stats_count():
    r=row(total_INT=7,total_MAD=120,total_EVA=9,total_MP=80,add_DEX=20,add_MAD=1,add_PDD=1,add_HP=20)
    f=packet_view(pd.DataFrame([r]),True)
    assert '마127' in f.iloc[0]['총스탯'] and '回' not in f.iloc[0]['총스탯']
    assert '회피' not in f.iloc[0]['총스탯'] and 'MP' not in f.iloc[0]['총스탯']
    assert f.iloc[0]['총스탯'].endswith('[ 24 ]')
    assert '추가옵 합' not in f.columns
    r.update(option_codes='16011',gem_DEX=3,total_DEX=10)
    f=packet_view(pd.DataFrame([r]),True,prices={'16011':100})
    assert '덱10' in f.iloc[0]['총스탯'] and '덱13' not in f.iloc[0]['총스탯']
    assert '[' not in f.iloc[0]['총스탯'] and '#8A4B08' in f.iloc[0]['_보석HTML']

def test_time_crosses_midnight_and_keeps_uncertain_one_day_unknown():
    a=pd.DataFrame([row(captured_at='2026-11-09 23:59:45',internal_time='2026-11-12 23:59:40')])
    c=pd.DataFrame([row(status='completed',captured_at='2026-11-10 00:00:25',internal_time='2026-11-10 00:00:20')])
    _,linked,count=deduplicate_active_completed(a,c)
    assert count==1 and linked.iloc[0]['_sale_duration_seconds']==40
    assert packet_view(linked).iloc[0]['_빠른판매']
    a.loc[0,'internal_time']='2026-11-10 23:59:40'
    _,linked,_=deduplicate_active_completed(a,c)
    assert pd.isna(linked.iloc[0]['_sale_duration_seconds'])
    assert not packet_view(linked).iloc[0]['_빠른판매']

def test_multiple_identical_active_listings_do_not_produce_fast_sale():
    a=pd.DataFrame([row(),row(captured_at='2026-11-10 10:00:06')])
    c=pd.DataFrame([row(status='completed',captured_at='2026-11-10 10:01:02',internal_time='2026-11-10 10:01:00')])
    _,linked,_=deduplicate_active_completed(a,c)
    assert pd.isna(linked.iloc[0]['_sale_duration_seconds'])

def test_capture_delay_over_ten_minutes_is_unknown():
    a=pd.DataFrame([row()]);c=pd.DataFrame([row(status='completed',captured_at='2026-11-10 10:30:01',internal_time='2026-11-10 10:01:00')])
    _,linked,_=deduplicate_active_completed(a,c)
    assert pd.isna(linked.iloc[0]['_sale_duration_seconds'])

def test_class_and_cloak_aliases_and_strength_dagger():
    f=pd.DataFrame({'itemCode':[1,2,1102101,1102102,1102104,3,4],'itemName':['a']*7,'sheet':['신발','신발','망토','망토','망토','단검','단검'],'직업':['도적','궁수','','','','도적','도적'],'힘':[0,0,0,0,0,0,2]})
    assert f.loc[mask_for_item_query(f,'도적 신발')].itemCode.tolist()==[1]
    assert f.loc[mask_for_item_query(f,'신이속')].itemCode.tolist()==[1102101,1102104]
    assert f.loc[mask_for_item_query(f,'단도')].itemCode.tolist()==[4]

def test_html_escapes_packet_text_and_preserves_gem_colors():
    view=packet_view(pd.DataFrame([row(itemName='<script>alert(1)</script>',option_codes='26008,16011,26010')]))
    text=render_table(view)
    assert '<script>' not in text and '&lt;script&gt;' in text
    assert '#174EA6' in text and '#8A4B08' in text and '#595959' in text

def test_external_search_is_a_plain_link():
    f=pd.DataFrame([{'itemCode':1452000,'sheet':'활'}])
    assert search_page_url(f,['공116'])=='https://mapleland.gg/item/1452000?lowincPAD=116&highincPAD=116'

def test_sql_pushdown_and_linked_sort_on_real_parquet_shape(tmp_path):
    active=pd.DataFrame([row(itemCode=1072000,total_DEX=10),row(itemCode=1072001,total_DEX=11,captured_at='2026-11-10 10:00:30')])
    completed=pd.DataFrame([row(itemCode=1072000,total_DEX=10,status='completed',captured_at='2026-11-10 10:01:05',internal_time='2026-11-10 10:01:00')])
    a=tmp_path/'a.parquet';c=tmp_path/'c.parquet';active.to_parquet(a);completed.to_parquet(c)
    found,_=search_packet_data(a,c,[1072000,1072001],['덱10~11'])
    assert found.itemCode.tolist()==[1072001,1072000]
    assert found.iloc[1]['_sale_duration_seconds']==60
