"""Behavior checks against the final search requirements, including boundaries."""
import pandas as pd
import pytest
from tests.test_search_v2 import row
from your_app.domain.search_rules import color_key, color_score, predicted_color, gem_profile, evaluate_gems
from your_app.processing.packet_search import filter_packet_rows, packet_view, search_packet_data, prepare_rows
from your_app.gui.search_table import render_table


@pytest.mark.parametrize('sheet,job,context,required,optional',[
    ('신발','전사','',{'STR','DEX','ACC'},set()),
    ('장갑','법사','',{'INT','LUK'},{'HP','EVA'}),
    ('신발','법사','',{'INT','LUK'},{'HP','EVA'}),
    ('전신','궁수','',{'STR','DEX'},{'HP','EVA'}),
    ('장갑','도적','',{'DEX','LUK'},{'HP','EVA'}),
    ('신발','도적','섀도어',{'STR','DEX','LUK'},set()),
    ('모자','해적','',{'STR','DEX'},{'HP','EVA'}),
    ('창','전사','',{'PAD','STR'},{'DEX','ACC'}),
    ('완드','법사','',{'MAD','INT'},{'LUK','EVA'}),
    ('활','궁수','',{'PAD','DEX'},{'STR','EVA'}),
    ('석궁','궁수','',{'PAD','DEX'},{'STR','EVA'}),
    ('아대','도적','',{'PAD','LUK'},{'DEX','EVA','HP'}),
    ('단검','도적','',{'PAD','LUK'},{'STR','DEX'}),
    ('너클','해적','',{'PAD','STR'},{'DEX','ACC'}),
    ('총','해적','',{'PAD','DEX'},{'STR','EVA','HP'}),
])
def test_all_class_gem_profiles(sheet,job,context,required,optional):
    actual_required,actual_optional,applicable=gem_profile(sheet,job,(),context)
    assert applicable and actual_required==required and actual_optional==optional


@pytest.mark.parametrize('value,expected',[(-1,'gray'),(0,'white'),(5,'white'),(6,'blue'),(22,'blue'),(23,'purple'),(39,'purple'),(40,'yellow'),(54,'yellow'),(55,'lime'),(69,'lime'),(70,'red')])
def test_every_name_color_boundary(value,expected):
    assert color_key(value)==expected


def test_color_uses_magic_and_hidden_stats_but_not_base():
    r=row(base_INT=100,add_MAD=20,add_PDD=1,add_MDD=1,add_EVA=1,add_MP=20,gem_INT=5)
    assert color_score(r)==30
    assert packet_view(pd.DataFrame([r])).iloc[0]['_아이템색']=='purple'


def test_prediction_limits_and_equipped_items():
    assert predicted_color(row(add_DEX=25))=='yellow'
    assert predicted_color(row(add_DEX=24))==''
    assert predicted_color(row(sheet='활',add_PAD=27))=='yellow'
    assert predicted_color(row(sheet='활',add_PAD=26))==''
    assert predicted_color(row(add_DEX=30,option_codes='26011'))==''
    assert predicted_color(row(sheet='귀고리',add_DEX=30))==''


@pytest.mark.parametrize('token,fields,expected',[
    ('전6',{'total_STR':1,'total_DEX':2,'total_ACC':3},True),
    ('궁3',{'total_STR':1,'total_DEX':2},True),
    ('도5',{'total_DEX':2,'total_LUK':3},True),
    ('단6',{'total_STR':1,'total_DEX':2,'total_LUK':3},True),
    ('법사10',{'total_INT':1,'total_LUK':2,'total_MAD':7},True),
    ('인트8',{'total_INT':1,'total_MAD':7},True),
    ('법신0',{'add_INT':-1,'add_LUK':1,'add_MAD':0},True),
    ('신점6',{'total_STR':1,'total_DEX':2,'total_ACC':3,'add_DEX':-1,'add_ACC':0},False),
    ('신민6',{'total_STR':1,'total_DEX':2,'total_ACC':3,'add_DEX':-1,'add_ACC':0},True),
    ('법지10',{'total_INT':1,'total_LUK':2,'total_MAD':7,'add_INT':1,'add_LUK':1},True),
    ('법행10',{'total_INT':1,'total_LUK':2,'total_MAD':7,'add_INT':1,'add_LUK':1},True),
])
def test_each_stat_sum_and_work_direction(token,fields,expected):
    assert bool(len(filter_packet_rows(pd.DataFrame([row(**fields)]),[token])))==expected


def test_optional_grade_and_useless_gem_do_not_invalidate_valid_armor():
    result=evaluate_gems(row(option_codes='26008,26011,16006',unit_price=200_000_000),{})
    assert result['gem_valid'] and '#8A4B08' in result['gem_html']
    useless=evaluate_gems(row(option_codes='26008,26011,26010',unit_price=200_000_000),{'26010':99_000_000})
    assert useless['gem_valid'] and useless['recognized_gem_cost']==6_750_000


def test_gem_excluded_price_is_full_cost_and_may_be_negative():
    view=packet_view(pd.DataFrame([row(option_codes='26008,26011',unit_price=1_000_000)]),prices={'26008':2_000_000,'26011':1_000_000})
    assert view.iloc[0]['인정보석원가(만)']==975
    assert view.iloc[0]['보석제외가(만)']==-875


def test_fast_sale_boundary_and_completed_red_priority():
    view=packet_view(pd.DataFrame([
        row(status='completed',_sale_duration_seconds=59),
        row(status='completed',_sale_duration_seconds=120),
        row(status='completed',_sale_duration_seconds=121),
        row(status='completed',_sale_duration_seconds=pd.NA),
    ]))
    assert view['_빠른판매'].tolist()==[True,True,False,False]
    assert view.iloc[0]['판매소요']=='59초'
    html=render_table(view)
    assert html.count('<tr class="fast">')==2 and html.count('<tr class="completed">')==2


def test_expired_listing_not_treated_as_completed():
    view=packet_view(pd.DataFrame([row(_expiry_at=pd.Timestamp('2020-01-01'))]))
    assert view.iloc[0]['상태']=='만료 / 완료 미확인'
    assert view.iloc[0]['남은 시간']=='만료'


@pytest.mark.parametrize('tokens,include_gems',[
    (['공100'],False),(['덱~8'],False),(['궁3~10'],False),(['법신0'],False),
    (['도7~'],True),(['신점0'],False),(['업0','작5'],False),(['완작'],False),
])
def test_parquet_predicate_matches_in_memory_filter(tmp_path,tokens,include_gems):
    source=pd.DataFrame([row(itemCode=1,total_PAD=100,total_DEX=2,total_STR=1,gem_LUK=5),row(itemCode=2,total_PAD=101,total_DEX=8,total_LUK=1)])
    active=tmp_path/'active.parquet';completed=tmp_path/'completed.parquet'
    source.to_parquet(active);source.iloc[:0].to_parquet(completed)
    expected=filter_packet_rows(prepare_rows(source),tokens,include_gems).itemCode.tolist()
    actual,_=search_packet_data(active,completed,[1,2],tokens,include_gems)
    assert sorted(actual.itemCode.tolist() if not actual.empty else [])==sorted(expected)
