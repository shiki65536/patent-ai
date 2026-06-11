import os
import json
import requests
import streamlit as st


DEFAULT_API_BASE = os.getenv("PATENT_AI_API_BASE", "http://127.0.0.1:8000/api/v1")
DEFAULT_API_KEY = os.getenv("PATENT_AI_API_KEY", "")


st.set_page_config(
    page_title="Patent AI Demo",
    page_icon="🧠",
    layout="wide",
)


def get_headers(api_key: str) -> dict:
    headers = {"Content-Type": "application/json"}
    if api_key.strip():
        headers["x-api-key"] = api_key.strip()
    return headers


def safe_json(response: requests.Response):
    try:
        return response.json()
    except Exception:
        return {"raw_text": response.text}


def call_health(api_base: str):
    url = f"{api_base}/health"
    return requests.get(url, timeout=15)


def call_system_status(api_base: str):
    url = f"{api_base}/system/status"
    return requests.get(url, timeout=30)


def call_translate(api_base: str, api_key: str, payload: dict):
    url = f"{api_base}/translate"
    return requests.post(url, headers=get_headers(api_key), json=payload, timeout=180)


def call_test_rag(api_base: str, api_key: str, payload: dict):
    url = f"{api_base}/translate/test-rag"
    return requests.post(url, headers=get_headers(api_key), json=payload, timeout=120)


def render_example_card(example: dict, idx: int):
    similarity = example.get("similarity_score")
    score_text = f"{similarity:.3f}" if isinstance(similarity, (int, float)) else "N/A"

    with st.container(border=True):
        st.markdown(f"**Example {idx}**")
        st.write(f"Similarity: {score_text}")
        st.write(f"Section: {example.get('section_type', 'N/A')}")
        st.write(f"Domain: {example.get('domain', 'N/A')}")

        source_text = example.get("source_text", "")
        translation = example.get("translation", "")

        col1, col2 = st.columns(2)
        with col1:
            st.caption("Japanese")
            st.text_area(
                f"jp_example_{idx}",
                value=source_text,
                height=160,
                disabled=True,
                label_visibility="collapsed",
            )
        with col2:
            st.caption("Chinese")
            st.text_area(
                f"zh_example_{idx}",
                value=translation,
                height=160,
                disabled=True,
                label_visibility="collapsed",
            )


def render_term_table(terms: list[dict]):
    if not terms:
        st.info("No terminology matched.")
        return

    rows = []
    for term in terms:
        rows.append({
            "Japanese": term.get("japanese_term", ""),
            "Chinese": term.get("chinese_term", ""),
            "Domain": term.get("domain", ""),
        })

    st.dataframe(rows, use_container_width=True, hide_index=True)


st.title("🧠 Patent AI Translation Demo")
st.caption("RAG-powered Japanese → Traditional Chinese patent translation showcase")

with st.sidebar:
    st.header("Configuration")

    api_base = st.text_input(
        "Backend API Base URL",
        value=DEFAULT_API_BASE,
        help="Example: http://127.0.0.1:8000/api/v1 or your Render URL",
    )

    api_key = st.text_input(
        "API Key (optional)",
        value=DEFAULT_API_KEY,
        type="password",
        help="If your backend has API_SECRET enabled, put the same key here.",
    )

    st.divider()

    st.subheader("Request Options")

    domain = st.selectbox(
        "Domain",
        options=["", "semiconductor", "mechanical", "general"],
        index=1,
    )

    section_type = st.selectbox(
        "Section Type",
        options=[
            "general",
            "title",
            "abstract",
            "technical_field",
            "background",
            "prior_art",
            "summary",
            "problem",
            "solution",
            "effects",
            "description",
            "examples",
            "claims",
        ],
        index=0,
    )

    use_rag = st.checkbox("Use RAG", value=True)
    num_examples = st.slider("Number of examples", min_value=1, max_value=5, value=3)

    st.divider()

    if st.button("Check Health", use_container_width=True):
        try:
            resp = call_health(api_base)
            data = safe_json(resp)
            if resp.ok:
                st.success("Backend reachable")
                st.json(data)
            else:
                st.error(f"Health check failed: {resp.status_code}")
                st.json(data)
        except Exception as e:
            st.error(f"Connection failed: {e}")

    if st.button("Load System Status", use_container_width=True):
        try:
            resp = call_system_status(api_base)
            data = safe_json(resp)
            if resp.ok:
                st.success("Loaded system status")
                st.json(data)
            else:
                st.error(f"Status request failed: {resp.status_code}")
                st.json(data)
        except Exception as e:
            st.error(f"Connection failed: {e}")


