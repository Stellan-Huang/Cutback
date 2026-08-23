from pathlib import Path

import streamlit as st

from src.agent import parse_review
from src.executor import execute_action
from src.models import EditAction


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


if st.button("分析意见", type="primary"):
    if uploaded_file is None:
        st.error("请先上传视频。")

    elif not review.strip():
        st.error("请输入审核意见。")

    else:
        INPUT_PATH.write_bytes(uploaded_file.getbuffer())

        try:
            action = parse_review(review)

            st.session_state["action"] = action.model_dump()
            st.session_state["input_ready"] = True

        except Exception as e:
            st.error(f"解析失败：{e}")


if "action" in st.session_state:
    action = EditAction.model_validate(
        st.session_state["action"]
    )

    st.subheader("AI 编辑建议")

    st.json(action.model_dump())

    st.write(
        f"Cutback 建议删除 "
        f"**{action.start_time:.1f}s – {action.end_time:.1f}s**"
    )

    if st.button("确认执行"):
        try:
            execute_action(
                action,
                str(INPUT_PATH),
                str(OUTPUT_PATH),
            )

            st.session_state["output_ready"] = True

        except Exception as e:
            st.error(f"执行失败：{e}")


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
