from typing import Dict, List, Tuple

from anthropic import Anthropic
import google.generativeai as genai

from app.config import settings


class PatentTranslator:
    """AI-powered patent translation assistant with RAG and model routing."""

    def __init__(self):
        self.provider = settings.LLM_PROVIDER.lower()
        self.anthropic_client = None

        if settings.ANTHROPIC_API_KEY:
            self.anthropic_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)

    def translate(
        self,
        japanese_text: str,
        section_type: str = "general",
        domain: str = None,
        examples: List[Dict] = None,
        terminology: List[Dict] = None,
        provider: str | None = None,
    ) -> Tuple[str, float, Dict]:
        """Translate Japanese patent text to Traditional Chinese."""

        selected_provider = (provider or self.provider or "gemini").lower()
        examples_context = self._format_examples(examples) if examples else ""
        term_hints = self._format_terminology(terminology) if terminology else ""

        prompt = self._build_translation_prompt(
            japanese_text,
            section_type,
            domain,
            examples_context,
            term_hints,
        )

        if selected_provider == "claude":
            translation = self._translate_with_claude(prompt)
        else:
            selected_provider = "gemini"
            translation = self._translate_with_gemini(prompt)

        confidence = self._calculate_confidence(japanese_text, translation)
        estimated_cost = self.estimate_cost(selected_provider, prompt, translation)

        metadata = {
            "provider": selected_provider,
            "model": settings.CLAUDE_MODEL if selected_provider == "claude" else settings.GEMINI_MODEL,
            "estimated_cost_usd": estimated_cost,
            "input_chars": len(prompt),
            "output_chars": len(translation),
        }

        return translation, confidence, metadata

    def estimate_cost(self, provider: str, prompt: str, output: str) -> float:
        """Conservative token-cost estimate for UI guardrails."""
        input_tokens = max(len(prompt) / 4, 1)
        output_tokens = max(len(output) / 4, 1)

        if provider == "claude":
            return round((input_tokens / 1_000_000 * 3.0) + (output_tokens / 1_000_000 * 15.0), 6)

        # Gemini Flash-class estimate, intentionally conservative for demo display.
        return round((input_tokens / 1_000_000 * 0.075) + (output_tokens / 1_000_000 * 0.30), 6)

    def _translate_with_gemini(self, prompt: str) -> str:
        if not settings.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is required for Gemini translation")

        model = genai.GenerativeModel(settings.GEMINI_MODEL)
        response = model.generate_content(prompt)

        if not response.text:
            raise RuntimeError("Gemini returned an empty response")

        return response.text.strip()

    def _translate_with_claude(self, prompt: str) -> str:
        if settings.DISABLE_CLAUDE:
            raise RuntimeError("Claude is disabled for this demo")

        if not self.anthropic_client:
            raise RuntimeError("ANTHROPIC_API_KEY is required for Claude translation")

        response = self.anthropic_client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=4000,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.content[0].text.strip()

    def _build_translation_prompt(
        self,
        japanese_text: str,
        section_type: str,
        domain: str,
        examples: str,
        terminology: str,
    ) -> str:
        domain_str = f"技術領域：{domain}" if domain else ""

        return f"""你是專業的日文轉繁體中文專利翻譯員，專精半導體與機械領域。

    任務：
    你只能翻譯 <SOURCE_TEXT> 內的日文。
    <RAG_EXAMPLES> 只用來參考術語與風格，絕對不要翻譯、續寫、摘要或複製其中內容。

    翻譯要求：
    1. 使用台灣專利局慣用術語
    2. 保持專利文件的法律精確性
    3. 維持原文的句子結構和邏輯關係
    4. 技術術語必須一致且準確
    5. 只輸出 <SOURCE_TEXT> 的繁體中文譯文
    6. 不要輸出說明、標題、RAG 範例或額外段落

    {terminology}

    <RAG_EXAMPLES>
    {examples}
    </RAG_EXAMPLES>

    段落類型：{section_type}
    {domain_str}

    <SOURCE_TEXT>
    {japanese_text}
    </SOURCE_TEXT>

    繁體中文譯文："""

    def _format_examples(self, examples: List[Dict]) -> str:
        if not examples:
            return ""

        formatted = []

        for index, example in enumerate(examples, 1):
            source = (example.get("source_text") or "").strip()
            translation = (example.get("translation") or "").strip()

            if not source or not translation:
                continue

            source = source[:160].rstrip()
            translation = translation[:160].rstrip()

            formatted.append(
                f"範例 {index}：\n"
                f"JP snippet: {source}\n"
                f"ZH snippet: {translation}"
            )

        return "\n\n".join(formatted)

    def _format_terminology(self, terminology: List[Dict]) -> str:
        if not terminology:
            return ""

        formatted = ["重要術語對照表：\n"]

        for term in terminology:
            jp = term.get("japanese_term", "")
            zh = term.get("chinese_term", "")
            formatted.append(f"  • {jp} → {zh}")

        return "\n".join(formatted)

    def _calculate_confidence(self, source: str, translation: str) -> float:
        source_len = len(source)
        trans_len = len(translation)

        if source_len == 0:
            return 0.0

        ratio = trans_len / source_len

        if 0.6 <= ratio <= 1.4:
            return 0.9
        if 0.4 <= ratio <= 1.6:
            return 0.7
        return 0.5
