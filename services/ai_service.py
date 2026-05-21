import os
import uuid
import requests
import anthropic
from config import Config


# ── Claude API 클라이언트 (싱글턴) ────────────────────────
_claude_client = None

def get_claude_client():
    global _claude_client
    if _claude_client is None:
        _claude_client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)
    return _claude_client


# ── Step 1: 일기 → 이미지 프롬프트 변환 ──────────────────

PROMPT_EXTRACTION_SYSTEM = """
You are a creative assistant that converts diary entries into image generation prompts.

Rules:
1. Extract the core scene, emotions, and objects from the diary.
2. Output ONLY the image prompt — no explanation, no preamble.
3. The prompt must describe a children's crayon drawing style scene.
4. Keep it under 60 words.
5. Always append style keywords at the end.
6. Never include personal names or identifying information.

Style keywords to always append:
"children's crayon drawing, kindergarten art style, thick outlines, bright colors, naive art, simple shapes, white background"

Example:
Input: "오늘 친구랑 공원에서 놀았다. 강아지도 봤어. 아이스크림도 먹었고 진짜 행복했다."
Output: "two kids playing in a sunny park, fluffy dog running nearby, ice cream cones, big smiles, children's crayon drawing, kindergarten art style, thick outlines, bright colors, naive art, simple shapes, white background"
"""

def diary_to_image_prompt(diary_content: str) -> str:
    """
    일기 원문 → 이미지 생성 프롬프트 변환.
    
    ⚠️  프라이버시: diary_content 는 이 함수 안에서만 사용되고
        절대 DB에 저장되지 않습니다. 반환값(프롬프트)만 저장됩니다.
    """
    client = get_claude_client()

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=200,
        system=PROMPT_EXTRACTION_SYSTEM,
        messages=[
            {"role": "user", "content": diary_content}
        ]
    )

    prompt = message.content[0].text.strip()
    return prompt


# ── Step 2: 프롬프트 → 이미지 생성 (HuggingFace) ─────────

def generate_image_from_prompt(prompt: str) -> str:
    """
    HuggingFace Inference API로 이미지 생성.
    생성된 이미지를 로컬에 저장하고 경로를 반환합니다.
    """
    headers = {"Authorization": f"Bearer {Config.HF_API_KEY}"}
    payload = {
        "inputs": prompt,
        "parameters": {
            "negative_prompt": "realistic, photographic, detailed, adult, scary, dark",
            "num_inference_steps": 30,
            "guidance_scale": 7.5,
        }
    }

    response = requests.post(
        Config.hf_api_url(),
        headers=headers,
        json=payload,
        timeout=60
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"HuggingFace API error: {response.status_code} — {response.text[:200]}"
        )

    # 이미지 바이너리 저장
    os.makedirs(Config.IMAGE_SAVE_PATH, exist_ok=True)
    filename  = f"{uuid.uuid4()}.png"
    save_path = os.path.join(Config.IMAGE_SAVE_PATH, filename)

    with open(save_path, "wb") as f:
        f.write(response.content)

    # 웹에서 접근 가능한 경로 반환 (/static/images/generated/xxx.png)
    web_path = save_path.replace("./static", "/static", 1)
    return web_path


# ── 통합 파이프라인 ───────────────────────────────────────

def process_diary(diary_content: str) -> dict:
    """
    일기 원문을 받아 이미지 생성까지 한번에 처리.
    
    Returns:
        {
          "image_prompt": str,   # DB에 저장될 프롬프트
          "image_path":   str,   # 저장된 이미지 경로
        }
    
    ⚠️  diary_content 는 이 함수 scope 내에서만 존재하며
        반환값에 포함되지 않습니다.
    """
    image_prompt = diary_to_image_prompt(diary_content)
    image_path   = generate_image_from_prompt(image_prompt)

    # diary_content 는 여기서 소멸 — 로그에도 남기지 않음
    return {
        "image_prompt": image_prompt,
        "image_path":   image_path,
    }
