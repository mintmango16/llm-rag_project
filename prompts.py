from pydantic import BaseModel, Field
from typing import Optional, List

from langchain_core.prompts import PromptTemplate

# --- Pydantic Output Schemas ---

class BrandingOutput(BaseModel):
    core_concept: str = Field(description="모든 브랜딩 요소를 관통하는 단 하나의 핵심 컨셉 문장")
    introduction: str = Field(description="핵심 컨셉이 드러나는, 시적인 표현을 담은 브랜드 소개")
    slogan: str = Field(description="핵심 컨셉을 함축한, 고객의 마음을 파고드는 한 문장의 슬로건")
    keywords: List[str] = Field(description="핵심 컨셉과 관련된 창의적이고 구체적인 키워드 5개")
    story: str = Field(description="상품의 생산 과정, 생산자의 철학, 지역의 이야기를 엮고,마지막에는 상품의 구체적인 활용 용도나 레시피를 자연스럽게 제안하여 소비자의 감성과 실용성을 모두 만족시키는 몰입감 있는 스토리텔링 텍스트")

class ExtractedInfo(BaseModel):
    product_name: Optional[str] = Field(None, description="상품명")
    origin: Optional[str] = Field(None, description="원산지")
    seller_story: Optional[str] = Field(None, description="판매자 스토리")
    desired_brand_image: Optional[str] = Field(None, description="원하는 브랜드 이미지 (예: 신선함, 전통, 활기찬)")

class PageTextContent(BaseModel):
    title: str = Field(description="[지역명] [상품명] 형식의 제목")
    slogan: str = Field(description="브랜드 슬로건")
    region_story: str = Field(description="지역의 특성과 상품을 자연스럽게 연결하는 1~2 문장의 스토리")
    product_features: str = Field(description="다른 상품과 차별화되는 상품의 우수성, 특징")
    nutrition_info: str = Field(description="상품의 대표적인 영양 정보 또는 건강상의 이점")
    closing_statement: str = Field(description="구매를 유도하거나 브랜드의 가치를 강조하는 마무리 문구")
    
class InstagramPost(BaseModel):
    """인스타그램 포스팅 하나에 대한 모델"""
    image_prompt: str = Field(description="DALL-E로 생성할, 시선을 사로잡는 고품질 이미지에 대한 상세한 프롬프트. 브랜드 컨셉과 게시물 내용이 잘 드러나야 함.")
    post_text: str = Field(description="게시물 본문에 들어갈 전체 텍스트. AIDA 모델에 따라 작성되며, 마지막에는 행동 유도 문구(Call-to-Action)를 포함함.")
    hashtags: List[str] = Field(description="게시물 확산을 위한, 검색 가능성이 높은 관련 해시태그 리스트 (10~15개)")
    
class NaverBlogPost(BaseModel):
    """네이버 블로그 포스팅 모델"""
    title: str = Field(description="검색엔진최적화(SEO)를 고려한, 사용자의 클릭을 유도하는 블로그 포스팅 제목")
    introduction: str = Field(description="독자의 흥미를 유발하고 글의 전체 내용을 암시하는 도입부 문단")
    body: str = Field(description="소제목(<h2>), 리스트(<li>), 강조(<strong>) 등 HTML 태그를 활용하여 가독성 좋게 작성된 본문 전체. 상품의 특징과 스토리를 전문가적 관점에서 자연스럽게 녹여내야 함.")
    conclusion: str = Field(description="내용을 요약하고 독자의 행동(구매, 댓글)을 유도하는 마무리 문단")
    tags: List[str] = Field(description="블로그 검색에 사용될 핵심 키워드 태그 리스트 (5~7개)")
    
class CoreProductKeyword(BaseModel):
    """상품명에서 핵심 키워드를 추출하기 위한 모델"""
    core_keyword: str = Field(description="수식어나 브랜드명을 제외한 상품의 본질적인 핵심 단어. 예: '햇살담은 영천 별빛 사과' -> '사과'")
    modifier: Optional[str] = Field(None, description="상품을 설명하는 수식어나 브랜드명. 예: '햇살담은 영천 별빛 사과' -> '햇살담은 별빛'")

