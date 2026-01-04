from anthropic import Anthropic
from typing import List, Tuple, Dict
from app.config import settings
import re
import json

class PatentTranslator:
    """AI-powered patent translation assistant with RAG"""
    
    def __init__(self):
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = settings.CLAUDE_MODEL
    
    def translate(
        self, 
        japanese_text: str, 
        section_type: str = "general",
        domain: str = None,
        examples: List[Dict] = None,
        terminology: List[Dict] = None
    ) -> Tuple[str, float]:
        """Translate Japanese patent text to Traditional Chinese"""
        
        # Build context from examples
        examples_context = self._format_examples(examples) if examples else ""
        
        # Build terminology hints
        term_hints = self._format_terminology(terminology) if terminology else ""
        
        # Build prompt
        prompt = self._build_translation_prompt(
            japanese_text,
            section_type,
            domain,
            examples_context,
            term_hints
        )
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                temperature=0,  # Deterministic for translation
                messages=[{"role": "user", "content": prompt}]
            )
            
            translation = response.content[0].text
            
            # Calculate confidence (simple heuristic)
            confidence = self._calculate_confidence(japanese_text, translation)
            
            return translation, confidence
            
        except Exception as e:
            raise Exception(f"Translation failed: {str(e)}")
    
    def _build_translation_prompt(
        self,
        japanese_text: str,
        section_type: str,
        domain: str,
        examples: str,
        terminology: str
    ) -> str:
        """Build comprehensive translation prompt"""
        
        domain_str = f"技術領域：{domain}" if domain else ""
        
        prompt = f"""你是專業的日文轉繁體中文專利翻譯員，專精半導體與機械領域。

翻譯要求：
1. 使用台灣專利局慣用術語
2. 保持專利文件的法律精確性
3. 維持原文的句子結構和邏輯關係
4. 專利請求項（claim）必須保持編號和從屬關係
5. 技術術語必須一致且準確

{terminology}

{examples}

---

請將以下日文專利內容翻譯成繁體中文：

段落類型：{section_type}
{domain_str}

日文原文：
{japanese_text}

繁體中文翻譯："""
        
        return prompt
    
    def _format_examples(self, examples: List[Dict]) -> str:
        """Format retrieved examples for prompt"""
        if not examples:
            return ""
        
        formatted = ["參考以下過去的翻譯範例（學習風格和用語）：\n"]
        
        for i, ex in enumerate(examples, 1):
            formatted.append(f"範例 {i}:")
            formatted.append(f"日文：{ex.get('source_text', '')[:200]}...")
            formatted.append(f"中文：{ex.get('translation', '')[:200]}...\n")
        
        return "\n".join(formatted)
    
    def _format_terminology(self, terminology: List[Dict]) -> str:
        """Format terminology for prompt"""
        if not terminology:
            return ""
        
        formatted = ["重要術語對照表：\n"]
        
        for term in terminology:
            jp = term.get('japanese_term', '')
            zh = term.get('chinese_term', '')
            formatted.append(f"  • {jp} → {zh}")
        
        return "\n".join(formatted)
    
    def _calculate_confidence(self, source: str, translation: str) -> float:
        """Calculate translation confidence score"""
        # Simple heuristic based on length ratio and completeness
        source_len = len(source)
        trans_len = len(translation)
        
        if source_len == 0:
            return 0.0
        
        # Expected ratio for JP->ZH is roughly 1:0.8 to 1:1.2
        ratio = trans_len / source_len
        
        if 0.6 <= ratio <= 1.4:
            confidence = 0.9
        elif 0.4 <= ratio <= 1.6:
            confidence = 0.7
        else:
            confidence = 0.5
        
        return confidence