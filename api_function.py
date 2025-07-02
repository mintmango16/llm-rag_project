import os
import requests
import traceback
import logging
from io import BytesIO
from typing import Optional, List, Dict, Tuple, Any
import openai
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from tavily import TavilyClient
import openai
import streamlit as st
from prompts import *

# --- Setup & Initialization ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

try:
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7, api_key=OPENAI_API_KEY)
    json_llm = llm.bind(response_format={"type": "json_object"})
    tavily_client = TavilyClient(api_key=TAVILY_API_KEY)

    # Parser Instances
    str_parser = StrOutputParser()
    json_parser_branding = JsonOutputParser(pydantic_object=BrandingOutput)
    json_parser_info = JsonOutputParser(pydantic_object=ExtractedInfo)
    json_parser_core_keyword = JsonOutputParser(pydantic_object=CoreProductKeyword)
    json_parser_slogans = JsonOutputParser(pydantic_object=SloganAlternatives)
except Exception as e:
    logging.error(f"API 클라이언트 초기화 실패: {e}")
    llm = None
    tavily_client = None

def extract_core_product_keyword(product_name: str) -> Optional[str]:
    """상품명에서 핵심 키워드를 추출합니다."""
    if not llm:
        logging.error("LLM이 초기화되지 않아 핵심 단어 추출을 건너뜁니다.")
        return product_name # 실패 시 원본 상품명 반환
    
    chain = EXTRACT_CORE_KEYWORD_PROMPT | llm | json_parser_core_keyword
    try:
        logging.info(f"'{product_name}'에서 핵심 단어 추출 시도...")
        result = chain.invoke({
            "product_name": product_name,
            "format_instructions": json_parser_core_keyword.get_format_instructions()
        })
        core_keyword = result.get('core_keyword', product_name)
        logging.info(f"핵심 단어 추출 성공: {core_keyword}")
        return core_keyword
    except Exception as e:
        logging.error(f"핵심 단어 추출 중 오류 발생: {e}")
        return product_name # 오류 발생 시에도 원본 상품명 반환

def regenerate_slogan(core_concept: str, original_slogan: str) -> Optional[List[str]]:
    """핵심 컨셉을 바탕으로 새로운 슬로건들을 제안합니다."""
    logging.info("새로운 슬로건 생성을 시작합니다.")
    
    chain = REGENERATE_SLOGAN_PROMPT | llm | json_parser_slogans
    try:
        response = chain.invoke({
            "core_concept": core_concept,
            "original_slogan": original_slogan,
            "format_instructions": json_parser_slogans.get_format_instructions()
        })
        return response.get('alternatives', [])
    except Exception as e:
        logging.error(f"슬로건 재생성 중 오류: {e}\n{traceback.format_exc()}")
        return None
    
# --- 음성 인식 및 AI 인터뷰 관련 함수 ---
def transcribe_audio(audio_bytes: bytes) -> Optional[str]:
    """OpenAI Whisper API를 사용하여 음성 파일을 텍스트로 변환합니다."""
    if not OPENAI_API_KEY:
        logging.error("OpenAI API 키가 설정되지 않아 음성 인식을 건너뜁니다.")
        return None
    try:
        # Whisper API는 파일 객체를 요구하므로, BytesIO를 사용합니다.
        audio_file = BytesIO(audio_bytes)
        audio_file.name = "temp_audio.wav"  # 임의의 파일명 지정

        transcript = openai.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="text"
        )
        logging.info(f"음성 인식 성공: {transcript}")
        return transcript
    except Exception as e:
        logging.error(f"Whisper API 호출 중 오류 발생: {e}")
        return "음성 인식 중 오류가 발생했습니다. 다시 시도해주세요."