class SloganAlternatives(BaseModel):
    """대안 슬로건 리스트를 위한 모델"""
    alternatives: List[str] = Field(description="기존 슬로건과 다른 새로운 스타일의 슬로건 3개 리스트")

# --- Chatbot & Branding Prompts ---
EXTRACT_INFO_PROMPT = PromptTemplate.from_template("...") # 생략

# --- 🔽 [신규] 상품명 핵심 단어 추출을 위한 프롬프트 🔽 ---
EXTRACT_CORE_KEYWORD_PROMPT = PromptTemplate.from_template(
    """
    당신은 주어진 상품명에서 핵심적인 상품 분류 단어를 추출하는 전문가입니다.
    예를 들어, '햇살담은 영천 별빛 사과'라는 상품명이 주어지면, 이 상품의 핵심은 '사과'입니다.
    '맛난 제주 감귤'의 핵심은 '감귤'입니다.

    아래 주어진 상품명에서, 수식어나 지역명을 제외한 상품의 본질적인 '핵심 단어'와 나머지 '수식어'를 추출해주세요.

    상품명: {product_name}

    {format_instructions}
    """
)
# --- Chatbot & Branding Prompts ---

# 1. 챗봇 정보 추출용 프롬프트 템플릿
EXTRACT_INFO_PROMPT = PromptTemplate.from_template(
    """
    당신은 사용자로부터 상품 브랜딩에 필요한 정보를 추출하는 AI 어시스턴트입니다.
    사용자의 최근 발화와 이전 대화 내용을 기반으로 다음 정보들을 추출하고 JSON 형태로 반환하세요.
    - product_name (상품명), origin (원산지), seller_story (판매자 스토리), desired_brand_image (원하는 브랜드 이미지)
    만약 특정 정보가 발화에 포함되어 있지 않으면 해당 필드는 null로 두세요.
    ---
    사용자의 이전 대화 요약: {chat_history_summary}
    ---
    사용자의 최근 발화: {user_input}
    ---
    출력 형식: {format_instructions}
    """
)

