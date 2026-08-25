from pathlib import Path

import streamlit as st

from src.agent import parse_reviews
from src.executor import execute_actions
from src.models import EditAction, ReviewResult


DATA_DIR = Path("data")
OUTPUT_DIR = Path("outputs")

INPUT_PATH = DATA_DIR / "uploaded.mp4"
OUTPUT_PATH = OUTPUT_DIR / "cutback_result.mp4"

DATA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)


st.set_page_config(
    page_title="Cutback",
    page_icon="✂️",
    layout="wide",
)


st.title("Cutback")
st.caption(
    "Review-to-Edit Agent · "
    "将视频审核意见转换为可执行、可确认的视频编辑操作"
)


# =========================
# 1. 输入
# =========================

uploaded_file = st.file_uploader(
    "上传视频",
    type=["mp4"],
)

reviews_text = st.text_area(
    "审核意见",
    placeholder=(
        "每行输入一条审核意见，例如：\n"
        "00:10-00:20 这段删掉\n"
        "00:30-00:40 这段放到开头\n"
        "00:50-01:00 这里有点拖\n"
        "01:10-01:20 这段挺好的，保留"
    ),
    height=160,
)

reviews = [
    line.strip()
    for line in reviews_text.splitlines()
    if line.strip()
]


# =========================
# 2. 分析全部 Review
# =========================

if st.button(
    "分析全部意见",
    type="primary",
):
    if uploaded_file is None:
        st.error("请先上传视频。")

    elif not reviews:
        st.error("请输入至少一条审核意见。")

    else:
        INPUT_PATH.write_bytes(
            uploaded_file.getbuffer()
        )

        # 新一轮分析开始后，
        # 旧输出和旧动态控件全部失效
        st.session_state.pop(
            "output_ready",
            None,
        )

        st.session_state.pop(
            "review_items",
            None,
        )

        dynamic_prefixes = (
            "approve_",
            "start_",
            "end_",
            "destination_",
        )

        for key in list(
            st.session_state.keys()
        ):
            if key.startswith(
                dynamic_prefixes
            ):
                del st.session_state[key]

        try:
            with st.spinner(
                f"正在分析 {len(reviews)} 条审核意见..."
            ):
                results = parse_reviews(
                    reviews
                )

            items = [
                {
                    "review": review,
                    "result": result.model_dump(),
                }
                for review, result in zip(
                    reviews,
                    results,
                )
            ]

            st.session_state[
                "review_items"
            ] = items

            st.session_state[
                "input_ready"
            ] = True

            # 为 ACTION 初始化可编辑参数
            for index, item in enumerate(items):
                result = ReviewResult.model_validate(
                    item["result"]
                )

                if (
                    result.status == "ACTION"
                    and result.action is not None
                ):
                    action = result.action

                    st.session_state[
                        f"start_{index}"
                    ] = action.start_time

                    st.session_state[
                        f"end_{index}"
                    ] = action.end_time

                    if (
                        action.action
                        == "MOVE_RANGE"
                    ):
                        st.session_state[
                            f"destination_{index}"
                        ] = action.destination_time

            st.success(
                f"已完成 {len(reviews)} 条审核意见分析。"
            )

        except Exception as e:
            st.error(
                f"分析失败：{e}"
            )


# =========================
# 3. 展示 Review Queue
# =========================

approved_actions = []


