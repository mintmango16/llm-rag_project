import streamlit as st
import api_function as api
from prompts import BrandingOutput, STORY_INTERVIEW_QUESTIONS, PageTextContent
import os
import av
import io
from streamlit_webrtc import webrtc_streamer, WebRtcMode, AudioProcessorBase

# --- 1. 페이지 설정 및 세션 상태 초기화 ---
st.set_page_config(page_title="AI 홍보 비서", layout="centered")

def initialize_session_state():
    """세션 상태를 초기화하는 함수"""
    if 'current_step' not in st.session_state:
        st.session_state.current_step = 'welcome'

    # 데이터 저장소
    if 'product_info' not in st.session_state:
        st.session_state.product_info = {}
    
    # 입력 방식 및 임시 텍스트 저장을 위한 상태
    if 'input_method' not in st.session_state:
        st.session_state.input_method = 'direct'
    if 'transcribed_text' not in st.session_state:
        st.session_state.transcribed_text = ""

    # AI 인터뷰 관련 상태
    if 'interview_answers' not in st.session_state:
        st.session_state.interview_answers = {}
    if 'interview_question_index' not in st.session_state:
        st.session_state.interview_question_index = 0
    if 'generated_story_text' not in st.session_state:
        st.session_state.generated_story_text = None
        
    # webrtc 오디오 데이터 저장을 위한 상태
    if "audio_bytes" not in st.session_state:
        st.session_state.audio_bytes = None
    
    # 결과물 저장을 위한 상태
    if 'branding_result' not in st.session_state:
        st.session_state.branding_result = None
    if 'live_local_info' not in st.session_state:
        st.session_state.live_local_info = None
    if 'detail_page_images' not in st.session_state:
        st.session_state.detail_page_images = []
    if 'detail_page_texts' not in st.session_state:
        st.session_state.detail_page_texts = []
    if 'marketing_content' not in st.session_state:
        st.session_state.marketing_content = {}
        
    if 'final_detail_page' not in st.session_state:
        st.session_state.final_detail_page = None
        
    if 'slogan_alternatives' not in st.session_state:
        st.session_state.slogan_alternatives = []


initialize_session_state()


# --- 2. 오디오 처리 클래스 (streamlit-webrtc) ---
class AudioRecorder(AudioProcessorBase):
    def __init__(self) -> None:
        self._frames = []
    def recv(self, frame: av.AudioFrame) -> av.AudioFrame:
        self._frames.append(frame)
        return frame
    def on_ended(self):
        if not self._frames:
            return
        sound = self._frames[0]
        for frame in self._frames[1:]:
            sound += frame
        buffer = io.BytesIO()
        output_container = av.open(buffer, mode="w", format="wav")
        stream = output_container.add_stream("pcm_s16le", rate=sound.sample_rate, layout="mono")
        for frame in av.AudioResampler(format="s16", layout="mono", rate=sound.sample_rate).resample(sound):
            for packet in stream.encode(frame):
                output_container.mux(packet)
        output_container.close()
        buffer.seek(0)
        st.session_state.audio_bytes = buffer.read()


# --- 3. 단계별 UI 렌더링 함수 ---

def show_progress():
    if st.session_state.product_info:
        with st.expander("지금까지 입력한 정보 보기", expanded=False):
            for key, value in st.session_state.product_info.items():
                st.markdown(f"- **{key}**: {value}")

def render_welcome_page():
    st.title("사장님, 환영합니다! 👋")
    st.subheader("제가 사장님의 상품 홍보를 도와드릴게요.")
    st.markdown("---")
    st.write("몇 가지 질문에만 답해주시면, AI가 알아서 멋진 소개글과 사진을 만들어 드립니다.")
    if st.button("네, 좋습니다! 시작할게요 👍", type="primary", use_container_width=True):
        st.session_state.current_step = 'get_name'
        st.session_state.input_method = 'direct'
        st.rerun()