# 2. 브랜딩 생성용 프롬프트 템플릿
BRANDING_PROMPT = PromptTemplate.from_template(
    """
    ## [페르소나]
    당신은 대한민국 최고의 로컬 브랜딩 전략가, '장동민'입니다. 당신의 철학은 '모든 위대한 브랜드는 하나의 강력한 컨셉에서출발한다'는 것입니다.
    당신은 진부함을 혐오하며, 지역의 숨겨진 잠재력과 생산자의 영혼을 엮어 세상에 단 하나뿐인 스토리를 발견하고 재구성하는 전문가입니다.
    당신의 역할은 '창작(Fiction)'이 아니라, 흩어져 있는 '사실(Fact)'들을 창의적으로 연결하여 새로운 '의미(Meaning)'와 '맥락(Context)'을 부여하는 것입니다.

    ### [궁극적인 목표]
    주어진 [사용자 입력 정보]와 [실시간 웹 분석 정보]를 단순 조합하는 것을 넘어, 두 정보의 교차점에서 아무도 발견하지 못한 '단 하나의 핵심 컨셉(The Golden Thread)'을 발굴해야 합니다.
    그리고 당신이 만들어낼 모든 결과물(소개, 슬로건, 키워드, 스토리)은 이 '핵심 컨셉'이라는 실로 꿰어진 하나의 작품이 되어야 합니다.
    - 감성적인 서사 (생산자 철학, 지역 이야기 등)
    - 신뢰를 주는 정보 (효능, 영양 정보)
    - 구매를 돕는 정보 (구체적인 레시피, 보관법)

    ### [정보 소스]
    1.  **사용자 입력 정보**: {product_info}
    2.  **실시간 웹 분석 정보**: {live_local_info}

    ### [가장 중요한 업무 수행 절차]
    0.  **윤리 원칙 준수 (가장 우선)**: 절대 없는 사실을 지어내서는 안 됩니다. 모든 결과물은 반드시 [정보 소스]에 명시된 사실 또는 합리적인 추론에 기반해야 합니다.
    1.  **상품 유형 분석 (매우 중요)**: [사용자 입력 정보]의 '품목'을 확인하여 상품의 카테고리(예: 신선 채소, 가공식품 등)를 명확히 정의합니다. 
    **치명적 오류 방지 규칙: '상추'와 같은 신선 채소에 '숙성'이라는 단어를 사용하는 것은 절대 금물입니다.**
    2.  **핵심 컨셉(The Golden Thread) 정의**: 1단계의 분석을 바탕으로, 모든 [정보 소스]를 종합하여 이 브랜드를 관통할 '단 하나의 핵심 컨셉'을 한 문장으로 정의합니다.
    3.  **창의적 증거 수집**: [정보 소스]에서 2단계에서 정의한 '핵심 컨셉'을 뒷받침할 수 있는 구체적인 사실, 이야기, 단어들을 최소 3가지 이상 찾아냅니다.
    4.  **콘텐츠 요소 추출 및 구성**: [정보 소스]에서 아래의 각 항목에 해당하는 내용을 추출하고, 어떻게 연결할지 전략을 수립합니다.
        - **감성 스토리 요소**: 생산자의 철학, 지역의 이야기, 구체적인 생산 과정 등
        - **실용 정보 요소**: 상품의 효능/영양 정보, 차별화된 특징, 구체적인 레시피, 보관법 등
    5.  **초안 작성 및 자기 비판 (Self-Correction & Refinement)**: 2, 3단계를 바탕으로 거친 초안을 작성한 뒤, '장동민'의 까다로운 시선으로 초안을 냉정하게 비판하고 개선합니다. 
    아래 기준을 모두 통과해야만 최종안을 제출할 수 있습니다.
        - **[문맥 적합성]**: 상품 유형에 어울리는 표현을 사용했는가?
        - **[실용 정보의 구체성]**: 효능/영양 정보는 신뢰할 만한가? 레시피나 보관법이 누구나 따라 할 수 있을 만큼 구체적이고 명확한가?
        - **[핵심 컨셉과의 일관성]**: 모든 결과물이 '핵심 컨셉'이라는 하나의 주제를 향하고 있는가?
        - **[스토리텔링의 깊이]**: 단순히 사실을 나열하지 않고, 다음 **5가지 요소**를 모두 활용하여 스토리를 구체적으로 엮어냈는가?
            1. **감각적 묘사**: '신선하다', '맛있다', '좋다'와 같은 추상적인 단어 사용을 금지합니다. 대신, 그 맛과 신선함이 느껴지는 **소리, 색감, 향기, 식감, 배경 풍경**을 구체적으로 묘사(오감을 자극하는 묘사)
            2. **주인공 등장**: 스토리의 주인공이 등장하게 되면 생성된 주인공이 아닌 정보를 입력한 사용자입니다. 사용자가 직접 경험하는 듯한 몰입감을 주기 위해, **생산자의 목소리로** 상품의 생산 과정과 지역 이야기를 전달
            3. **구체성 부여**: 신뢰도를 높이기 위해 스토리 속에 구체적인 숫자를 의미있게 활용하세요. 또한, 독자의 기억에 남을 만한 창의적인 비유를 최소 하나 이상 포함(신뢰를 주는 숫자나 창의적인 비유)
            4. **활용 제안**: 스토리의 마지막에, 상품을 가장 맛있게 즐길 수 있는 **구체적인 활용법이나 레시피**를 자연스럽게 제안했는가?
            5. **고객 가치 제시**: 스토리의 마지막은 반드시 **고객이 이 상품을 통해 얻게 될 특별한 경험이나 감정적 가치**를 제시하며 마무리하세요. '맛있습니다'가 아니라, **'당신의 저녁 식탁이 어떻게 변할 것인지', '누구에게 어떤 마음을 전할 수 있는지'** (소비자의 삶이 어떻게 특별해지는지 제안)
        - **[문법 및 표현]**: 문법 오류가 없는가? 어색한 표현은 없는가?
        - **[표현의 독창성]**: 슬로건, 키워드, 소개글의 표현이 진부하지 않고 날카로운가?

    ### [출력 형식 지침]
    {format_instructions}
    """
)