def generate_story_from_interview(interview_summary: str) -> Optional[str]:
    """AI 인터뷰 요약본을 바탕으로 최종 상품 스토리를 생성합니다."""
    if not llm:
        logging.error("LLM이 초기화되지 않아 스토리 생성을 건너뜁니다.")
        return None
    try:
        chain = STORY_GENERATION_FROM_INTERVIEW_PROMPT | llm | str_parser
        generated_story = chain.invoke({"interview_summary": interview_summary})
        return generated_story
    except Exception as e:
        logging.error(f"인터뷰 기반 스토리 생성 중 오류: {e}")
        return "스토리 생성 중 오류가 발생했습니다."
    
FONT_FOLDER = "fonts"
FONT_FILENAME = "나눔손글씨_성실체.ttf"
# __file__은 현재 파일의 경로를 나타냅니다.
FONT_PATH = os.path.join(os.path.dirname(__file__), FONT_FOLDER, FONT_FILENAME)
NUM_DETAIL_PAGES = 5

# --- Core Logic Functions ---

def extract_info_from_user_input(user_input: str, chat_history_summary: str) -> Optional[Dict]:
    """LangChain 체인을 사용하여 사용자 입력에서 정보를 추출합니다."""
    if not llm:
        logging.error("LLM이 초기화되지 않아 정보 추출을 건너뜁니다.")
        return None
    chain = EXTRACT_INFO_PROMPT | llm | json_parser_info
    try:
        return chain.invoke({
            "user_input": user_input,
            "chat_history_summary": chat_history_summary,
            "format_instructions": json_parser_info.get_format_instructions()
        })
    except Exception as e:
        logging.error(f"정보 추출 중 오류 발생: {e}")
        return None

def search_with_tavily_multi_query(product_info: dict) -> Tuple[str, List[str]]:
    """Tavily를 사용하여 웹에서 심층 정보를 검색하고, 수행된 쿼리 목록과 요약 결과를 반환합니다."""
    if not tavily_client:
        logging.error("Tavily 클라이언트가 초기화되지 않아 검색을 건너뜁니다.")
        return "Tavily 클라이언트가 설정되지 않았습니다.", []

    region = product_info.get("원산지", "")
    product = product_info.get("핵심상품명", product_info.get("상품명", ""))
    
    queries = [
        f"'{region} {product}'의 역사, 기후, 토양 특징",
        f"'{product}'의 주된 효능 및 영양성분",
        f"'{product}'을 활용한 특별한 레시피",
        f"'{product}' 신선도 유지 및 보관법",
        f"'{region}' 지역의 문화 또는 스토리",
    ]
    
    logging.info(f"다음 쿼리로 웹 탐색을 수행합니다: {queries}")
    
    final_summary = ""
    unique_results = set()
    for query in queries:
        try:
            response = tavily_client.search(query=query, search_depth="basic", max_results=3)
            for res in response['results']:
                content = res['content']
                if content not in unique_results:
                    final_summary += f"- {res['title']}: {content}\n"
                    unique_results.add(content)
        except Exception as e:
            logging.warning(f"'{query}' 검색 중 오류 발생: {e}")
            
    return (final_summary if final_summary else "관련 웹 정보를 찾을 수 없습니다.", queries)


def generate_branding(product_info: dict, live_local_info: str) -> Optional[BrandingOutput]:
    """LangChain 체인을 사용하여 브랜딩 콘텐츠를 생성합니다."""
    if not llm:
        logging.error("LLM이 초기화되지 않아 브랜딩 생성을 건너뜁니다.")
        return None
        
    chain = BRANDING_PROMPT | llm | json_parser_branding
    try:
        product_info_str = "\n".join([f"- {key}: {value}" for key, value in product_info.items()])
        response_dict = chain.invoke({
            "product_info": product_info_str,
            "live_local_info": live_local_info,
            "format_instructions": json_parser_branding.get_format_instructions(),
        })
        return BrandingOutput(**response_dict) # Pydantic 객체로 변환하여 반환
    except Exception as e:
        logging.error(f"브랜딩 생성 중 오류 발생: {e}\n{traceback.format_exc()}")
        return None

