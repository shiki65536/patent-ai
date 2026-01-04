"""
Smart file matching for patent corpus
"""
import re
from pathlib import Path
from typing import Optional, List, Tuple
import logging

logger = logging.getLogger(__name__)

class FileNameMatcher:
    """Match Japanese and Chinese patent files"""
    
    @staticmethod
    def extract_patent_id(filename: str) -> Optional[str]:
        """
        Extract patent ID from filename
        
        Examples:
            P14770(JP).doc -> P14770
            P10517(JP).docx -> P10517
            P10555(SCW+KVN+GT)Final.docx -> P10555
        """
        # Pattern: P + digits
        match = re.search(r'(P\d+)', filename)
        if match:
            return match.group(1)
        
        # Fallback: just digits
        match = re.search(r'(\d{4,})', filename)
        if match:
            return match.group(1)
        
        return None
    
    @staticmethod
    def is_japanese_file(filename: str) -> bool:
        """Check if file is Japanese version"""
        return bool(re.search(r'\(JP\)', filename, re.IGNORECASE))
    
    @staticmethod
    def is_chinese_file(filename: str) -> bool:
        """Check if file is Chinese version"""
        patterns = [
            r'\(SCW[^)]*\)',  # (SCW), (SCW+KVN), etc.
            r'\(ZH\)',
            r'_zh\.',
            r'_ZH\.',
        ]
        return any(re.search(p, filename, re.IGNORECASE) for p in patterns)
    
    @staticmethod
    def find_chinese_match(
        jp_file: Path,
        zh_directory: Path
    ) -> Optional[Path]:
        """
        Find matching Chinese file for Japanese file
        
        Args:
            jp_file: Japanese file path
            zh_directory: Directory containing Chinese files
            
        Returns:
            Path to matching Chinese file or None
        """
        # Extract patent ID from Japanese file
        patent_id = FileNameMatcher.extract_patent_id(jp_file.name)
        
        if not patent_id:
            logger.warning(f"Cannot extract patent ID from: {jp_file.name}")
            return None
        
        logger.debug(f"Looking for Chinese file with ID: {patent_id}")
        
        # Get all files in Chinese directory
        zh_files = list(zh_directory.glob("*"))
        
        # Find files with matching patent ID
        candidates = []
        for zh_file in zh_files:
            if zh_file.suffix.lower() not in ['.doc', '.docx', '.pdf']:
                continue
            
            zh_patent_id = FileNameMatcher.extract_patent_id(zh_file.name)
            
            if zh_patent_id == patent_id:
                # Check if it's a Chinese file
                if FileNameMatcher.is_chinese_file(zh_file.name):
                    candidates.append(zh_file)
        
        if not candidates:
            logger.warning(f"No Chinese file found for: {jp_file.name} (ID: {patent_id})")
            return None
        
        if len(candidates) == 1:
            logger.debug(f"Matched: {jp_file.name} -> {candidates[0].name}")
            return candidates[0]
        
        # Multiple candidates - prefer Final version
        for candidate in candidates:
            if 'final' in candidate.name.lower():
                logger.debug(f"Matched (Final): {jp_file.name} -> {candidate.name}")
                return candidate
        
        # Otherwise, return first
        logger.warning(f"Multiple matches for {jp_file.name}, using: {candidates[0].name}")
        return candidates[0]
    
    @staticmethod
    def find_all_pairs(
        jp_directory: Path,
        zh_directory: Path
    ) -> List[Tuple[Path, Path]]:
        """
        Find all matching Japanese-Chinese file pairs
        
        Returns:
            List of (japanese_file, chinese_file) tuples
        """
        pairs = []
        
        # Get all Japanese files
        jp_files = [
            f for f in jp_directory.glob("*")
            if f.suffix.lower() in ['.doc', '.docx', '.pdf']
            and FileNameMatcher.is_japanese_file(f.name)
        ]
        
        logger.info(f"Found {len(jp_files)} Japanese files")
        
        for jp_file in jp_files:
            zh_file = FileNameMatcher.find_chinese_match(jp_file, zh_directory)
            if zh_file:
                pairs.append((jp_file, zh_file))
        
        logger.info(f"Matched {len(pairs)} file pairs")
        
        return pairs