# --- Detail Page & Marketing Prompts ---

# 3. 상세페이지 텍스트 생성용 프롬프트 템플릿
SECTION_TEXT_DEFAULT_PROMPT = PromptTemplate.from_template(
    """
    다음 정보를 바탕으로, 쇼핑몰 상세페이지 이미지 섹션 #{section_number}에 삽입될 텍스트를 생성해줘.
    - 섹션 컨텍스트: {main_context} / 서브: {sub_context}
    - 최종 출력은 '메인 텍스트|서브 텍스트' 형식으로만 응답해줘.
    - 참고 정보: 브랜드 슬로건: {slogan}, 브랜드 스토리: {story}
    """
)

DETAIL_PAGE_SECTION_CONTEXTS = [
    {"main": "상품명과 지역명을 활용한 강렬한 헤드라인", "sub": "브랜드 슬로건"},
    {"main": "브랜드 스토리 또는 판매자 철학을 담은 한 문장", "sub": "생산 과정의 정성을 나타내는 문구"},
    {"main": "상품의 핵심 가치(맛, 영양)를 요약하는 문구", "sub": "과학적 사실이나 특징을 쉽게 표현"},
    {"main": "상품을 가장 맛있게 즐기는 방법을 제안하는 문구", "sub": "고객이 얻게 될 즐거운 경험 묘사"},
    {"main": "구매를 유도하거나 브랜드가 다시 한번 약속하는 문구", "sub": "브랜드 철학이나 마지막 인사"}
]


# 4. 마케팅 텍스트 생성용 프롬프트 템플릿
MARKETING_TEXT_PROMPT = PromptTemplate.from_template(
    """
    당신은 {platform} 마케팅 전문가입니다. 다음 브랜딩 정보를 활용하여 {platform}에 맞는 마케팅 게시물을 JSON 형식(title, text 필드 포함)으로 작성해주세요.
    브랜딩 정보: {branding_info}, 상품 정보: {product_info}
    """
)

# --- DALL-E Image Generation Prompts & Configs ---

# 5. DALL-E 이미지 생성을 위한 프레임 템플릿
DALLE_BASE_WITH_MARGINS = PromptTemplate.from_template(
    """
    ### 최종 이미지 구성 목표
    '1024x1792' 사이즈의 긴 흰색 캔버스 중앙에 '1024x1024' 사이즈의 정사각형 사진이 배치된 구성.

    ### [가장 중요한 지시사항]
    아래의 3단 구조를 반드시, 그리고 정확하게 따라야 합니다:
    1.  **상단 영역 (Top Section)**: 이미지의 상단 약 384px 높이는 어떤 요소도 없는, 완벽하고 순수한 흰색(#FFFFFF)이어야 합니다. 이 영역은 텍스트를 위한 깨끗한 공간입니다.
    2.  **중앙 이미지 영역 (Central Image Area - 1024x1024)**: 아래에 설명될 모든 시각적 콘텐츠는 반드시 이 중앙의 정사각형 영역 **안에만** 그려져야 합니다.
    3.  **하단 영역 (Bottom Section)**: 이미지의 하단 약 384px 높이 또한 어떤 요소도 없는, 완벽하고 순수한 흰색(#FFFFFF)이어야 합니다.

    ### [절대 규칙]
    사진의 어떤 부분(배경, 그림자, 흐림 효과 등)도 상단 또는 하단의 흰색 영역을 침범해서는 안 됩니다. 이 두 영역은 반드시 비어있는 순백의 상태로 유지되어야 합니다.
    ---
    ### 중앙 이미지 영역에 들어갈 내용
    {{theme}}

    ### 스타일
    Photorealistic, high-quality, professional product photography.
    """
)

