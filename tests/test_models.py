import sys
from pathlib import Path

from pydantic import ValidationError
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.models import EditAction


def test_valid_delete_range():
    action = EditAction(action="DELETE_RANGE", start_time=10, end_time=20)
    assert action.action == "DELETE_RANGE"
    assert action.start_time == 10
    assert action.end_time == 20


def test_end_not_after_start():
    with pytest.raises(ValidationError):
        EditAction(action="DELETE_RANGE", start_time=10, end_time=10)


def test_invalid_action():
    with pytest.raises(ValidationError):
        EditAction(action="CUT", start_time=10, end_time=20)
