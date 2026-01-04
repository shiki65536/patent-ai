# 📚 Patent AI Translation System (JP → ZH)

A **RAG-powered Japanese → Traditional Chinese patent translation system** built on Claude, optimized for technical accuracy, terminology consistency, and long-form legal documents.

This project explores whether **Claude + Retrieval-Augmented Generation (RAG)** can meaningfully improve real-world patent translation workflows.

---

## ✨ Key Features

- **RAG-based Translation**

  - Retrieves similar historical patent translations for contextual grounding
  - Uses semantic vector search instead of naive prompt stuffing

- **Terminology-Aware**

  - 11,000+ verified domain-specific terms (semiconductor, mechanical, general)
  - Terminology injected directly into prompts

- **Section-Aware Translation**

  - Title, abstract, claims, and descriptions translated independently
  - Better consistency and debuggability for long patents

- **Deterministic Output**

  - Temperature = 0 for reproducible, review-friendly translations

- **Batch & API Support**

  - Translate single PDFs or entire folders
  - FastAPI-based REST API for integration

- **Production Ready**

  - Dockerized
  - Deployed on Render
  - PostgreSQL (Supabase) + Chroma Vector DB

---

## 🏗️ System Architecture (High Level)

```
PDF / DOCX
   ↓
Document Parser (section-based)
   ↓
RAG Retrieval (Chroma + embeddings)
   ↓
Terminology Matching (Postgres)
   ↓
Prompt Construction
   ↓
Claude 4.5 Translation
   ↓
Formatted DOCX Output (+ metadata)
```

---

## 📊 Current System Stats

```
Historical Translations: 1,264 entries
Terminology Database:   11,112 terms
Vector Index Coverage:  99.7%
Domains:
  - Semiconductor: 17.7%
  - Mechanical:    22.7%
  - General:       42.9%
  - Unknown:       16.7%
```

---

## 🛠️ Tech Stack

| Layer      | Technology                    |
| ---------- | ----------------------------- |
| API        | FastAPI                       |
| LLM        | Claude Sonnet 4.5 (Anthropic) |
| Vector DB  | Chroma                        |
| Embeddings | sentence-transformers         |
| Database   | PostgreSQL (Supabase)         |
| Docs       | PyMuPDF, python-docx          |
| Deployment | Docker + Render               |

---

## 🚀 Quick Start (Local)

### 1. Clone & Setup

```bash
git clone https://github.com/yourusername/patent-ai.git
cd patent-ai

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Environment Variables

Create `.env`:

```bash
ANTHROPIC_API_KEY=your_api_key_here
DATABASE_URL=sqlite:///./patent_ai.db
SECRET_KEY=dev-secret
```

### 3. Initialize Database

```bash
python -c "from app.database import init_db; init_db()"
```

### 4. Run API Server

```bash
uvicorn app.main:app --reload
```

API docs available at:
`http://localhost:8000/docs`

---

## 📥 Import Data (Optional but Recommended)

### Import Terminology

```bash
python scripts/import_terminology_excel.py data/terminology.xlsx
```

### Import Historical Translations

```bash
python scripts/import_patent_corpus.py \
  data/corpus/japanese \
  data/corpus/chinese
```

### Build Vector Index

```bash
python scripts/build_vector_index.py
```

---

## 📄 Translate a Patent

### Single PDF

```bash
python scripts/translate_pdf.py input.pdf \
  --output result.docx \
  --domain semiconductor
```

### Batch Translation

```bash
python scripts/batch_translate.py \
  input_folder/ \
  output_folder/ \
  --domain semiconductor
```

---

## 📑 Output Format

Each translated section includes metadata:

- Confidence score
- Number of RAG examples used
- Matched terminology count

Example:

```
發明名稱
---------
基板處理裝置
[confidence: 0.95 | examples: 3 | terms: 5]
```

**Confidence guide**

- `0.9–1.0`: Excellent
- `0.7–0.9`: Good
- `0.5–0.7`: Review recommended
- `<0.5`: Manual translation advised

Quality checks:

```bash
python scripts/test_translation_quality.py
```

---

## 🌐 API Example

```bash
curl -X POST http://localhost:8000/api/v1/translate \
  -H "Content-Type: application/json" \
  -d '{
    "japanese_text": "半導体装置の製造方法",
    "domain": "semiconductor",
    "use_rag": true
  }'
```

---

## 🧠 Design Notes

This system is **not intended to replace human translators**, but to:

- Reduce cognitive load
- Improve terminology consistency
- Speed up first-pass drafts

---

## 📌 Status

- Actively used in real JP→ZH patent translation workflows
- Open to iteration and domain expansion

---

## 📬 Contactgia

Built by **Shiki Wen**