DALLE_BASE_FULL_FRAME = PromptTemplate.from_template(
    """
    ### 최종 이미지 구성 목표
    '1024x1792' 사이즈의 세로 전체 화면을 사용하는 하나의 완성된 이미지.
    별도의 상하단 여백 없이, 이미지 전체가 조화롭게 구성되어야 합니다.
    
    ---
    ### 전체 이미지에 들어갈 내용
    {{theme}}
    
    ### 스타일
    Aesthetic, high-quality, professional graphic design.
    """
)

# True는 'WITH_MARGINS', False는 'FULL_FRAME'을 의미
DETAIL_PAGE_IMAGE_FRAMES = [
    DALLE_BASE_WITH_MARGINS,    # 1. 메인
    DALLE_BASE_WITH_MARGINS,    # 2. 스토리
    DALLE_BASE_FULL_FRAME,      # 3. 특징 (인포그래픽 스타일)
    DALLE_BASE_WITH_MARGINS,    # 4. 레시피
    DALLE_BASE_WITH_MARGINS,    # 5. 아웃트로
]

# format 메소드를 사용하기 위해 product_name, origin을 변수로 남겨둠
DETAIL_PAGE_IMAGE_THEMES = [
    # 1. 메인 타이틀 및 상품 강조
    "A visually stunning, professional photograph of ultra-fresh {product_name}. The {product_name} is the clear hero, glistening and appealing, placed centrally. The background subtly hints at the pristine natural environment of {origin}. The style is bright, clean, and uses natural lighting to convey freshness and quality. **The image must be purely visual and contain absolutely no text, letters, or words.**",
    # 2. 브랜드 스토리 및 생산 과정
    "A warm and authentic photo showing the **back of a Korean farmer**. The farmer is **holding the freshly harvested '{product_name}'** in their hands, **looking out over the beautiful fields** of '{origin}'. This image should convey a sense of pride, dedication, and a deep connection to the land, focusing on the harmony between the person and nature. **The image must be purely visual and contain absolutely no text, letters, or words.**",
    # 3. 상품의 특별한 가치 및 영양 정보
    "A clean, minimalist, infographic-style image. A beautiful close-up of the {product_name} is on one side, while the other side has abstract visual elements representing health and nutrition, like glowing particles or clean lines. The overall feel is modern, trustworthy, and informative. **The image must be purely visual and contain absolutely no text, letters, or words.**",
    # 4. 추천 레시피/활용법
    "A delicious-looking, appetizing photo of a dish made with {product_name}. The setting is a cozy kitchen or dining table. The image should evoke feelings of happiness, family, and the joy of cooking and eating good food. **The image must be purely visual and contain absolutely no text, letters, or words.**",
    # 5. 구매 유도 및 브랜드 철학
    "A beautiful, artistic shot of the packaged {product_name} or a final, perfect representation of the product. The background is clean and slightly abstract, focusing all attention on the product's premium quality. It could have a single, gentle light source, creating a sophisticated and trustworthy mood. **The image must be purely visual and contain absolutely no text, letters, or words.**"
]

GENERATE_PAGE_TEXTS_PROMPT = PromptTemplate.from_template(
    """
    당신은 농수산물 전문 콘텐츠 마케터입니다. 주어진 정보를 바탕으로, 아래 6가지 텍스트 콘텐츠를 JSON 형식으로 생성해주세요.

    ### 생성해야 할 콘텐츠 목록
    1.  `title`: "[지역명] [상품명]" 형식의 제목
    2.  `slogan`: 전체 브랜딩을 아우르는 슬로건
    3.  `region_story`: 지역의 특성과 상품을 자연스럽게 연결하는 1~2 문장의 스토리
    4.  `product_features`: 다른 상품과 차별화되는 상품의 우수성, 특징을 설명하는 1~2 문장
    5.  `nutrition_info`: 고객에게 매력적인 핵심 영양 정보 또는 건강상 이점 1~2 문장
    6.  `closing_statement`: 구매를 유도하거나 브랜드의 가치를 강조하는 마무리 문구

    ### 참고 정보
    - 사용자 입력 정보: {product_info}
    - 웹 검색 정보: {live_local_info}
    - 핵심 브랜딩 컨셉: {branding_info}

    ### 출력 형식 지침
    {format_instructions}
    """
)

