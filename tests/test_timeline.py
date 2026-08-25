import pytest

from src.models import EditAction
from src.timeline import build_timeline


def test_multiple_actions():
    actions = [
        EditAction(
            action="DELETE_RANGE",
            start_time=10,
            end_time=20,
        ),
        EditAction(
            action="MOVE_RANGE",
            start_time=30,
            end_time=40,
            destination_time=0,
        ),
    ]

    timeline = build_timeline(
        duration=60,
        actions=actions,
    )

    result = [
        (segment.start, segment.end)
        for segment in timeline
    ]

    assert result == [
        (30, 40),
        (0.0, 10),
        (20, 30),
        (40, 60),
    ]


def test_overlapping_actions_rejected():
    actions = [
        EditAction(
            action="DELETE_RANGE",
            start_time=10,
            end_time=20,
        ),
        EditAction(
            action="MOVE_RANGE",
            start_time=15,
            end_time=25,
            destination_time=0,
        ),
    ]

    with pytest.raises(ValueError):
        build_timeline(
            duration=60,
            actions=actions,
        )


def test_destination_inside_other_action_rejected():
    actions = [
        EditAction(
            action="DELETE_RANGE",
            start_time=10,
            end_time=20,
        ),
        EditAction(
            action="MOVE_RANGE",
            start_time=30,
            end_time=40,
            destination_time=15,
        ),
    ]

    with pytest.raises(ValueError):
        build_timeline(
            duration=60,
            actions=actions,
        )
