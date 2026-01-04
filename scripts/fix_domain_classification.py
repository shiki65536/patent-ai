""""
Fix domain classification for existing translations
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.models import PatentTranslation
import re

def enhanced_detect_domain(text: str) -> str:
    """Enhanced domain detection with better keywords"""
    
    # Semiconductor keywords (more comprehensive)
    semiconductor_kw = [
        # Japanese
        "半導体", "半導體", "トランジスタ", "ウェハ", "ウエハ", "晶圓",
        "集積回路", "積體電路", "MOSFET", "ダイオード", "二極體",
        "チップ", "晶片", "回路", "電路", "プラズマ", "電漿",
        "薄膜", "成膜", "エッチング", "蝕刻", "リソグラフィ",
        "静電チャック", "靜電夾頭", "CVD", "PVD", "スパッタ",
        "イオン注入", "離子植入", "酸化膜", "氧化膜", "窒化膜",
        # Chinese
        "半導體裝置", "半導體基板", "半導體製程", "電晶體",
        "積體電路", "晶圓", "晶片", "薄膜", "蝕刻", "微影",
    ]
    
    # Mechanical keywords (more comprehensive)
    mechanical_kw = [
        # Japanese
        "機械", "機構", "装置", "裝置", "歯車", "齒輪",
        "軸受", "軸承", "ベアリング", "モータ", "馬達",
        "回転", "旋轉", "駆動", "驅動", "伝達", "傳動",
        "ボルト", "螺栓", "ナット", "螺帽", "バネ", "彈簧",
        "シャフト", "軸", "ピストン", "活塞", "シリンダ",
        "研磨", "研削", "切削", "加工", "工具",
        # Chinese
        "機械裝置", "傳動機構", "驅動裝置", "旋轉機構",
        "齒輪", "軸承", "馬達", "活塞", "彈簧", "螺栓",
    ]
    
    text_sample = text[:3000].lower()
    
    # Count matches
    semi_count = sum(1 for kw in semiconductor_kw if kw.lower() in text_sample)
    mech_count = sum(1 for kw in mechanical_kw if kw.lower() in text_sample)
    
    # Decision with threshold
    if semi_count >= 3 and semi_count > mech_count:
        return "semiconductor"
    elif mech_count >= 3 and mech_count > semi_count:
        return "mechanical"
    elif semi_count > 0 or mech_count > 0:
        return "general"
    
    return "unknown"

def main():
    print("=" * 80)
    print("Domain Classification Fix")
    print("=" * 80)
    
    db = SessionLocal()
    
    # Get all translations
    translations = db.query(PatentTranslation).all()
    
    print(f"\nProcessing {len(translations)} translations...")
    
    # Statistics
    changes = {
        'semiconductor': 0,
        'mechanical': 0,
        'general': 0,
        'unknown': 0
    }
    
    for trans in translations:
        old_domain = trans.domain
        
        # Detect new domain
        combined_text = f"{trans.source_text} {trans.translation}"
        new_domain = enhanced_detect_domain(combined_text)
        
        if new_domain != old_domain:
            trans.domain = new_domain
            changes[new_domain] += 1
    
    db.commit()
    
    print(f"\n✓ Updated domains:")
    print(f"  To semiconductor: {changes['semiconductor']}")
    print(f"  To mechanical:    {changes['mechanical']}")
    print(f"  To general:       {changes['general']}")
    print(f"  To unknown:       {changes['unknown']}")
    
    # Show new distribution
    from sqlalchemy import func
    new_dist = db.query(
        PatentTranslation.domain,
        func.count(PatentTranslation.id)
    ).group_by(PatentTranslation.domain).all()
    
    print(f"\nNew distribution:")
    total = sum(count for _, count in new_dist)
    for domain, count in new_dist:
        pct = count/total*100
        print(f"  {domain:15s}: {count:4d} ({pct:5.1f}%)")
    
    db.close()

if __name__ == "__main__":
    main()
