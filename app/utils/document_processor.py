"""
Production-grade patent corpus importer helpers (FINAL FIXED).

Fixes vs your broken run:
- Removes inline (?m) flags inside patterns that are later embedded/combined (this caused:
  "global flags not at the start of the expression").
- Keeps the "high section count" behavior (para alignment early-return).
- Adds claims block extraction safely (no regex flag errors), without reducing imported sections.
- Does NOT assume paragraphs stop at 0040; will capture 0001..0199.. or higher as long as markers exist.

Key design:
1) parse_sections():
   - normalize + remove front matter
   - split numbered paragraphs into para_XXXX (this is what drives high imports)
   - parse header sections (title/abstract/etc)
   - extract claims block (optional, stored as "claims" text)
2) align_sections():
   - prefer para alignment; if any para matched, return those (same as your "good" version)
   - otherwise fallback to header mapping
3) extract_claims():
   - splits claim text into individual claims (works for JP and ZH examples)
"""

import logging
import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import docx
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Extract text from patent documents with robust error handling."""

    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

    def extract_text(self, file_path: str) -> Optional[str]:
        path = Path(file_path)

        try:
            if not path.exists():
                logger.warning(f"File not found: {file_path}")
                return None

            if path.stat().st_size > self.MAX_FILE_SIZE:
                logger.warning(f"File too large: {path.name} ({path.stat().st_size} bytes)")
                return None

            ext = path.suffix.lower()

            if ext == ".docx":
                return self._extract_docx(path)
            if ext == ".pdf":
                return self._extract_pdf(path)
            if ext == ".doc":
                logger.warning(f"DOC format not supported: {path.name}")
                return None

            logger.warning(f"Unsupported format: {ext} ({path.name})")
            return None

        except Exception as e:
            logger.error(f"Error extracting from {path.name}: {e}")
            return None

    def _extract_docx(self, path: Path) -> str:
        doc = docx.Document(path)
        paragraphs = [p.text for p in doc.paragraphs if p.text and p.text.strip()]
        return "\n".join(paragraphs)

    def _extract_pdf(self, path: Path) -> Optional[str]:
        """
        Extract text from PDF with OCR detection.
        Returns None if PDF appears image-based (no extractable text).
        """
        try:
            doc = fitz.open(path)
            text_parts: List[str] = []
            total_chars = 0

            for page_num, page in enumerate(doc):
                page_text = page.get_text() or ""
                text_parts.append(page_text)
                total_chars += len(page_text.strip())

                # If first 3 pages have almost no text, likely OCR needed
                if page_num == 2 and total_chars < 100:
                    logger.warning(f"PDF appears to be image-based (no OCR): {path.name}")
                    doc.close()
                    return None

            doc.close()

            full_text = "\n".join(text_parts)
            if len(full_text.strip()) < 500:
                logger.warning(f"PDF has insufficient text ({len(full_text)} chars): {path.name}")
                return None

            return full_text

        except Exception as e:
            logger.error(f"PDF extraction failed for {path.name}: {e}")
            return None

    def clean_text(self, text: str) -> str:
        """Light cleaning; parser does the structure work."""
        if not text:
            return ""

        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"\n\s*\d+\s*/\s*\d+\s*\n", "\n", text)
        text = re.sub(r"\n\s*\d+\s*\n", "\n", text)
        text = re.sub(r"[ \t]{2,}", " ", text)

        return text.strip()


class PatentSectionParser:
    """
    Production-grade patent section parser for your corpus.

    High-import strategy:
    - Split numbered paragraphs: para_0001, para_0002, ...
      (This is what gave you 300+ imported entries.)
    - Align by para keys first; if any para alignment exists, return only para-aligned pairs
      (matches your "good" version behavior).

    Claims:
    - Extract claims block into sections["claims"] if found
    - extract_claims() can be called by importer to split into individual claims
    """

    def __init__(self, debug: bool = False):
        self.debug = debug

    # ---------- Public API ----------

    def parse_sections(self, text: str, language: str) -> Dict[str, str]:
        if not text:
            return {}

        t = self._normalize(text)
        t = self._remove_front_matter(t, language)

        if self.debug:
            print("=== PARSER INPUT HEAD ===")
            print(t[:300])

        sections: Dict[str, str] = {}

        # Keep safe fallback (optional)
        if len(t.strip()) > 200:
            sections["full_text"] = t.strip()

        # 1) Numbered paragraph chunks (main driver of high imports)
        sections.update(self._split_numbered_paragraphs(t))

        # 2) Header-based sections
        if language == "japanese":
            sections.update(self._parse_jp(t))
        else:
            sections.update(self._parse_zh(t))

        # 3) Claims block (do NOT break high imports; do NOT rely on inline flags)
        claims_block = self._extract_claims_block(t, language)
        if claims_block and len(claims_block) > 200:
            sections["claims"] = claims_block

        return sections

    def align_sections(
        self,
        jp_sections: Dict[str, str],
        zh_sections: Dict[str, str],
    ) -> List[Tuple[str, str, str]]:
        aligned: List[Tuple[str, str, str]] = []

        # 1) Prefer paragraph alignment (same as your "good" version)
        jp_para_keys = sorted(k for k in jp_sections.keys() if k.startswith("para_"))
        for k in jp_para_keys:
            if k in zh_sections:
                aligned.append((k, jp_sections[k], zh_sections[k]))

        if aligned:
            return aligned

        # 2) Fallback: header mapping
        mapping = {
            "title": "title",
            "abstract": "abstract",
            "technical_field": "technical_field",
            "background": "prior_art",
            "prior_art": "prior_art",
            "summary": "summary",
            "problem": "problem",
            "solution": "solution",
            "effects": "effects",
            "description": "description",
            "examples": "examples",
            "claims": "claims",
            "full_text": "full_text",
        }

        for jp_key, zh_key in mapping.items():
            if jp_key in jp_sections and zh_key in zh_sections:
                aligned.append((jp_key, jp_sections[jp_key], zh_sections[zh_key]))

        return aligned

    def extract_claims(self, claims_text: str) -> List[Dict]:
        """
        Extract individual claims from a claims section.

        IMPORTANT: No inline (?m) here. We pass re.MULTILINE via flags.
        """
        if not claims_text:
            return []

        claim_markers = [
            r"【\s*請求項\s*(\d{1,4})\s*】",
            r"請求項\s*(\d{1,4})",
            r"【\s*項次\s*(\d{1,4})\s*】",
            r"^\s*(\d{1,4})\s*[.．、]\s+",
        ]
        combined = "|".join(f"(?:{p})" for p in claim_markers)

        parts = re.split(combined, claims_text, flags=re.MULTILINE)
        claims: List[Dict] = []

        current_no: Optional[str] = None
        buf: List[str] = []

        for p in parts:
            if not p:
                continue
            s = p.strip()
            if not s:
                continue

            if s.isdigit():
                if current_no is not None and buf:
                    claims.append({"number": current_no, "text": "\n".join(buf).strip()})
                current_no = s
                buf = []
            else:
                buf.append(s)

        if current_no is not None and buf:
            claims.append({"number": current_no, "text": "\n".join(buf).strip()})

        return claims

    # ---------- Header-based parsing ----------

    def _parse_jp(self, t: str) -> Dict[str, str]:
        sections: Dict[str, str] = {}

        m = re.search(r"【発明の名称】\s*(.+)", t)
        if m:
            title = m.group(1).strip()
            if len(title) > 1:
                sections["title"] = title

        # Abstract near end, sometimes after claims
        abs_text = self._slice_by_markers(
            t,
            start_markers=[
                r"【書類名】\s*要約書",
                r"【要約】",
            ],
            end_markers=[
                r"【書類名】\s*特許請求の範囲",
                r"【特許請求の範囲】",
                r"【請求項",
                r"【書類名】\s*図面",
                r"【図面の簡単な説明】",
                r"【符号の説明】",
            ],
            include_start=False,
        )
        if abs_text and len(abs_text) > 80:
            abs_text = re.sub(r"^.*【要約】\s*", "", abs_text, flags=re.DOTALL).strip()
            if len(abs_text) > 80:
                sections["abstract"] = abs_text

        jp_defs = [
            ("technical_field", r"【技術分野】"),
            ("background", r"【背景技術】"),
            ("prior_art", r"【先行技術文献】"),
            ("summary", r"【発明の概要】"),
            ("problem", r"【発明が解決しようとする課題】"),
            ("solution", r"【課題を解決するための手段】"),
            ("effects", r"【発明の効果】"),
            ("description", r"【発明を実施するための形態】"),
            ("examples", r"【実施例】"),
            ("claims", r"【書類名】\s*特許請求の範囲|【特許請求の範囲】"),
        ]

        for i, (name, start_pat) in enumerate(jp_defs):
            start = re.search(start_pat, t)
            if not start:
                continue
            start_idx = start.end()

            end_idx = len(t)
            for _, next_pat in jp_defs[i + 1:]:
                nxt = re.search(next_pat, t[start_idx:])
                if nxt:
                    end_idx = start_idx + nxt.start()
                    break

            content = t[start_idx:end_idx].strip()
            content = self._strip_leading_numbering(content)
            if len(content) > 80:
                sections[name] = content

        return sections

    def _parse_zh(self, t: str) -> Dict[str, str]:
        sections: Dict[str, str] = {}

        m = re.search(r"【中文發明名稱】\s*(.+)", t)
        if m:
            title = m.group(1).strip()
            if len(title) > 1:
                sections["title"] = title

        abstract = self._slice_by_markers(
            t,
            start_markers=[r"【中文】"],
            end_markers=[
                r"【技術領域】",
                r"【發明所屬之技術領域】",
                r"【先前技術】",
                r"【發明內容】",
                r"【申請專利範圍】",
                r"【發明申請專利範圍】",
                r"【發明說明書】",
            ],
            include_start=False,
        )
        if abstract and len(abstract.strip()) > 80:
            sections["abstract"] = abstract.strip()

        zh_defs = [
            ("technical_field", r"【技術領域】|【發明所屬之技術領域】"),
            ("prior_art", r"【先前技術】"),
            ("summary", r"【發明內容】"),
            ("problem", r"【發明欲解決之問題】"),
            ("solution", r"【解決問題之技術手段】"),
            ("effects", r"【發明之功效】"),
            ("description", r"【實施方式】"),
            ("examples", r"【實施例】"),
            ("claims", r"【\s*(?:發明)?申請專利範圍\s*】|【\s*申請專利範圍\s*】"),
        ]

        for i, (name, start_pat) in enumerate(zh_defs):
            start = re.search(start_pat, t)
            if not start:
                continue
            start_idx = start.end()

            end_idx = len(t)
            for _, next_pat in zh_defs[i + 1:]:
                nxt = re.search(next_pat, t[start_idx:])
                if nxt:
                    end_idx = start_idx + nxt.start()
                    break

            content = t[start_idx:end_idx].strip()
            content = self._strip_leading_numbering(content)
            if len(content) > 80:
                sections[name] = content

        return sections

    # ---------- Paragraph chunking (THIS is what you care about) ----------

    def _split_numbered_paragraphs(self, t: str) -> Dict[str, str]:
        """
        Split by paragraph markers (no max):
        - 【０００１】 -> after NFKC becomes 【0001】
        - 【0001】
        - [0001]

        This will capture up to 【0199】 etc as long as markers exist.
        """
        marker_pat = r"(?:【\s*0*([0-9]{1,4})\s*】|\[\s*0*([0-9]{1,4})\s*\])"
        matches = list(re.finditer(marker_pat, t))
        if not matches:
            return {}

        chunks: Dict[str, str] = {}
        for i, m in enumerate(matches):
            n1 = m.group(1)
            n2 = m.group(2)
            num_raw = n1 or n2 or ""
            if not num_raw:
                continue

            num = num_raw.zfill(4)
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(t)
            body = t[start:end].strip()

            # Drop tiny noise
            if len(body) < 50:
                continue

            # Keep a reasonable cap per para (avoid huge embeddings)
            if len(body) > 8000:
                body = body[:8000]

            chunks[f"para_{num}"] = body

        return chunks

    # ---------- Claims block extraction (safe; no inline flags) ----------

    def _extract_claims_block(self, t: str, language: str) -> Optional[str]:
        """
        Extract claims block without inline (?m).
        Uses re.MULTILINE via flags, so it never triggers the "global flags not at start" error.
        """
        if language == "japanese":
            start_pats = [
                r"^\s*【書類名】\s*特許請求の範囲\s*$",
                r"^\s*【特許請求の範囲】\s*$",
                r"^\s*特許請求の範囲\s*$",
            ]
            # End near drawings / abstract (claims can appear before drawings)
            end_pats = [
                r"^\s*【書類名】\s*図面\s*$",
                r"^\s*【図面の簡単な説明】\s*$",
                r"^\s*【符号の説明】\s*$",
                r"^\s*【書類名】\s*要約書\s*$",
                r"^\s*【要約】\s*$",
            ]
        else:
            start_pats = [
                r"^\s*【發明申請專利範圍】\s*$",
                r"^\s*【申請專利範圍】\s*$",
                r"^\s*(?:發明)?申請專利範圍\s*$",
            ]
            end_pats = [
                r"^\s*【發明圖式】\s*$",
                r"^\s*【圖式簡單說明】\s*$",
                r"^\s*【符號說明】\s*$",
                r"^\s*【主要元件符號說明】\s*$",
            ]

        start_idx = self._find_first_multiline(t, start_pats)
        if start_idx is None:
            return None

        # Slice from start header to end marker (or EOF)
        tail = t[start_idx:]
        end_rel = self._find_first_multiline(tail, end_pats)
        end_idx = start_idx + end_rel if end_rel is not None else len(t)

        block = t[start_idx:end_idx].strip()

        # Must contain claim items
        if not re.search(r"^\s*【\s*請求項\s*\d{1,4}\s*】", block, flags=re.MULTILINE):
            # Some docs may omit the header but have claim items; try fallback:
            item_idx = self._find_first_multiline(t, [r"^\s*【\s*請求項\s*\d{1,4}\s*】"])
            if item_idx is None:
                return None
            tail2 = t[item_idx:]
            end_rel2 = self._find_first_multiline(tail2, end_pats)
            end_idx2 = item_idx + end_rel2 if end_rel2 is not None else len(t)
            block = t[item_idx:end_idx2].strip()

        # Strip headings to keep only claim items onwards
        # (optional, but keeps the block clean)
        lines = []
        for ln in block.splitlines():
            s = ln.strip()
            if not s:
                continue
            if language == "japanese" and re.match(r"^【書類名】\s*特許請求の範囲$", s):
                continue
            if language == "japanese" and re.match(r"^【特許請求の範囲】$", s):
                continue
            if language != "japanese" and re.match(r"^【(發明申請專利範圍|申請專利範圍)】$", s):
                continue
            lines.append(ln)

        cleaned = "\n".join(lines).strip()
        return cleaned if len(cleaned) > 200 else None

    def _find_first_multiline(self, text: str, patterns: List[str]) -> Optional[int]:
        best: Optional[int] = None
        for p in patterns:
            m = re.search(p, text, flags=re.MULTILINE)
            if m:
                if best is None or m.start() < best:
                    best = m.start()
        return best

    # ---------- Text helpers ----------

    def _normalize(self, text: str) -> str:
        text = unicodedata.normalize("NFKC", text)
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text

    def _remove_front_matter(self, text: str, language: str) -> str:
        # Include paragraph marker anchors too (covers docs starting with [0001])
        if language == "japanese":
            anchor = r"【発明の名称】|【技術分野】|【書類名】\s*明細書|【特許請求の範囲】|【書類名】\s*特許請求の範囲|\[\s*0*0001\s*\]|【\s*0*0001\s*】"
        else:
            anchor = r"【中文發明名稱】|【中文】|【技術領域】|【先前技術】|【發明內容】|【發明摘要】|【發明說明書】|【\s*(?:發明)?申請專利範圍\s*】|\[\s*0*0001\s*\]|【\s*0*0001\s*】"

        m = re.search(anchor, text)
        if m:
            return text[m.start():].strip()
        return text.strip()

    def _slice_by_markers(
        self,
        text: str,
        start_markers: List[str],
        end_markers: List[str],
        include_start: bool,
    ) -> Optional[str]:
        start_idx: Optional[int] = None
        for sm in start_markers:
            m = re.search(sm, text)
            if m:
                start_idx = m.start() if include_start else m.end()
                break
        if start_idx is None:
            return None

        end_idx = len(text)
        for em in end_markers:
            m2 = re.search(em, text[start_idx:])
            if m2:
                end_idx = start_idx + m2.start()
                break

        out = text[start_idx:end_idx].strip()
        return out if out else None

    def _strip_leading_numbering(self, s: str) -> str:
        s = re.sub(r"^\s*(【\s*\d+\s*】|\[\s*\d+\s*\])\s*", "", s)
        return s.strip()