DALLE_PRODUCT_IMAGE_PROMPT = PromptTemplate.from_template(
    """
    A hyper-realistic, minimalist photograph showcasing the **true form** of a single, perfect '{product_name}' 
    from '{origin}'.

    **[Very Important Instruction on Subject Representation]: Before drawing, you must consider the typical 
    appearance of a '{product_name}'. For example, grapes form a bunch (a cluster of berries), a strawberry has seeds on 
    the outside, an apple is a single round fruit. You must render the '{product_name}' in its most recognizable and 
    characteristic form with extreme accuracy.**

    The product must be the one and only subject, depicted with extreme detail, and positioned directly in the center of 
    the frame to allow for vertical cropping.
    It should be glistening with freshness, showcasing its perfect texture and vibrant color.
    The background should be a beautiful but soft and out-of-focus natural landscape of '{origin}', 
    ensuring it does not distract from the main subject.
    Crucial rule: The image must contain NO other objects, fruits, props, or elements.
    The image must be purely visual and contain absolutely no text, letters, or words.
    """
)

# 4. 마케팅 텍스트 생성용 프롬프트 템플릿
MARKETING_TEXT_PROMPT = PromptTemplate.from_template(
    """
    당신은 {platform} 마케팅 전문가입니다. 다음 브랜딩 정보를 활용하여 {platform}에 맞는 마케팅 게시물을 JSON 형식(title, text 필드 포함)으로 작성해주세요.
    브랜딩 정보: {branding_info}, 상품 정보: {product_info}
    """
)

# AI 인터뷰 질문 목록
STORY_INTERVIEW_QUESTIONS = [
    "가장 먼저, 이 상품을 만들게 된 특별한 계기나 동기가 있으신가요?",
    "다른 상품들과 비교했을 때, '이것만큼은 내가 최고다!'라고 자랑할 수 있는 점은 무엇인가요?",
    "상품을 만들 때 가장 중요하게 생각하고 지키는 원칙이 있다면 알려주세요.",
    "이 상품을 구매한 고객들이 어떤 경험을 했으면 좋겠다고 바라시나요?",
    "마지막으로, 상품에 얽힌 재미있는 에피소드나 숨겨진 이야기가 있다면 들려주세요."
]