def render_input_step(step_title, subheader, placeholder, info_key, next_step):
    """상품명, 원산지 입력을 위한 공통 UI 템플릿"""
    show_progress()
    st.info(f"✅ **{step_title}**")
    st.subheader(subheader)

    input_method = st.session_state.get('input_method', 'direct')

    # '마이크' 모드일 때만 녹음 UI를 먼저 보여줌
    if input_method == 'mic':
        st.info("아래 'START' 버튼을 누르고 말씀하신 후, 'STOP'을 눌러주세요.")
        webrtc_streamer(
            key=f"webrtc_{info_key}",
            mode=WebRtcMode.SENDONLY,
            audio_processor_factory=AudioRecorder,
            media_stream_constraints={"video": False, "audio": True},
        )
        if st.session_state.audio_bytes:
            with st.spinner("음성을 텍스트로 변환 중..."):
                transcribed = api.transcribe_audio(st.session_state.audio_bytes)
                st.session_state.transcribed_text = transcribed if transcribed else ""
                st.session_state.audio_bytes = None
                st.session_state.input_method = 'direct'
                st.rerun()
        if st.button("직접 입력할래요"):
            st.session_state.input_method = 'direct'
            st.rerun()
    
    # '직접 입력' 모드일 때 UI
    else:
        user_input = st.text_input(
            "여기에 입력하시거나, 마이크 버튼을 눌러 말씀하세요.",
            value=st.session_state.get('transcribed_text', ''),
            placeholder=placeholder,
            key=f"input_{info_key}"
        )
        if st.button("🎙️ 마이크로 말하기", key=f"mic_{info_key}"):
            st.session_state.input_method = 'mic'
            st.session_state.transcribed_text = ""
            st.rerun()

    # '다음' 버튼은 항상 표시
    if st.button("다음", type="primary", use_container_width=True):
        final_input = st.session_state.get(f"input_{info_key}", "")
        if final_input:
            st.session_state.product_info[info_key] = final_input
            st.session_state.current_step = next_step
            st.session_state.transcribed_text = ""
            st.session_state.input_method = 'direct'
            st.rerun()
        else:
            st.warning("내용을 꼭 입력해주세요!")

