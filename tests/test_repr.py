"""Text representations identify MARTHE objects and preserve their content."""

import ast
from copy import deepcopy

import pandas as pd
import pytest

from martpy.inputs import MartHisto, MartLiais, MartParams, MartTimeSteps


@pytest.fixture(params=['histo', 'liais'])
def mart_dataframe(request):
    if request.param == 'histo':
        return MartHisto.from_histo_file(
            'tests/data/histo/hallue_with_afluent.histo'
        )
    return MartLiais.from_file('tests/data/liais_fract/craie_npc.liais')


@pytest.mark.parametrize('row_count', [0, 2, None], ids=['empty', 'small', 'full'])
def test_dataframe_text_preserves_pandas_rendering(
    mart_dataframe, row_count, capsys
):
    frame = mart_dataframe.iloc[:row_count]
    original = pd.DataFrame(frame).copy(deep=True)

    with pd.option_context(
        'display.max_rows', 4, 'display.max_columns', 4, 'display.width', 80
    ):
        text = repr(frame)
        header, table = text.split('\n', 1)
        assert header == frame.__class__.__name__
        expected_table = repr(original)
        if frame.empty:
            expected_table = expected_table.replace(
                'Empty DataFrame', f'Empty {frame.__class__.__name__}', 1
            )
        assert table == expected_table
        assert str(frame) == text
        print(frame)
        assert capsys.readouterr().out == text + '\n'
        if row_count is None:
            assert '...' in table

    pd.testing.assert_frame_equal(pd.DataFrame(frame), original)


def test_dataframe_html_preserves_pandas_rendering(mart_dataframe):
    frame = mart_dataframe.head(2)
    with pd.option_context('display.notebook_repr_html', True):
        assert frame._repr_html_() == pd.DataFrame(frame)._repr_html_()


@pytest.mark.parametrize('source', ['template', 'file'])
def test_params_text_preserves_parameters(source, capsys):
    if source == 'template':
        params = MartParams.from_template()
    else:
        params = MartParams.from_file(
            'tests/data/mart_hallue/hallue_for_test.mart'
        )
    original = deepcopy(params.to_dict())

    text = repr(params)
    header, content = text.split('\n', 1)
    assert header == 'MartParams'
    assert ast.literal_eval(content) == original
    assert str(params) == text
    print(params)
    assert capsys.readouterr().out == text + '\n'
    assert params.to_dict() == original


@pytest.mark.parametrize('time_kind', ['numeric', 'datetime'])
@pytest.mark.parametrize('has_actions', [False, True])
def test_timesteps_text_preserves_summary(time_kind, has_actions, capsys):
    if time_kind == 'numeric':
        dates = [0.0, 1.5, 3.0]
    else:
        dates = pd.date_range('2000-01-01', periods=3)
    times = pd.DataFrame({
        'step': [0, 1, 2],
        'time': dates,
        'has_action': [has_actions, False, False],
    })
    actions = {}
    if has_actions:
        actions[str(dates[0])] = {'HDYNAM': [{'value': 1}]}
    timesteps = MartTimeSteps(times, actions)
    original_times = times.copy(deep=True)
    original_actions = deepcopy(actions)

    text = repr(timesteps)
    lines = text.splitlines()
    assert lines[0] == 'MartTimeSteps'
    assert lines[1] == '============='
    assert lines[2] == f'Datetime From: {dates[0]}, to: {dates[-1]}'
    assert lines[3] == 'Number of steps: 3'
    expected_action_count = 1 if has_actions else 0
    assert lines[4] == f'Number of steps with action: {expected_action_count}'
    assert str(timesteps) == text
    print(timesteps)
    assert capsys.readouterr().out == text + '\n'
    pd.testing.assert_frame_equal(timesteps.times, original_times)
    assert timesteps.actions == original_actions


def test_representations_use_subclass_names():
    class CustomHisto(MartHisto):
        pass

    class CustomLiais(MartLiais):
        pass

    class CustomParams(MartParams):
        pass

    class CustomTimeSteps(MartTimeSteps):
        pass

    objects = [
        CustomHisto(pd.DataFrame()),
        CustomLiais(pd.DataFrame()),
        CustomParams(**MartParams.from_template().to_dict()),
        CustomTimeSteps.from_dates(dates=['2000-01-01']),
    ]
    expected_names = [
        'CustomHisto', 'CustomLiais', 'CustomParams', 'CustomTimeSteps'
    ]
    for obj, expected_name in zip(objects, expected_names):
        assert repr(obj).splitlines()[0] == expected_name
        assert str(obj) == repr(obj)
