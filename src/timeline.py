from dataclasses import dataclass

from src.models import EditAction


EPS = 1e-6


@dataclass(frozen=True)
class Segment:
    start: float
    end: float


def _split_at(
    segments: list[Segment],
    point: float,
) -> list[Segment]:
    result = []

    for segment in segments:
        if (
            segment.start + EPS
            < point
            < segment.end - EPS
        ):
            result.extend(
                [
                    Segment(segment.start, point),
                    Segment(point, segment.end),
                ]
            )
        else:
            result.append(segment)

    return result


def _validate_actions(
    duration: float,
    actions: list[EditAction],
) -> None:
    for action in actions:
        if action.end_time > duration + EPS:
            raise ValueError(
                "编辑范围超出视频时长"
            )

        if action.action == "MOVE_RANGE":
            destination = float(
                action.destination_time
            )

            if destination > duration + EPS:
                raise ValueError(
                    "MOVE_RANGE 目标位置超出视频时长"
                )

    # V0 不处理多个操作源范围互相重叠的情况
    for i, left in enumerate(actions):
        for right in actions[i + 1:]:
            overlap = (
                max(
                    left.start_time,
                    right.start_time,
                )
                <
                min(
                    left.end_time,
                    right.end_time,
                ) - EPS
            )

            if overlap:
                raise ValueError(
                    "多个编辑操作的时间范围发生重叠，"
                    "请取消或修改其中一个操作"
                )

    move_actions = [
        action
        for action in actions
        if action.action == "MOVE_RANGE"
    ]

    for i, action in enumerate(move_actions):
        destination = float(
            action.destination_time
        )

        # 目标位置不能落入另一个待编辑范围
        for other in actions:
            if other is action:
                continue

            if (
                other.start_time
                <= destination
                < other.end_time
            ):
                raise ValueError(
                    "MOVE_RANGE 的目标位置落在"
                    "另一个编辑操作范围内"
                )

        # V0 不处理两个片段移动到同一位置
        for other in move_actions[i + 1:]:
            if (
                abs(
                    destination
                    - float(other.destination_time)
                )
                < EPS
            ):
                raise ValueError(
                    "多个 MOVE_RANGE 不能使用"
                    "相同的目标位置"
                )


def _apply_delete(
    segments: list[Segment],
    action: EditAction,
) -> list[Segment]:
    segments = _split_at(
        segments,
        action.start_time,
    )

    segments = _split_at(
        segments,
        action.end_time,
    )

    return [
        segment
        for segment in segments
        if not (
            segment.start
            >= action.start_time - EPS
            and segment.end
            <= action.end_time + EPS
        )
    ]


def _apply_move(
    segments: list[Segment],
    action: EditAction,
    duration: float,
) -> list[Segment]:
    destination = float(
        action.destination_time
    )

    for point in (
        action.start_time,
        action.end_time,
        destination,
    ):
        segments = _split_at(
            segments,
            point,
        )

    moving = [
        segment
        for segment in segments
        if (
            segment.start
            >= action.start_time - EPS
            and segment.end
            <= action.end_time + EPS
        )
    ]

    expected_length = (
        action.end_time
        - action.start_time
    )

    actual_length = sum(
        segment.end - segment.start
        for segment in moving
    )

    if (
        abs(
            expected_length
            - actual_length
        )
        > EPS
    ):
        raise ValueError(
            "MOVE_RANGE 的源片段已被其他操作改变"
        )

    remaining = [
        segment
        for segment in segments
        if segment not in moving
    ]

    # 移动到视频末尾
    if abs(destination - duration) < EPS:
        return remaining + moving

    insert_index = next(
        (
            index
            for index, segment
            in enumerate(remaining)
            if abs(
                segment.start
                - destination
            )
            < EPS
        ),
        None,
    )

    if insert_index is None:
        raise ValueError(
            "无法在目标位置插入移动片段"
        )

    return (
        remaining[:insert_index]
        + moving
        + remaining[insert_index:]
    )


def build_timeline(
    duration: float,
    actions: list[EditAction],
) -> list[Segment]:
    if not actions:
        raise ValueError(
            "没有需要执行的编辑操作"
        )

    _validate_actions(
        duration,
        actions,
    )

    segments = [
        Segment(
            start=0.0,
            end=duration,
        )
    ]

    for action in actions:
        if action.action == "DELETE_RANGE":
            segments = _apply_delete(
                segments,
                action,
            )

        elif action.action == "MOVE_RANGE":
            segments = _apply_move(
                segments,
                action,
                duration,
            )

    if not segments:
        raise ValueError(
            "编辑结果不能为空视频"
        )

    return segments