def render_story_step():
    show_progress()
    st.info("✅ **3단계:** 상품 자랑하기 (가장 중요해요!)")
    st.subheader("사장님의 상품 자랑을 마음껏 해주세요!")
    input_method = st.session_state.get('input_method', 'direct')
    
    # [수정된 핵심 로직] AI 인터뷰로 생성된 스토리가 있으면 먼저 보여줌
    if input_method == 'chat' and st.session_state.generated_story_text is not None:
        st.success("AI가 생성한 스토리 초안입니다. 확인 후 수정하시거나, 바로 다음 단계로 넘어가세요.")
        story_draft = st.text_area(
            "AI 생성 스토리 초안 (직접 수정 가능)", 
            value=st.session_state.generated_story_text, 
            height=250, key="final_story_input"
        )
        if st.button("완벽해요! 다음 단계로", type="primary", use_container_width=True):
            st.session_state.product_info['판매자 스토리'] = st.session_state.final_story_input
            st.session_state.current_step = 'get_image'
            st.session_state.input_method = 'direct'
            st.session_state.generated_story_text = None
            st.rerun()
        if st.button("다시 인터뷰할래요"):
            st.session_state.input_method = 'chat'
            st.session_state.interview_question_index = 0
            st.session_state.generated_story_text = None
            st.rerun()
        return

    # '직접 입력' 모드
    if input_method == 'direct':
        st.text_area(
            "여기에 상품 이야기를 자유롭게 작성해주세요.",
            value=st.session_state.get('transcribed_text', ''),
            height=200, key="story_direct_input",
            help="어떤 점이 특별한지, 어떻게 정성껏 만드시는지 등 자유롭게 이야기해주세요."
        )
        st.markdown("<p style='text-align: center; color: grey;'>글쓰기가 어려우시면 아래 도움을 받아보세요</p>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        if c1.button("🎙️ 마이크로 말하기", use_container_width=True):
            st.session_state.input_method = 'mic'; st.rerun()
        if c2.button("💬 AI랑 대화하며 만들기", use_container_width=True):
            st.session_state.input_method = 'chat'; st.session_state.interview_question_index = 0; st.rerun()
        if st.button("다음 단계로", type="primary", use_container_width=True):
            st.session_state.product_info['판매자 스토리'] = st.session_state.story_direct_input
            st.session_state.current_step = 'get_image'; st.rerun()
            
    # '마이크' 모드
    elif input_method == 'mic':
        st.info("아래 'START' 버튼을 누르고 말씀하신 후, 'STOP'을 눌러주세요.")
        webrtc_streamer(key="webrtc_story", mode=WebRtcMode.SENDONLY, audio_processor_factory=AudioRecorder, media_stream_constraints={"video": False, "audio": True})
        if st.session_state.audio_bytes:
            with st.spinner("음성을 텍스트로 변환하고 있습니다..."):
                st.session_state.transcribed_text = api.transcribe_audio(st.session_state.audio_bytes) or ""
                st.session_state.audio_bytes = None
                st.session_state.input_method = 'direct'
                st.rerun()
        if st.button("직접 쓸래요"): st.session_state.input_method = 'direct'; st.rerun()
            
    # 'AI 대화' 모드
    elif input_method == 'chat':
        q_index = st.session_state.interview_question_index
        if q_index < len(STORY_INTERVIEW_QUESTIONS):
            question = STORY_INTERVIEW_QUESTIONS[q_index]
            st.info(f"**질문 {q_index + 1}/**{len(STORY_INTERVIEW_QUESTIONS)}: {question}")
            answer = st.text_area("답변을 입력해주세요.", key=f"answer_{q_index}")
            if st.button("답변 제출", type="primary"):
                st.session_state.interview_answers[q_index] = answer
                st.session_state.interview_question_index += 1
                st.rerun()
        else:
            st.success("모든 질문에 답변해주셔서 감사합니다!")
            if st.button("✨ AI 스토리 자동 생성하기", type="primary", use_container_width=True):
                with st.spinner("AI 카피라이터가 스토리를 작성하고 있습니다..."):
                    summary = ""
                    for i, question in enumerate(STORY_INTERVIEW_QUESTIONS):
                        answer = st.session_state.interview_answers.get(i, "답변 없음")
                        summary += f"Q: {question}\nA: {answer}\n\n"
                    st.session_state.generated_story_text = api.generate_story_from_interview(summary)
                    st.rerun()
        if st.button("직접 쓸래요"): st.session_state.input_method = 'direct'; st.rerun()

def render_image_step():
    show_progress()
    st.info("**4단계:** 원하는 느낌 선택하기")
    st.subheader("손님들이 우리 상품을 어떤 느낌으로 기억하면 좋을까요?")
    image_options = ["믿음직한", "정겨운", "건강한", "고급스러운", "활기찬", "신선한", "전통적인", "친환경적인", "맛있는", "편리한", "재미있는", "감성적인"]
    selected_options = st.multiselect("어울리는 느낌을 모두 골라주세요.", image_options)
    other_image = st.text_input("혹시 다른 느낌이 있다면 직접 적어주세요.")
    if st.button("다음", type="primary", use_container_width=True):
        final_image_text = ", ".join(selected_options)
        if other_image: final_image_text += f", {other_image}" if final_image_text else other_image
        if not final_image_text:
            st.warning("원하는 느낌을 하나 이상 선택하거나 입력해주세요!")
        else:
            st.session_state.product_info['원하는 브랜드 이미지'] = final_image_text
            st.session_state.current_step = 'get_category'
            st.rerun()

def render_category_step():
    show_progress()
    st.info("**5단계:** 상품 종류 선택하기 (마지막 질문!)")
    st.subheader("이 상품은 어떤 종류에 속하나요?")
    
    category = st.selectbox("아래에서 가장 비슷한 종류를 선택해주세요.", ["과일", "채소", "수산물", "가공식품", "기타"])
    
    if st.button("이제 결과 만들러 가기!", type="primary", use_container_width=True):
        st.session_state.product_info['품목'] = category
        st.session_state.current_step = 'processing'
        st.rerun()

def render_processing_page():
    st.balloons()
    st.success("모든 정보가 준비되었습니다! 이제 AI가 마법을 부릴 시간입니다.")
    st.header("AI 홍보 전문가가 열심히 작업하고 있습니다...")

    with st.spinner("1. 최신 정보와 트렌드를 분석하는 중..."):
        summary, _ = api.search_with_tavily_multi_query(st.session_state.product_info)
        st.session_state.live_local_info = summary
        st.success("최신 정보 분석 완료!")

    with st.spinner("2. 사장님만의 특별한 브랜딩을 만드는 중..."):
        branding_result = api.generate_branding(st.session_state.product_info, st.session_state.live_local_info)
        if branding_result:
            st.session_state.branding_result = branding_result
            st.success("브랜딩 생성 완료!")
        else:
            st.error("브랜딩 생성에 실패했습니다. 잠시 후 다시 시도해주세요.")
            st.session_state.current_step = 'get_category' # 이전 단계로
            st.rerun()

    st.session_state.current_step = 'show_results'
    st.rerun()

def render_results_page():
    st.title("사장님만의 특별한 브랜드가 탄생!")
    st.write("사장님의 소중한 이야기와 저희 AI의 분석을 통해, 세상에 단 하나뿐인 브랜드 컨셉을 만들었습니다.")

    branding_tab, detail_images_tab, marketing_tab = st.tabs(["**브랜드 컨셉**", "**상세페이지**", "**마케팅 콘텐츠**"])

    with branding_tab:
        render_branding_concept_cards()

    with detail_images_tab:
        st.header("AI 상세페이지 자동 생성")
        st.info("AI가 브랜딩 컨셉에 맞춰 상세페이지를 생성 및 조립합니다.")
        
        if st.session_state.final_detail_page:
            st.markdown("---")
            st.subheader("✨ 최종 완성된 상세페이지")
            st.image(st.session_state.final_detail_page, caption="AI가 생성한 최종 상세페이지")
            st.download_button(label="상세페이지 다운로드", data=st.session_state.final_detail_page, file_name=f"{st.session_state.product_info.get('상품명', 'product')}_상세페이지.png", mime="image/png")
            st.markdown("---")

        button_text = "상세페이지 다시 생성 및 조립하기" if st.session_state.final_detail_page else "🎨 상세페이지 생성 및 조립하기"
        
        if st.button(button_text, type="primary"):
            st.session_state.final_detail_page = None # 다시 생성 시 기존 이미지 초기화
            result_container = st.container(border=True)
            
            with result_container:
                st.subheader("상세페이지 생성 과정")

            # 1. 텍스트 생성 및 표시
            with st.spinner("1/3 - 텍스트 콘텐츠 생성 중..."):
                page_texts_dict = api.generate_page_texts(st.session_state.product_info, st.session_state.branding_result, st.session_state.live_local_info)
            
            if page_texts_dict:
                with result_container:
                    st.write("**1단계: 텍스트 생성 완료**")
                    with st.expander("생성된 텍스트 내용 보기"):
                        st.json(page_texts_dict)
            else:
                st.error("텍스트 콘텐츠 생성에 실패했습니다.")
                return

            # 2. 이미지 생성 및 표시
            with st.spinner("2/3 - DALL-E 이미지 생성 중..."):
                image_url = api.generate_product_image(st.session_state.product_info)

            if image_url:
                with result_container:
                    st.write("**2단계: DALL-E 원본 이미지 생성 완료**")
                    st.image(image_url, caption="텍스트가 추가되기 전의 원본 이미지입니다.")
            else:
                st.error("DALL-E 이미지 생성에 실패했습니다.")
                return

            # 3. 최종 조립 및 표시
            with st.spinner("3/3 - 최종 이미지 조립 중..."):
                page_texts_object = PageTextContent(**page_texts_dict)
                font_path = os.path.join(os.path.dirname(__file__), "fonts", "나눔손글씨_성실체.ttf")
                final_image_buffer = api.compose_final_image(page_texts_object, image_url, font_path, font_path)
            
            if final_image_buffer:
                st.session_state.final_detail_page = final_image_buffer.getvalue()
                st.success("상세페이지 조립이 완료되었습니다!")
                st.rerun()
            else:
                st.error("최종 이미지 조립에 실패했습니다.")

    with marketing_tab:
        render_expert_marketing_page()

def render_expert_marketing_page():
    st.header("🚀 전문가용 AI 마케팅 콘텐츠 생성")
    st.info("사장님의 상품에 딱 맞는 마케팅 콘텐츠를 AI가 자동으로 생성해 드립니다.")
    
    # 탭으로 콘텐츠 종류 선택
    insta_tab, blog_tab = st.tabs(["인스타그램 포스트", "네이버 블로그"])

    with insta_tab:
        # render_instagram_creator_ui()
        render_instagram_creator_ui()
    with blog_tab:
        render_naver_blog_creator_ui()

def render_instagram_creator_ui():
    st.subheader("📸 AI 인스타그램 포스트")
    st.write("AI 마케팅 전문가가 사장님의 브랜딩에 맞춰 최고의 인스타그램 게시물을 생성합니다.")

    if st.button("✨ 최적화된 인스타그램 게시물 생성하기", type="primary", use_container_width=True):
        content_key = 'instagram_post'
        st.session_state.marketing_content[content_key] = None
        
        with st.spinner("AI 인스타그램 전문가가 콘텐츠를 제작하고 있습니다..."):
            post_data = api.generate_instagram_post(st.session_state.branding_result, st.session_state.product_info)
        
        if post_data:
            with st.spinner("콘텐츠에 맞는 이미지를 DALL-E로 생성 중입니다..."):
                image_bytes = api.generate_dalle_image_from_prompt(post_data.get('image_prompt'))
            if image_bytes:
                st.session_state.marketing_content[content_key] = {"image": image_bytes, "post_text": post_data.get('post_text'), "hashtags": post_data.get('hashtags')}
                st.success("인스타그램 게시물 생성이 완료되었습니다!")
            else:
                st.error("이미지 생성에 실패했습니다.")
        else:
            st.error("게시물 콘텐츠 생성에 실패했습니다.")
        st.rerun()

    if 'instagram_post' in st.session_state.marketing_content and st.session_state.marketing_content['instagram_post']:
        content = st.session_state.marketing_content['instagram_post']
        st.markdown("---")
        st.subheader("✅ 생성된 인스타그램 게시물 미리보기")
        
        with st.container(border=True):
            col1, col2 = st.columns([1, 5])
            with col1:
                st.markdown(f"**{st.session_state.product_info.get('상품명', '우리가게_이름').replace(' ', '_')}**")
                st.caption(f"{st.session_state.product_info.get('원산지', '대한민국')}")
            
            st.image(content['image'], use_container_width=True)
            st.write("❤️ 💬 ✈️")
            st.text_area("게시물 문구 (수정 가능)", value=content['post_text'], height=200, key="insta_post_text_edit")
            st.text_area("해시태그 (수정 가능)", value=" ".join([f"#{tag}" for tag in content['hashtags']]), key="insta_hashtags_edit")

            st.write("**게시물 본문**")
            st.code(content['post_text'], language='text')

            st.write("**해시태그**")
            st.code(" ".join([f"#{tag}" for tag in content['hashtags']]), language='text')

        st.markdown("---")
        st.write("**콘텐츠 활용하기**")
        st.download_button("이미지 다운로드", content['image'], "instagram_post.png", "image/png", use_container_width=True)
            
def render_naver_blog_creator_ui():
    st.subheader("✍️ AI 네이버 블로그 정보성 포스팅")
    st.write("AI 전문가가 신뢰도 높은 정보성 블로그 글을 작성하여 잠재 고객을 유치합니다.")

    if st.button("✨ 정보성 블로그 포스팅 생성하기", type="primary", use_container_width=True):
        content_key = 'naver_blog_post'
        st.session_state.marketing_content[content_key] = None
        
        with st.spinner("AI 전문가가 블로그 포스팅을 작성하고 있습니다..."):
            post_data = api.generate_naver_blog_post(st.session_state.branding_result, st.session_state.product_info)
        
        if post_data:
            st.session_state.marketing_content[content_key] = post_data
            st.success("블로그 포스팅 생성이 완료되었습니다!")
        else:
            st.error("블로그 포스팅 생성에 실패했습니다.")
        st.rerun()

    if 'naver_blog_post' in st.session_state.marketing_content and st.session_state.marketing_content['naver_blog_post']:
        content = st.session_state.marketing_content['naver_blog_post']
        st.markdown("---")
        st.subheader("✅ 생성된 블로그 포스팅 미리보기")

        with st.container(border=True):
            st.markdown(f"## {content.get('title', '')}")
            col1, col2 = st.columns([1, 9])
            with col1:
                st.image("https://ssl.pstatic.net/static/blog/img_profile.png", width=50)
            with col2:
                st.markdown(f"**{st.session_state.product_info.get('상품명', '우리가게').replace(' ', '_')}**")
            st.divider()
            st.markdown(content.get('body', ''), unsafe_allow_html=True)
            st.divider()
            tags_html = "".join(f"<span style='background-color: #f3f3f3; color: #666; padding: 5px 10px; border-radius: 15px; margin: 3px; display: inline-block;'>#{tag}</span>" for tag in content.get('tags', []))
            st.markdown(tags_html, unsafe_allow_html=True)
            st.markdown("---")

        st.markdown("---")
        st.write("**콘텐츠 활용하기**")
        st.write("아래 상자의 복사 버튼을 눌러 HTML 전체를 복사한 후, 네이버 블로그 글쓰기 화면의 'HTML' 모드에 붙여넣으세요.")
        st.code(content.get('body', ''), language='html')
                
def render_branding_concept_cards():
    """브랜드 컨셉을 '정보 상자(카드)' 형태로 보여주는 함수"""
    
    b = st.session_state.branding_result
    if not isinstance(b, BrandingOutput):
        st.error("브랜딩 결과가 아직 생성되지 않았거나, 올바르지 않습니다.")
        return

    # 카드 1: 핵심 컨셉
    with st.container(border=True):
        st.subheader("💡 우리 브랜드의 핵심 약속")
        st.write("AI는 사장님의 이야기 속에서 우리 브랜드가 고객에게 전달해야 할 가장 중요한 가치를 발견했습니다.")
        st.markdown(f"<div style='background-color:#F0F8FF; padding: 15px; border-radius: 10px; color: #121111; text-align: center; font-weight: bold; font-size: 1.1em;'>{b.core_concept}</div>", unsafe_allow_html=True)

    st.markdown("---")

    # 카드 2: 브랜드 슬로건
    with st.container(border=True):
        st.subheader("🗣️ 고객의 마음을 사로잡을 한마디")
        st.write("이 슬로건은 상품 포장, 온라인 스토어, 광고 등 모든 곳에 사용할 수 있는 강력한 무기입니다.")
        
        # 슬로건 목업 이미지 표시 (첫 번째 상세페이지 이미지를 활용)
        if st.session_state.detail_page_images and st.session_state.detail_page_images[0]:
            st.image(st.session_state.detail_page_images[0], use_container_width=True, caption="[활용 예시] 상세페이지 대표 이미지")
        
        st.markdown(f"<h3 style='text-align: center; color: #FFBF00;'>\"{b.slogan}\"</h3>", unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        if c1.button("다른 슬로건 제안받기", use_container_width=True):
            with st.spinner("새로운 슬로건을 구상하고 있습니다..."):
                alternatives = api.regenerate_slogan(
                    core_concept=b.core_concept,
                    original_slogan=b.slogan
                )
                st.session_state.slogan_alternatives = alternatives
                st.rerun()
                
        if c2.button("마음에 들어요!", type="primary", use_container_width=True):
            st.toast("👍 슬로건이 마음에 드셨다니 다행입니다!", icon="😊")

    st.markdown("---")

    # 카드 3: 핵심 키워드
    with st.container(border=True):
        st.subheader("#️ 우리 가게를 알릴 핵심 키워드")
        st.write("이 키워드들은 인스타그램 해시태그나 블로그 포스팅에 사용하면 더 많은 고객을 만나는 데 큰 도움이 됩니다.")
        
        keyword_html = "".join(f"<span style='background-color: #E6F3FF; color: #0066CC; padding: 8px 15px; border-radius: 20px; margin: 5px; display: inline-block;'>#{kw}</span>" for kw in b.keywords)
        st.markdown(f"<div style='text-align: center; padding: 10px;'>{keyword_html}</div>", unsafe_allow_html=True)
        
    st.markdown("---")
    
    # 카드 4: 브랜드 스토리
    with st.container(border=True):
        st.subheader(" 사장님의 진심이 담긴, 브랜드 스토리")
        st.write("AI가 사장님의 목소리를 바탕으로, 고객의 마음을 움직일 감동적인 이야기를 완성했습니다. 자유롭게 수정해보세요.")
        
        edited_story = st.text_area(
            "브랜드 스토리 (직접 수정 가능)",
            value=b.story,
            height=300,
            key="story_edit_area"
        )
        
        st.write("**글의 분위기를 바꿔볼까요?**")
        c1, c2, c3 = st.columns(3)
        if c1.button("더 전문적으로", use_container_width=True): st.toast("기능 준비 중입니다.", icon="🔧")
        if c2.button("더 친근하게", use_container_width=True): st.toast("기능 준비 중입니다.", icon="🔧")
        if c3.button("더 짧게 요약", use_container_width=True): st.toast("기능 준비 중입니다.", icon="🔧")
    
    st.markdown("---")
    
    with st.expander("🔍 AI가 참고한 실시간 웹 검색 결과 보기"):
        st.info("AI는 아래의 최신 웹 정보를 바탕으로 브랜딩 컨셉과 스토리를 생성했습니다.")
            
        # 세션 상태에 저장된 웹 검색 결과를 가져옵니다.
        # st.session_state.live_local_info는 processing 단계에서 저장됩니다.
        live_info = st.session_state.get('live_local_info', '검색된 정보가 없습니다.')
            
        # st.markdown을 사용하면 줄바꿈이 그대로 표시됩니다.
        st.markdown(live_info)
    # 다음 단계로 이동 버튼
    st.success("이제 이 멋진 브랜드 컨셉으로 실제 마케팅에 사용할 콘텐츠들을 만들어볼까요?")
    st.write("상단의 **'② 상세페이지 시안'** 탭을 눌러 AI가 생성한 이미지를 확인해보세요!")
            
# --- 3. 메인 로직: 현재 단계에 따라 적절한 함수 호출 ---
step_map = {
    'welcome': render_welcome_page,
    'get_name': lambda: render_input_step(
        step_title="1단계: 상품 이름 정하기",
        subheader="가장 먼저, 판매하실 상품의 이름이 무엇인가요?",
        placeholder="예: 해남 유기농 배추",
        info_key="상품명",
        next_step="get_origin"
    ),
    'get_origin': lambda: render_input_step(
        step_title="2단계: 상품 원산지 정하기",
        subheader=f"'{st.session_state.product_info.get('상품명', '상품')}'은(는) 어디에서 왔나요?",
        placeholder="예: 전라남도 해남",
        info_key="원산지",
        next_step="get_story"
    ),
    'get_story': render_story_step,
    'get_image': render_image_step,
    'get_category': render_category_step,
    'processing': render_processing_page,
    'show_results': render_results_page,
}

render_function = step_map.get(st.session_state.current_step, render_welcome_page)
render_function()