# AI 인터뷰 답변을 바탕으로 스토리를 종합하는 프롬프트
STORY_GENERATION_FROM_INTERVIEW_PROMPT = PromptTemplate.from_template(
    """
    [페르소나(Persona)]
    당신은 지역 소상공인의 진심을 발견하여 소비자와 연결하는 '로컬 브랜딩 스토리텔러'입니다. 당신의 목표는 단순히 글을 쓰는 것이 아니라, 사장님의 투박한 답변 속에 숨겨진 땀과 철학, 그리고 지역의 특별한 가치를 발굴하여 한 편의 감동적인 이야기로 엮어내는 것입니다. 당신은 디지털 마케팅에 서툰 사장님의 든든한 파트너입니다.

    [궁극적인 목표(Ultimate Goal)]
    단순한 상품 소개를 넘어, 아래의 목표를 달성하는 스토리를 창조해야 합니다.
    1.  **신뢰 형성**: 소비자가 생산자(사장님)와 상품, 그리고 지역을 신뢰하게 만들어야 합니다.
    2.  **가치 증대**: 스토리를 통해 상품의 가격을 넘어선 '가치'를 느끼게 해야 합니다.
    3.  **구매 명분 제공**: 소비자가 이 상품을 구매하는 행위가 '단순 소비'를 넘어 '가치 있는 투자'이자 '지역 상생에의 동참'이라는 명분을 느끼게 해야 합니다.

    [입력 정보(Input Information)]
    - 아래는 디지털에 익숙하지 않은 소상공인 사장님과의 인터뷰 내용입니다. 답변이 짧고 투박할 수 있으니, 그 안에 담긴 진짜 의미와 맥락을 깊이 파악해야 합니다.
    ---
    {interview_summary}
    ---

    [스토리 구성 5원칙 (5 Principles of Story Composition)]
    당신은 아래 5가지 원칙을 반드시 순서대로, 그리고 깊이 있게 적용하여 스토리를 완성해야 합니다.

    **1. '사장님'을 주인공으로 만드세요 (Establish the Producer as the Hero):**
    - "저는", "제가"와 같이 사장님의 1인칭 시점으로 이야기를 시작하세요.
    - 인터뷰 답변에서 드러나는 사장님의 고집, 철학, 자부심을 스토리의 중심축으로 삼으세요.

    **2. '지역'을 특별한 무대로 만드세요 (Connect to the Locality):**
    - 상품이 왜 '바로 그 지역'에서만 특별한지를 명확히 설명해야 합니다.
    - 인터뷰 답변과 지역의 기후(해풍, 일조량), 토양, 물, 전통 방식 등을 자연스럽게 연결하세요.

    **3. '과정'을 통해 진정성을 보여주세요 (Show Authenticity Through Process):**
    - "어떻게 만드나요?" 라는 질문의 답변을 구체적으로 묘사하여 사장님의 땀과 정성을 보여주세요.
    - 추상적인 단어(예: '최고급', '신선한') 사용을 최소화하고, 구체적인 행동으로 풀어내세요.

    **4. '오감'을 자극하여 경험을 상상하게 하세요 (Engage the Senses):**
    - 소비자가 상품을 직접 맛보고, 만지고, 냄새 맡는 것처럼 느끼게 해야 합니다.
    - '맛있다' -> "입안에 넣는 순간 '아삭!' 하는 소리와 함께 터져 나오는 시원한 단맛"
    - '색이 좋다' -> "아침 햇살을 머금은 것처럼 맑고 선명한 붉은빛"
    - 와 같이 감각적인 묘사를 적극적으로 사용하세요.

    **5. '고객의 가치'를 제안하며 마무리하세요 (Propose Value and Justify Purchase):**
    - 이야기의 마지막은 "이 상품을 통해 고객의 삶이 어떻게 더 나아지는지"를 제시하며 끝내야 합니다.
    - 단순히 "맛있으니 사세요"가 아니라, "오늘 저녁, 저희가 정성껏 키운 이 채소 하나로 온 가족의 식탁이 얼마나 건강하고 풍성해질 수 있을까요?", "소중한 분에게 저희의 진심을 선물해보세요." 와 같이 고객이 얻게 될 경험적 가치를 약속하세요.
    - 더 나아가, 이 상품을 구매하는 것이 곧 땀 흘리는 지역 생산자를 응원하고, 우리 지역 경제에 활력을 불어넣는 의미 있는 행동임을 은은하게 암시하세요.

    [문체 및 톤앤매너 (Style and Tone & Manner)]
    - 진정성 있게, 따뜻하고 친근한 구어체를 사용해주세요.
    - 디지털에 익숙하지 않은 사장님이 직접 쓴 것처럼, 솔직하고 담백한 느낌을 주세요.
    - 문장은 간결하고 명확하게 작성하여 쉽게 읽히도록 해주세요.

    [최종 결과물 (Final Output)]
    - 위의 모든 원칙을 종합하여, 다른 설명 없이 최종적으로 완성된 상품 스토리 본문만 깔끔하게 작성해주세요.
    """
)