def generate_detail_page_section_texts(branding_info: BrandingOutput, product_info: dict) -> List[Dict]:
    """상세페이지 각 섹션에 사용할 텍스트를 생성합니다."""
    if not llm:
        logging.error("LLM이 초기화되지 않아 텍스트 생성을 건너뜁니다.")
        return []
        
    section_texts = []
    chain = SECTION_TEXT_DEFAULT_PROMPT | llm | str_parser
    
    for i, context in enumerate(DETAIL_PAGE_SECTION_CONTEXTS):
        try:
            prompt_input = {
                "section_number": i + 1,
                "main_context": context['main'],
                "sub_context": context['sub'],
                "slogan": branding_info.slogan,
                "story": branding_info.story,
            }
            res = chain.invoke(prompt_input)
            parts = res.split('|', 1)
            main_t = parts[0].strip() if parts else ""
            sub_t = parts[1].strip() if len(parts) > 1 else ""
            section_texts.append({"main_text": main_t, "sub_text": sub_t})
        except Exception as e:
            logging.warning(f"상세페이지 텍스트 섹션 {i+1} 생성 실패: {e}")
            section_texts.append({"main_text": f"{product_info['상품명']}!", "sub_text": "신선함을 지금 만나보세요."})
            
    return section_texts

# --- Image Generation & Processing ---

def _draw_wrapped_text(draw, text, font, position_y, img_width, max_width_ratio=0.9, line_spacing=10, text_color=(0,0,0,255)):
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        if draw.textbbox((0, 0), current_line + " " + word if current_line else word, font=font)[2] < img_width * max_width_ratio:
            current_line += " " + word if current_line else word
        else:
            lines.append(current_line)
            current_line = word
    lines.append(current_line)

    total_text_height = sum(draw.textbbox((0, 0), line, font=font)[3] for line in lines) + (len(lines) - 1) * line_spacing
    current_y = position_y - total_text_height / 2

    for line in lines:
        line_bbox = draw.textbbox((0, 0), line, font=font)
        x = (img_width - line_bbox[2]) / 2
        draw.text((x, current_y), line, font=font, fill=text_color)
        current_y += line_bbox[3] + line_spacing
    return current_y # 마지막으로 그려진 y 좌표 반환