default_text = """本発明は、半導体装置およびその製造方法に関する。"""

col_left, col_right = st.columns([1.05, 0.95])

with col_left:
    st.subheader("Input")

    japanese_text = st.text_area(
        "Japanese Patent Text",
        value=default_text,
        height=260,
        help="Paste Japanese patent content here.",
    )

    button_col1, button_col2 = st.columns(2)

    with button_col1:
        translate_clicked = st.button("Translate", type="primary", use_container_width=True)

    with button_col2:
        rag_test_clicked = st.button("Test RAG Only", use_container_width=True)

with col_right:
    st.subheader("Quick Summary")
    st.markdown(
        f"""
**API Base**  
`{api_base}`

**Domain**  
`{domain or "N/A"}`

**Section Type**  
`{section_type}`

**RAG Enabled**  
`{use_rag}`

**Examples Requested**  
`{num_examples}`
"""
    )

payload = {
    "japanese_text": japanese_text,
    "section_type": section_type,
    "domain": domain or None,
    "use_rag": use_rag,
    "num_examples": num_examples,
}

if translate_clicked:
    if not japanese_text.strip():
        st.warning("Please enter Japanese text first.")
    else:
        with st.spinner("Translating..."):
            try:
                resp = call_translate(api_base, api_key, payload)
                data = safe_json(resp)

                if not resp.ok:
                    st.error(f"Translation failed: HTTP {resp.status_code}")
                    st.json(data)
                else:
                    st.success("Translation completed")

                    st.subheader("Translation Result")
                    st.text_area(
                        "Traditional Chinese Translation",
                        value=data.get("translation", ""),
                        height=260,
                    )

                    meta_col1, meta_col2, meta_col3 = st.columns(3)
                    with meta_col1:
                        st.metric("Confidence", f"{data.get('confidence_score', 0):.2f}")
                    with meta_col2:
                        retrieved_examples = data.get("retrieved_examples", [])
                        st.metric("Examples Used", len(retrieved_examples))
                    with meta_col3:
                        terminology_used = data.get("terminology_used", [])
                        st.metric("Terms Matched", len(terminology_used))

                    st.subheader("Retrieved Examples")
                    if retrieved_examples:
                        for idx, example in enumerate(retrieved_examples, start=1):
                            render_example_card(example, idx)
                    else:
                        st.info("No RAG examples returned.")

                    st.subheader("Terminology Used")
                    render_term_table(terminology_used)

                    with st.expander("Raw Response JSON"):
                        st.json(data)

            except Exception as e:
                st.error(f"Request failed: {e}")

if rag_test_clicked:
    if not japanese_text.strip():
        st.warning("Please enter Japanese text first.")
    else:
        with st.spinner("Testing RAG..."):
            try:
                resp = call_test_rag(api_base, api_key, payload)
                data = safe_json(resp)

                if not resp.ok:
                    st.error(f"RAG test failed: HTTP {resp.status_code}")
                    st.json(data)
                else:
                    st.success("RAG debug completed")

                    rag_status = data.get("rag_status", {})

                    metric_col1, metric_col2, metric_col3 = st.columns(3)
                    with metric_col1:
                        st.metric("Examples Retrieved", rag_status.get("examples_retrieved", 0))
                    with metric_col2:
                        st.metric("Terms Matched", rag_status.get("terms_matched", 0))
                    with metric_col3:
                        avg_similarity = rag_status.get("avg_similarity", 0)
                        if isinstance(avg_similarity, (int, float)):
                            st.metric("Avg Similarity", f"{avg_similarity:.3f}")
                        else:
                            st.metric("Avg Similarity", "N/A")

                    st.subheader("Retrieved Examples")
                    examples = data.get("retrieved_examples", [])
                    if examples:
                        for idx, example in enumerate(examples, start=1):
                            render_example_card(example, idx)
                    else:
                        st.info("No examples retrieved.")

                    st.subheader("Matched Terminology")
                    render_term_table(data.get("terminology_found", []))

                    with st.expander("Raw Response JSON"):
                        st.json(data)

            except Exception as e:
                st.error(f"Request failed: {e}")