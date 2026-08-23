from pathlib import Path

import streamlit as st

from src.agent import parse_review
from src.executor import execute_action
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


uploaded_file = st.file_uploader(
    "上传视频",
    type=["mp4"],
)

review = st.text_area(
    "审核意见",
    placeholder="例如：00:10-00:20 这段删掉",
)


# =========================
# 1. 分析审核意见
# =========================

if st.button("分析意见", type="primary"):
    if uploaded_file is None:
        st.error("请先上传视频。")

    elif not review.strip():
        st.error("请输入审核意见。")

    else:
        INPUT_PATH.write_bytes(uploaded_file.getbuffer())

        # 新一次分析开始时，旧的执行结果不再有效
        st.session_state.pop("output_ready", None)

        try:
            result = parse_review(review)

            st.session_state["review_result"] = result.model_dump()
            st.session_state["input_ready"] = True

            # ACTION 情况下，把 AI 建议的时间写入可编辑控件
            if result.status == "ACTION" and result.action is not None:
                st.session_state["edit_start"] = result.action.start_time
                st.session_state["edit_end"] = result.action.end_time

        except Exception as e:
            st.error(f"解析失败：{e}")


# =========================
# 2. 展示 Cutback 的判断
# =========================

if "review_result" in st.session_state:
    result = ReviewResult.model_validate(
        st.session_state["review_result"]
    )

    st.subheader("Cutback 分析结果")

    # ---------- ACTION ----------
    if result.status == "ACTION":
        action = result.action

        if action is None:
            st.error("模型返回了无效的 ACTION。")

        else:
            st.success("该审核意见可以转换为明确的编辑操作。")

            st.write(
                f"Cutback 建议删除 "
                f"**{action.start_time:.1f}s – {action.end_time:.1f}s**"
            )

            st.caption(
                "执行前可以修改时间范围；"
                "不修改直接执行即视为接受 AI 建议。"
            )

            start_time = st.number_input(
                "开始时间（秒）",
                min_value=0.0,
                step=0.1,
                key="edit_start",
            )

            end_time = st.number_input(
                "结束时间（秒）",
                min_value=0.0,
                step=0.1,
                key="edit_end",
            )

            left, right = st.columns(2)

            with left:
                if st.button(
                    "执行当前方案",
                    type="primary",
                ):
                    try:
                        final_action = EditAction(
                            action="DELETE_RANGE",
                            start_time=start_time,
                            end_time=end_time,
                        )

                        execute_action(
                            final_action,
                            str(INPUT_PATH),
                            str(OUTPUT_PATH),
                        )

                        st.session_state["output_ready"] = True
                        st.success("修改完成。")

                    except Exception as e:
                        st.error(f"执行失败：{e}")

            with right:
                if st.button("拒绝本次建议"):
                    st.session_state.pop(
                        "review_result",
                        None,
                    )
                    st.session_state.pop(
                        "output_ready",
                        None,
                    )
                    st.rerun()

    # ---------- CLARIFY ----------
    elif result.status == "CLARIFY":
        st.warning("需要进一步确认")

        st.write(
            result.message
            or "当前信息不足以确定具体编辑操作。"
        )

        st.caption(
            "请补充或修改上方审核意见，然后重新分析。"
        )

    # ---------- NO_ACTION ----------
    elif result.status == "NO_ACTION":
        st.info(
            result.message
            or "该审核意见不需要执行修改。"
        )


# =========================
# 3. 视频预览
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
            st.video(str(INPUT_PATH))

        with right:
            st.subheader("修改后")
            st.video(str(OUTPUT_PATH))

    else:
        st.subheader("原视频")
        st.video(str(INPUT_PATH))