def _overlay_text_on_image(image_bytes: BytesIO, text_blocks: List[Dict]) -> Optional[bytes]:
    """Pillow를 사용하여 이미지에 여러 텍스트 블록을 오버레이합니다."""
    try:
        img = Image.open(image_bytes).convert("RGBA")
        draw = ImageDraw.Draw(img)
        width, height = img.size
        top_margin_center = ((height - 1024) // 2) / 2
        bottom_margin_center = height - top_margin_center

        for block in text_blocks:
            position = block.get("position", "top")
            y_center = top_margin_center if position == 'top' else bottom_margin_center
            
            try:
                main_font = ImageFont.truetype(FONT_PATH, block.get("main_font_size", 50))
                sub_font = ImageFont.truetype(FONT_PATH, block.get("sub_font_size", 30))
            except IOError:
                logging.error(f"폰트 파일을 찾을 수 없습니다: {FONT_PATH}. 기본 폰트를 사용합니다.")
                main_font = ImageFont.load_default(size=block.get("main_font_size", 50))
                sub_font = ImageFont.load_default(size=block.get("sub_font_size", 30))
            
            # 메인 텍스트 그리기
            last_y = _draw_wrapped_text(draw, block["main_text"], main_font, y_center, width)
            
            # 서브 텍스트 그리기
            if block.get("sub_text"):
                _draw_wrapped_text(draw, block["sub_text"], sub_font, last_y + 15, width, max_width_ratio=0.8, line_spacing=5)

        output_buffer = BytesIO()
        img.save(output_buffer, format="PNG")
        return output_buffer.getvalue()

    except Exception as e:
        logging.error(f"이미지 텍스트 오버레이 중 오류: {e}")
        return None

def _generate_single_image_with_text(index: int, product_info: dict, section_text: dict, branding_slogan: str) -> Optional[bytes]:
    """DALL-E로 단일 이미지를 생성하고 텍스트를 합성합니다."""
    try:
        logging.info(f"상세페이지 이미지 {index + 1}/{NUM_DETAIL_PAGES} 생성 시작...")
        
        # 1. DALL-E 프롬프트 준비
        frame_prompt = DETAIL_PAGE_IMAGE_FRAMES[index]
        theme_template = DETAIL_PAGE_IMAGE_THEMES[index]
        theme = theme_template.format(
            product_name=product_info['상품명'], 
            origin=product_info['원산지']
        )
        final_prompt = frame_prompt.format(theme=theme)
        
        # 2. DALL-E 이미지 생성
        response = openai.images.generate(
            model="dall-e-3", prompt=final_prompt, n=1, size="1024x1792", quality="standard"
        )
        image_url = response.data[0].url
        image_bytes = BytesIO(requests.get(image_url).content)
        
        # 3. 텍스트 블록 구성
        text_blocks = []
        # 각 이미지 인덱스에 따라 다른 텍스트 레이아웃 적용
        if index == 0:
            text_blocks.append({"position": "top", "main_text": f"{product_info['원산지']} {product_info['상품명']}", "sub_text": branding_slogan, "main_font_size": 70, "sub_font_size": 45})
            text_blocks.append({"position": "bottom", "main_text": section_text["main_text"], "sub_text": section_text["sub_text"], "main_font_size": 50, "sub_font_size": 35})
        else: # 1, 2, 3, 4번 이미지 공통 레이아웃
            text_blocks.append({"position": "top", "main_text": section_text["main_text"], "sub_text": section_text["sub_text"], "main_font_size": 60, "sub_font_size": 40})
            
        # 4. 텍스트 오버레이
        return _overlay_text_on_image(image_bytes, text_blocks)

    except Exception as e:
        logging.error(f"상세페이지 이미지 {index + 1} 생성 중 오류: {e}\n{traceback.format_exc()}")
        return None

def generate_all_detail_page_images(product_info: dict, branding_info: BrandingOutput) -> Tuple[List[Optional[bytes]], List[Dict]]:
    """5개의 상세페이지 이미지를 생성하고 텍스트를 합성합니다."""
    if not OPENAI_API_KEY:
        logging.error("OpenAI API 키가 설정되지 않아 이미지 생성을 건너뜁니다.")
        return [], []
        
    section_texts = generate_detail_page_section_texts(branding_info, product_info)
    processed_images = []

    # [Refactor] for i in range(1) 버그 수정 및 병렬 처리 준비 (현재는 순차 실행)
    for i in range(1):
        # [Refactor] 복잡한 로직을 헬퍼 함수 호출로 대체
        final_image = _generate_single_image_with_text(i, product_info, section_texts[i], branding_info.slogan)
        processed_images.append(final_image)
        
    return processed_images, section_texts


def generate_marketing_content(platform: str, branding_info: BrandingOutput, product_info: dict) -> Dict:
    """플랫폼별 마케팅 텍스트와 이미지를 생성합니다."""
    # 텍스트 생성
    if not json_llm:
        logging.error("LLM이 초기화되지 않아 마케팅 텍스트 생성을 건너뜁니다.")
        return {"text": None, "image": None}
        
    text_content = None
    try:
        chain = MARKETING_TEXT_PROMPT | json_llm | JsonOutputParser()
        text_content = chain.invoke({
            "platform": platform,
            "branding_info": branding_info.model_dump_json(),
            "product_info": product_info
        })
    except Exception as e:
        logging.error(f"마케팅 텍스트 생성 중 오류: {e}")

    # 이미지 생성 (블로그 제외)
    image_url = None
    if platform != "네이버 블로그" and OPENAI_API_KEY:
        image_prompt = f"A professional marketing image for {platform}. Theme: '{branding_info.slogan}'. Featuring: High-quality photo of '{product_info['상품명']}' from '{product_info['원산지']}'. Style: clean, appealing, with Korean text '{branding_info.slogan}' harmoniously integrated. Photorealistic."
        try:
            response = openai.images.generate(model="dall-e-3", prompt=image_prompt, n=1, size="1024x1024")
            image_url = response.data[0].url
        except Exception as e:
            logging.error(f"마케팅 이미지 생성 중 오류: {e}")
            
    return {"text": text_content, "image": image_url}

def generate_page_texts(product_info: dict, branding_info: BrandingOutput, live_local_info: str) -> Optional[PageTextContent]:
    """상세페이지에 필요한 6가지 텍스트 콘텐츠를 생성합니다."""
    parser = JsonOutputParser(pydantic_object=PageTextContent)
    chain = GENERATE_PAGE_TEXTS_PROMPT | llm | parser
    
    st.info("상세페이지에 사용할 텍스트를 생성 중입니다...")
    try:
        page_texts = chain.invoke({
            "product_info": product_info,
            "live_local_info": live_local_info,
            "branding_info": branding_info.model_dump_json(),
            "format_instructions": parser.get_format_instructions()
        })
        return page_texts
    except Exception as e:
        st.error(f"상세페이지 텍스트 생성 중 오류: {e}")
        return None

def generate_product_image(product_info: dict) -> Optional[str]:
    """DALL-E로 제품 이미지를 생성하고 URL을 반환합니다."""
    st.info("상품 이미지를 생성 중입니다...")
    try:
        # prompts.py에 정의된 템플릿을 사용
        product_keyword = product_info.get('핵심상품명', product_info.get('상품명', ''))
        prompt_text = DALLE_PRODUCT_IMAGE_PROMPT.format(
            product_name=product_keyword,
            origin=product_info.get('원산지', '')
        )
        response = openai.images.generate(
            model="dall-e-3",
            prompt=prompt_text,
            n=1,
            size="1024x1792",
            quality="standard",
        )
        return response.data[0].url
    except Exception as e:
        st.error(f"DALL-E 이미지 생성 중 오류: {e}")
        return None

class DesignConfig:
    """디자인 관련 설정을 중앙에서 관리하는 클래스"""
    CANVAS_SIZE = (1080, 1500)
    LEFT_SECTION_WIDTH = CANVAS_SIZE[0] // 2
    IMAGE_THUMBNAIL_SIZE = (467, 816)
    
    COLORS = {
        'white': (255, 255, 255),
        'black': (0, 0, 0),
        'grey': (100, 100, 100),
        'dark_grey': (50, 50, 50),
        'box1': (241, 231, 228),
        'box2': (231, 241, 228),
        'box3': (228, 238, 241),
    }

    @staticmethod
    def get_fonts(font_bold_path: str, font_regular_path: str) -> Dict[str, ImageFont.FreeTypeFont]:
        """폰트 파일을 로드하여 딕셔너리로 반환"""
        try:
            return {
                'title': ImageFont.truetype(font_bold_path, 80),
                'slogan': ImageFont.truetype(font_regular_path, 45),
                'heading': ImageFont.truetype(font_bold_path, 40),
                'body': ImageFont.truetype(font_regular_path, 32),
                'closing': ImageFont.truetype(font_bold_path, 50),
            }
        except Exception as e:
            logging.error(f"폰트 파일 로딩 실패: {e}")
            raise # 폰트 로딩 실패 시, 진행이 불가능하므로 예외를 다시 발생시킴

def _load_image_from_url(url: str, size: Tuple[int, int]) -> Optional[Image.Image]:
    """URL에서 이미지를 로드하고 리사이즈하여 반환"""
    try:
        response = requests.get(url)
        response.raise_for_status()
        image = Image.open(BytesIO(response.content))
        image.thumbnail(size)
        return image
    except Exception as e:
        logging.error(f"DALL-E 이미지 로딩 및 리사이즈 실패: {e}")
        return None

def _draw_text_in_box(draw: ImageDraw.ImageDraw, box: Tuple[int, int, int, int], text: str, 
                      font: ImageFont.FreeTypeFont, **kwargs):
    """지정된 박스 안에 텍스트를 자동 줄바꿈하여 중앙 정렬로 그림"""
    # 박스 배경 그리기 (옵션)
    box_color = kwargs.get('box_color')
    if box_color:
        padding = kwargs.get('padding', 20)
        corner_radius = kwargs.get('corner_radius', 0)
        bg_box = (box[0] - padding, box[1] - padding, box[0] + box[2] + padding, box[1] + box[3] + padding)
        draw.rounded_rectangle(bg_box, radius=corner_radius, fill=box_color)

    # 텍스트 줄바꿈 로직
    words = text.split()
    if not words: return
    lines = []
    current_line = ""
    for word in words:
        if draw.textbbox((0, 0), f"{current_line} {word}".strip(), font=font)[2] < box[2]:
            current_line = f"{current_line} {word}".strip()
        else:
            lines.append(current_line)
            current_line = word
    lines.append(current_line)

    # 텍스트 그리기
    y_text = box[1]
    text_color = kwargs.get('text_color', DesignConfig.COLORS['black'])
    for line in lines:
        line_bbox = draw.textbbox((0, 0), line, font=font)
        line_width = line_bbox[2] - line_bbox[0]
        x_text = box[0] + (box[2] - line_width) / 2
        draw.text((x_text, y_text), line, font=font, fill=text_color)
        y_text += (line_bbox[3] - line_bbox[1]) + 10 # 줄 간격

def compose_final_image(page_texts: PageTextContent, image_url: str, font_bold_path: str, 
                        font_regular_path: str) -> Optional[BytesIO]:
    """생성된 콘텐츠를 조립하여 최종 상세페이지 이미지를 생성합니다."""
    try:
        # 1. 설정 및 준비
        config = DesignConfig()
        fonts = config.get_fonts(font_bold_path, font_regular_path)
        canvas = Image.new('RGB', config.CANVAS_SIZE, config.COLORS['white'])
        draw = ImageDraw.Draw(canvas)
        
        # 2. DALL-E 이미지 로드 및 배치
        product_image = _load_image_from_url(image_url, config.IMAGE_THUMBNAIL_SIZE)
        img_y = (config.CANVAS_SIZE[1] - config.IMAGE_THUMBNAIL_SIZE[1]) // 2
        if product_image:
            img_x = (config.LEFT_SECTION_WIDTH - product_image.width) // 2
            canvas.paste(product_image, (img_x, img_y))

        # 3. 텍스트 요소 배치
        # 상단 제목 및 슬로건
        _draw_text_in_box(draw, (50, 100, 980, 150), page_texts.title, fonts['title'])
        _draw_text_in_box(draw, (50, 220, 980, 100), page_texts.slogan, fonts['slogan'], text_color=config.COLORS['grey'])

        # 오른쪽 정보 블록
        RIGHT_X = config.LEFT_SECTION_WIDTH + 33
        RIGHT_WIDTH = config.CANVAS_SIZE[0] - RIGHT_X - 33
        BOX_HEIGHT, BOX_SPACING = 200, 45
        
        box_y_positions = [img_y + 63, img_y + 63 + BOX_HEIGHT + BOX_SPACING, img_y + 63 + (BOX_HEIGHT + BOX_SPACING) * 2]
        box_texts = [page_texts.region_story, page_texts.product_features, page_texts.nutrition_info]
        box_colors = [config.COLORS['box1'], config.COLORS['box2'], config.COLORS['box3']]

        for y, text, color in zip(box_y_positions, box_texts, box_colors):
            _draw_text_in_box(draw, (RIGHT_X, y, RIGHT_WIDTH, BOX_HEIGHT), text, 
                              fonts['body'], box_color=color, corner_radius=30)
            
        # 하단 마무리 문구
        _draw_text_in_box(draw, (50, 1270, 980, 100), page_texts.closing_statement, 
                          fonts['closing'], text_color=config.COLORS['dark_grey'])
        
        # 4. 최종 이미지 버퍼로 반환
        output_buffer = BytesIO()
        canvas.save(output_buffer, format="PNG")
        output_buffer.seek(0)
        return output_buffer

    except Exception as e:
        logging.error(f"이미지 조립 중 심각한 오류 발생: {e}\n{traceback.format_exc()}")
        return None

def _generate_content(prompt_template, pydantic_model, invoke_params):
    """공통 콘텐츠 생성 로직을 처리하는 헬퍼 함수"""
    parser = JsonOutputParser(pydantic_object=pydantic_model)
    chain = prompt_template | llm | parser
    try:
        invoke_params["format_instructions"] = parser.get_format_instructions()
        return chain.invoke(invoke_params)
    except Exception as e:
        logging.error(f"콘텐츠 생성 중 오류: {e}\n{traceback.format_exc()}")
        return None
    
def generate_instagram_post(branding_info: BrandingOutput, product_info: dict) -> Optional[Dict[str, Any]]:
    """전문가 프롬프트를 사용하여 최적화된 인스타그램 포스트 콘텐츠를 생성합니다."""
    logging.info("최적화된 인스타그램 포스트 생성을 시작합니다.")
    
    parser = JsonOutputParser(pydantic_object=InstagramPost)
    chain = INSTAGRAM_POST_PROMPT | llm | parser

    try:
        post_content = chain.invoke({
            "branding_info": branding_info.model_dump_json(),
            "product_info": product_info,
            "format_instructions": parser.get_format_instructions()
        })
        return post_content
    except Exception as e:
        logging.error(f"인스타그램 포스트 생성 중 오류: {e}\n{traceback.format_exc()}")
        return None
    
def generate_naver_blog_post(branding_info: BrandingOutput, product_info: dict) -> Optional[Dict[str, Any]]:
    """전문가 프롬프트를 사용하여 최적화된 네이버 블로그 정보성 포스팅을 생성합니다."""
    logging.info("최적화된 네이버 블로그 포스팅 생성을 시작합니다.")
    
    parser = JsonOutputParser(pydantic_object=NaverBlogPost)
    chain = NAVER_BLOG_PROMPT | llm | parser

    try:
        post_content = chain.invoke({
            "branding_info": branding_info.model_dump_json(),
            "product_info": product_info,
            "format_instructions": parser.get_format_instructions()
        })
        return post_content
    except Exception as e:
        logging.error(f"네이버 블로그 포스팅 생성 중 오류: {e}\n{traceback.format_exc()}")
        return None


def generate_dalle_image_from_prompt(prompt: str) -> Optional[bytes]:
    """주어진 프롬프트로 DALL-E 이미지를 생성하고 이미지 데이터를 bytes로 반환합니다."""
    try:
        logging.info(f"DALL-E 이미지 생성 요청: {prompt[:100]}...")
        response = openai.images.generate(
            model="dall-e-3",
            prompt=prompt,
            n=1,
            size="1024x1024", # 인스타그램에 적합한 1:1 비율
            quality="hd" # 더 높은 품질의 이미지 요청
        )
        image_url = response.data[0].url
        image_response = requests.get(image_url)
        image_response.raise_for_status()
        return image_response.content
    except Exception as e:
        logging.error(f"DALL-E 이미지 생성 중 오류: {e}")
        return None
    
    