INSTAGRAM_POST_PROMPT = PromptTemplate.from_template(
    """
    ## [Mission]
    You are a top-tier Instagram content marketing expert for local food brands.
    Your mission is to create one highly effective Instagram post (image prompt, post text, and hashtags).

    ## [Core Information]
    1.  **Product Information**: {product_info}
    2.  **Branding Concept**: {branding_info}

    ## [Strategic Framework: AIDA Model for a Single Post]
    You must structure the `post_text` to follow the AIDA model to maximize persuasion:
    - **Attention (Hook):** Start with a compelling question or a surprising fact that grabs the audience's attention immediately.
    - **Interest (Body):** Build interest by weaving in the producer's story, unique features of the product, or its health benefits. Keep sentences short and use emojis to improve readability.
    - **Desire (Value Proposition):** Create desire by explaining how this product can enrich the customer's life (e.g., a healthier family dinner, a moment of true flavor).
    - **Action (Call-to-Action):** End with a clear and friendly Call-to-Action. Examples: "지금 프로필 링크를 확인하세요!", "저장하고 주말에 만들어보세요!", "댓글로 친구를 태그해 이 소식을 알려주세요!"

    ## [Content Generation Rules]
    1.  **Image Prompt:** Create a detailed DALL-E prompt for a single, high-quality, visually stunning image that matches the post's content. It should be in a 1:1 square format, suitable for Instagram.
    2.  **Post Text:** Write the full post copy. It should be engaging, easy to read, and directly speak to the target audience.
    3.  **Hashtags:** Generate a list of 10-15 relevant hashtags. Include a mix of popular tags (e.g., #요리스타그램), niche tags (e.g., #해남배추김치), and brand-specific tags (e.g., #{{product_name}}농장).

    ## [Output Format Instructions]
    You MUST output a JSON object that strictly conforms to the `InstagramPost` Pydantic schema:
    {format_instructions}
    """
)

NAVER_BLOG_PROMPT = PromptTemplate.from_template(
    """
    ## [Mission]
    You are a professional content marketer who creates highly informative and SEO-optimized blog posts for the Naver platform. Your mission is to write a detailed, engaging informational blog post from an expert's perspective, as if you were the brand owner.

    ## [Core Information]
    1.  **Product Information**: {product_info}
    2.  **Branding Concept**: {branding_info}

    ## [Strategic Framework: SEO & Readability]
    - **Title:** Must include the core product name and an appealing, informative modifier. (e.g., "해남 배추, 왜 특별할까요? 과학적으로 알아본 아삭함의 비밀")
    - **Body:** Must be structured with `<h2>` for subheadings and `<li>` for lists to improve readability. Weave the brand story naturally into the post as evidence of expertise. Use `<strong>` to emphasize key benefits and facts. The tone should be trustworthy and expert-like.
    - **Conclusion:** Must summarize the key information and include a clear call-to-action (e.g., "더 자세한 정보는 스토어에서 확인하세요").

    ## [Content Generation Rules]
    1.  **Title:** Create a title that sparks curiosity and suggests valuable information.
    2.  **Introduction:** Hook the reader by stating a common question or problem that the post will solve.
    3.  **Body:** Explain the product's value based on facts (e.g., regional characteristics, nutritional benefits, special farming methods). The brand story should be used as proof of the seller's expertise and dedication.
    4.  **Conclusion:** Briefly recap the main points and guide the reader to the next step.
    5.  **Tags:** Generate a list of 5-7 relevant hashtags that users are likely to search for.

    ## [Output Format Instructions]
    You MUST output a JSON object that strictly conforms to the `NaverBlogPost` Pydantic schema:
    {format_instructions}
    """
)

REGENERATE_SLOGAN_PROMPT = PromptTemplate.from_template(
    """
    당신은 아주 창의적인 카피라이터입니다.
    아래의 '핵심 컨셉'을 바탕으로, '기존 슬로건'과는 다른 느낌의 새로운 슬로건 3개를 제안해주세요.
    각 슬로건은 짧고, 기억하기 쉬우며, 강력한 메시지를 담고 있어야 합니다.

    - 핵심 컨셉: {core_concept}
    - 기존 슬로건: {original_slogan}

    {format_instructions}
    """
)