if "review_items" in st.session_state:
    st.subheader("Cutback 分析结果")

    items = st.session_state[
        "review_items"
    ]

    action_count = 0
    clarify_count = 0
    no_action_count = 0

    for item in items:
        result = ReviewResult.model_validate(
            item["result"]
        )

        if result.status == "ACTION":
            action_count += 1

        elif result.status == "CLARIFY":
            clarify_count += 1

        elif result.status == "NO_ACTION":
            no_action_count += 1

    st.caption(
        f"ACTION {action_count} · "
        f"CLARIFY {clarify_count} · "
        f"NO_ACTION {no_action_count}"
    )


    # -------------------------
    # 逐条 Review
    # -------------------------

    for index, item in enumerate(items):
        result = ReviewResult.model_validate(
            item["result"]
        )

        with st.container(
            border=True
        ):
            st.markdown(
                f"### Review {index + 1}"
            )

            st.write(
                item["review"]
            )

            # =====================
            # ACTION
            # =====================

            if result.status == "ACTION":
                action = result.action

                if action is None:
                    st.error(
                        "模型返回了无效的 ACTION。"
                    )
                    continue

                st.success(
                    f"ACTION · {action.action}"
                )

                # -----------------
                # DELETE_RANGE
                # -----------------

                if (
                    action.action
                    == "DELETE_RANGE"
                ):
                    st.write(
                        f"建议删除 "
                        f"**{action.start_time:.1f}s – "
                        f"{action.end_time:.1f}s**"
                    )

                # -----------------
                # MOVE_RANGE
                # -----------------

                elif (
                    action.action
                    == "MOVE_RANGE"
                ):
                    st.write(
                        f"建议将 "
                        f"**{action.start_time:.1f}s – "
                        f"{action.end_time:.1f}s** "
                        f"移动到 "
                        f"**{action.destination_time:.1f}s**"
                    )

                else:
                    st.error(
                        f"暂不支持的编辑操作："
                        f"{action.action}"
                    )
                    continue

                st.caption(
                    "执行前可以修改参数。"
                )


                # -----------------
                # 公共参数
                # -----------------

                start_time = st.number_input(
                    "开始时间（秒）",
                    min_value=0.0,
                    step=0.1,
                    key=f"start_{index}",
                )

                end_time = st.number_input(
                    "结束时间（秒）",
                    min_value=0.0,
                    step=0.1,
                    key=f"end_{index}",
                )


                # -----------------
                # MOVE 参数
                # -----------------

                destination_time = None

                if (
                    action.action
                    == "MOVE_RANGE"
                ):
                    destination_time = (
                        st.number_input(
                            "目标位置（秒）",
                            min_value=0.0,
                            step=0.1,
                            key=(
                                f"destination_"
                                f"{index}"
                            ),
                        )
                    )


                # -----------------
                # Human Approval
                # -----------------

                approved = st.checkbox(
                    "批准执行",
                    key=f"approve_{index}",
                )

                if approved:
                    try:
                        if (
                            action.action
                            == "DELETE_RANGE"
                        ):
                            final_action = EditAction(
                                action="DELETE_RANGE",
                                start_time=start_time,
                                end_time=end_time,
                            )

                        elif (
                            action.action
                            == "MOVE_RANGE"
                        ):
                            final_action = EditAction(
                                action="MOVE_RANGE",
                                start_time=start_time,
                                end_time=end_time,
                                destination_time=(
                                    destination_time
                                ),
                            )

                        else:
                            raise ValueError(
                                "不支持的编辑操作"
                            )

                        approved_actions.append(
                            final_action
                        )

                    except Exception as e:
                        st.error(
                            f"参数无效：{e}"
                        )


            # =====================
            # CLARIFY
            # =====================

            elif (
                result.status
                == "CLARIFY"
            ):
                st.warning(
                    "CLARIFY · 需要进一步确认"
                )

                st.write(
                    result.message
                    or (
                        "当前信息不足以确定"
                        "具体编辑操作。"
                    )
                )


            # =====================
            # NO_ACTION
            # =====================

            elif (
                result.status
                == "NO_ACTION"
            ):
                st.info(
                    "NO_ACTION · 无需修改"
                )

                if result.message:
                    st.write(
                        result.message
                    )


    # =========================
    # 4. 批量执行
    # =========================

    st.divider()

    st.write(
        f"已批准 "
        f"**{len(approved_actions)}** "
        f"个编辑操作"
    )

    if st.button(
        "执行已批准操作",
        type="primary",
    ):
        if not approved_actions:
            st.warning(
                "请至少批准一个编辑操作。"
            )

        else:
            try:
                with st.spinner(
                    "正在生成修改后视频..."
                ):
                    execute_actions(
                        approved_actions,
                        str(INPUT_PATH),
                        str(OUTPUT_PATH),
                    )

                st.session_state[
                    "output_ready"
                ] = True

                st.success(
                    "编辑完成。"
                )

            except Exception as e:
                st.error(
                    f"无法执行：{e}"
                )


# =========================
# 5. 视频预览
# =========================

if (
    st.session_state.get("input_ready")
    and INPUT_PATH.exists()
):
    st.divider()

    if (
        st.session_state.get("output_ready")
        and OUTPUT_PATH.exists()
    ):
        left, right = st.columns(2)

        with left:
            st.subheader("原视频")

            st.video(
                str(INPUT_PATH)
            )

        with right:
            st.subheader("修改后")

            st.video(
                str(OUTPUT_PATH)
            )

    else:
        st.subheader("原视频")

        st.video(
            str(INPUT_PATH)
        )
