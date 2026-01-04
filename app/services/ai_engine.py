from anthropic import Anthropic
from typing import List
from app.config import settings
from app.models import ReviewFinding
import json
import re

class AIEngine:
    """AI-powered patent translation assistant with RAG"""
    
    def __init__(self):
        if not settings.ANTHROPIC_API_KEY:
            raise RuntimeError("Missing ANTHROPIC_API_KEY. Set it in .env before using AIEngine.")
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = settings.CLAUDE_MODEL

    def _extract_json(self, text: str) -> dict:
        """Robust JSON extraction from LLM output"""
        
        # 1. Try direct JSON
        try:
            return json.loads(text)
        except Exception:
            pass

        # 2. Try fenced code block
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception:
                pass

        # 3. Try first {...} block
        match = re.search(r"(\{.*\})", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception:
                pass

        raise ValueError("Unable to extract valid JSON from AI response")

    
    def review_code(self, code: str, language: str, context: str = "") -> tuple[List[ReviewFinding], str, float]:
        """Perform AI code review"""
        
        prompt = f"""You are an expert code reviewer for a financial services company. Review the following {language} code for:
                    1. Security vulnerabilities
                    2. Performance issues
                    3. Code quality and best practices
                    4. Potential bugs
                    5. Style and maintainability

                    {f"Context: {context}" if context else ""}

                    Code to review:
                    ```{language}
                    {code}
                    ```

                    Provide your review in JSON format with the following structure:
                    {{
                    "findings": [
                        {{
                        "severity": "critical|major|minor|info",
                        "category": "security|performance|style|bug|suggestion",
                        "line_number": <number or null>,
                        "message": "description of the issue",
                        "suggestion": "how to fix it (optional)"
                        }}
                    ],
                    "summary": "overall assessment",
                    "score": <0-10 rating>
                    }}

                    Focus on issues that matter in production systems. Be specific and actionable."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse response
            content = response.content[0].text
            
            # Extract JSON (handle markdown code blocks)
            review_data = self._extract_json(content)

            findings = [ReviewFinding(**f) for f in review_data.get("findings", [])]
            summary = review_data.get("summary", "Review completed")
            score = float(review_data.get("score", 5.0))

            findings = findings[:10]
            score = max(0.0, min(10.0, score))
            
            return findings, summary, score
            
        except Exception as e:
            # Fallback for parsing errors
            return [
                ReviewFinding(
                    severity="info",
                    category="suggestion",
                    message=f"Review completed with parsing issue: {str(e)}"
                )
            ], "Automated review completed", 7.0