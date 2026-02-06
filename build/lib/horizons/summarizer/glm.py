from __future__ import annotations

import logging
from textwrap import dedent

import requests

from ..config import config

logger = logging.getLogger(__name__)

API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
DEFAULT_MODEL = "glm-4-plus"
SYSTEM_PROMPT = "你是一个中文资深科技记者，擅长从访谈中提炼洞察。"


def build_prompt(title: str, url: str, content: str) -> str:
    return dedent(
        f"""
        访谈标题：{title}
        原文链接：{url}

        原文内容：
        {content}

        请完成以下任务：
        1. 精炼总结访谈核心观点，包含3-5条关键洞察，每条带一句原文或事实依据。
        2. 概括受访者对行业趋势或产品策略的判断。
        3. 给出对读者的行动启发或思考题，2-3点。
        输出格式：Markdown，结构包括：
        - 标题（H1）
        - 原文信息（列表，含来源与链接）
        - 核心观点（编号列表）
        - 行业/策略判断（小节）
        - 行动启发（小节，项目符号）
        """
    ).strip()


class GLMSummarizer:
    def __init__(self, model: str = DEFAULT_MODEL) -> None:
        self.api_key = config.secrets.glm_api_key
        self.model = model

    def summarize(self, title: str, url: str, content: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_prompt(title, url, content)},
            ],
            "temperature": 0.3,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        logger.info("Calling GLM summarizer for %s", url)
        response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        try:
            content = data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            logger.error("Unexpected GLM response: %s", data)
            raise RuntimeError("Failed to parse GLM response") from exc
        return content
