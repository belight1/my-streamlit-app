
import os
import streamlit as st
from openai import OpenAI

# OpenAI 클라이언트 생성
client = OpenAI()

# 페이지 설정
st.set_page_config(page_title="아주 멋진 한영 번역기", page_icon="star")
st.title("번역이 아주 잘되는 한영 번역기입니다")
st.write("번역할 문장을 적어보시겠어요?")

# 사용자 입력(텍스트)
korean_text = st.text_area(
    "번역할 한글 문장을 입력하세요.",
    height=150,
    placeholder="예: 인공지능은 우리의 일상과 업무 방식을 빠르게 변화시키고 있습니다."
)

# 번역 버튼
if st.button("번! 역!"):

    if not korean_text.strip():
        st.warning("아무 입력도 하지 않으셨어요")
    else:
        with st.spinner("번역 중이에요..."):

            # 시스템 역할
            sys_role = """
            당신은 30년차 한영 번역 전문가입니다.
            간결하고 이해가 쉬운 문장으로 번역해야 합니다.
            문장을 임의로 지어내지 말고 주어진 문장만 번역하세요.
            """

            # 프롬프트 구성
            prompt = f"""
            다음 문장을 영어로 번역하세요.
            TEXT:
            {korean_text}
            """

            # GPT 호출
            response = client.responses.create(
                model="gpt-4o-mini",
                input=[
                    {"role": "system", "content": sys_role},
                    {"role": "user", "content": prompt}
                ]
            )

            # 결과 출력
            translated_text = response.output_text

            st.subheader("번역한 문장을 보여드릴게요 ~ ㅎㅎ")
            st.success(translated_text)
