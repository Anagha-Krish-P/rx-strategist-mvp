import logging
import os
import sys
import tempfile
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from rx_strategist.agents.workflow import run_workflow
from rx_strategist.presentation.report import build_markdown_report
from rx_strategist.presentation.result_adapter import adapt_workflow_result
from rx_strategist.presentation.session import next_upload_state

logger = logging.getLogger("rx_strategist.app")

ALLOWED_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
DISCLAIMER = (
    "This system provides AI-assisted medication safety information "
    "and does not replace professional clinical judgment."
)

APP_CSS = """
<style>
  @import url("https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap");
  html, body, [class*="stApp"] {
    font-family: "IBM Plex Sans", sans-serif;
    color: #12263a;
  }
  .stApp { background: #f4f7fb; }
  .block-container { padding-top: 1.4rem; max-width: 1180px; }
  .rx-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    gap: 1rem;
    margin-bottom: 1.4rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid #d7e1ee;
  }
  .rx-brand { font-size: 1.7rem; font-weight: 700; letter-spacing: -0.03em; }
  .rx-sub { color: #5b6b7c; margin-top: 0.2rem; font-size: 0.95rem; }
  .rx-ready {
    background: #e8f6ee;
    color: #17643b;
    border: 1px solid #b7e0c6;
    border-radius: 999px;
    padding: 0.4rem 0.85rem;
    font-size: 0.82rem;
    font-weight: 600;
  }
  .rx-card {
    background: #fff;
    border: 1px solid #dce6f2;
    border-radius: 16px;
    padding: 1.15rem 1.2rem 1.25rem;
    box-shadow: 0 8px 24px rgba(18, 38, 58, 0.04);
    height: 100%;
  }
  .rx-card h3 { margin: 0 0 0.85rem; font-size: 1.02rem; }
  .rx-hint { color: #6b7c8d; font-size: 0.82rem; margin-top: 0.45rem; }
  .status-low, .status-review, .status-unknown {
    border-radius: 16px;
    padding: 1.2rem 1.3rem;
    border: 1px solid transparent;
  }
  .status-low { background: #e9f7ef; border-color: #b7e0c6; }
  .status-review { background: #fff6e5; border-color: #f0d39a; }
  .status-unknown { background: #eef2f6; border-color: #d4dde7; }
  .status-kicker {
    font-size: 0.75rem;
    letter-spacing: 0.08em;
    font-weight: 700;
    color: #5b6b7c;
    margin-bottom: 0.25rem;
  }
  .status-title { font-size: 1.45rem; font-weight: 700; margin: 0; }
  .status-copy { margin: 0.35rem 0 0; color: #334155; }
  .finding {
    background: #fff;
    border: 1px solid #e3ebf4;
    border-left: 4px solid #c9a227;
    border-radius: 10px;
    padding: 0.85rem 1rem;
    margin-bottom: 0.7rem;
  }
  .kg-line {
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 0.86rem;
    background: #f7fafc;
    border-radius: 8px;
    padding: 0.45rem 0.7rem;
    margin-bottom: 0.35rem;
  }
  .disclaimer {
    color: #5b6b7c;
    font-size: 0.84rem;
    margin-top: 1.5rem;
    padding-top: 0.9rem;
    border-top: 1px solid #d7e1ee;
  }
</style>
"""


def _parse_list(raw: str):
    return [part.strip() for part in (raw or "").split(",") if part.strip()]


def _file_id(upload) -> str:
    return f"{upload.name}:{upload.size}"


def _init_state():
    defaults = {
        "file_id": None,
        "image_bytes": None,
        "image_name": None,
        "result": None,
        "error": None,
        "view": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _user_error(message: str):
    st.session_state.error = message
    st.session_state.result = None
    st.session_state.view = None


def _analyze(image_bytes: bytes, image_name: str, overrides: dict):
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        _user_error("A Gemini API key is required. Set the GEMINI_API_KEY environment variable.")
        return
    suffix = Path(image_name).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        _user_error("Unsupported image type. Upload a JPG, PNG, or WebP file.")
        return
    if not image_bytes:
        _user_error("The uploaded file is empty.")
        return

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
            handle.write(image_bytes)
            tmp_path = handle.name
        with st.spinner("Running OCR, extraction, and safety analysis..."):
            result = run_workflow(
                image_path=tmp_path,
                api_key=api_key,
                patient_overrides=overrides,
            )
        medicines = (result.get("verification") or {}).get("medications") or []
        if not medicines:
            _user_error("No medicines were extracted from this prescription.")
            return
        st.session_state.result = result
        st.session_state.view = adapt_workflow_result(result)
        st.session_state.error = None
    except ValueError as exc:
        logger.exception("Workflow value error")
        _user_error(str(exc))
    except Exception:
        logger.exception("Workflow failed")
        _user_error("Analysis failed. Check the image and API key, then try again.")
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)


def _render_findings(title: str, items: list):
    if not items:
        return
    with st.expander(f"{title} ({len(items)})", expanded=True):
        for item in items:
            medicines = " ↔ ".join(str(name) for name in item.get("medicines") or [] if name)
            st.markdown(
                f"""
                <div class="finding">
                  <strong>{item.get("severity", "Review")}</strong>
                  <div style="margin-top:0.25rem">{medicines}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown(f"**Why:** {item.get('reason')}")
            st.markdown(f"**Recommendation:** {item.get('recommendation')}")


def main():
    st.set_page_config(
        page_title="Rx-Strategist",
        page_icon="Rx",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.markdown(APP_CSS, unsafe_allow_html=True)
    _init_state()
    st.markdown(
        """
        <div class="rx-header">
          <div>
            <div class="rx-brand">Rx-Strategist</div>
            <div class="rx-sub">AI-assisted Prescription Safety Analysis</div>
          </div>
          <div class="rx-ready">System Status: Ready</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns(2, gap="large")
    with left:
        st.markdown('<div class="rx-card"><h3>Patient Profile</h3>', unsafe_allow_html=True)
        age = st.number_input("Age", min_value=0, max_value=120, value=55, step=1)
        conditions_raw = st.text_input(
            "Medical Conditions",
            value="hypertension, type 2 diabetes",
            help="Comma-separated. Used by indication matching.",
        )
        allergies_raw = st.text_input(
            "Known Allergies",
            value="",
            help="Comma-separated. Matched against prescribed drug names.",
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="rx-card"><h3>Prescription</h3>', unsafe_allow_html=True)
        upload = st.file_uploader(
            "Upload Prescription",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=False,
        )
        st.markdown(
            '<div class="rx-hint">Supported: JPG / PNG / WebP</div></div>',
            unsafe_allow_html=True,
        )

    if upload is not None:
        current_id = _file_id(upload)
        upload_state = next_upload_state(st.session_state.file_id, current_id)
        st.session_state.file_id = upload_state["file_id"]
        st.session_state.image_bytes = upload.getvalue()
        st.session_state.image_name = upload.name
        if upload_state["invalidate_result"]:
            st.session_state.result = None
            st.session_state.view = None
            st.session_state.error = None
        st.image(st.session_state.image_bytes, caption=upload.name, use_container_width=True)
    else:
        st.session_state.file_id = None
        st.session_state.image_bytes = None
        st.session_state.image_name = None
        st.session_state.result = None
        st.session_state.view = None

    analyze = st.button("Analyze Prescription", type="primary", use_container_width=True)
    if analyze:
        if not st.session_state.image_bytes:
            _user_error("Upload a prescription image before analyzing.")
        else:
            _analyze(
                st.session_state.image_bytes,
                st.session_state.image_name,
                {
                    "age": int(age),
                    "conditions": _parse_list(conditions_raw),
                    "allergies": _parse_list(allergies_raw),
                },
            )

    if st.session_state.error:
        st.error(st.session_state.error)

    view = st.session_state.view
    if not view:
        st.markdown(f'<div class="disclaimer">{DISCLAIMER}</div>', unsafe_allow_html=True)
        return

    status = view["status"]
    st.markdown(
        f"""
        <div class="{status['css_class']}">
          <div class="status-kicker">OVERALL SAFETY ASSESSMENT</div>
          <p class="status-title">{status['label']}</p>
          <p class="status-copy">{status['headline']}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    m1, m2, m3, m4 = st.columns(4)
    metrics = view["metrics"]
    m1.metric("Medicines Identified", metrics["medicines"])
    m2.metric("Potential Interactions", metrics["interactions"])
    m3.metric("Patient Risks", metrics["patient_risks"])
    m4.metric("Evidence Items", metrics["evidence"])

    st.subheader("Medicines")
    st.dataframe(view["medicines"], use_container_width=True, hide_index=True)

    st.subheader("Safety Findings")
    findings = view["findings"]
    if not any(findings.values()):
        st.info("No safety findings were reported by the current analysis.")
    else:
        _render_findings("Drug–Drug Interactions", findings["interactions"])
        _render_findings("Indication Concerns", findings["indications"])
        _render_findings("Dosage / Frequency Concerns", findings["dosage"])
        _render_findings("Allergy Concerns", findings["allergies"])

    st.subheader("Evidence & Knowledge")
    if view["kg_lines"]:
        st.caption("Knowledge graph relationships")
        for line in view["kg_lines"]:
            st.markdown(f'<div class="kg-line">{line}</div>', unsafe_allow_html=True)
    if view["evidence"]:
        for item in view["evidence"]:
            score = item.get("score")
            label = item["title"]
            if score is not None:
                label = f"{label}  ·  relevance {score}"
            with st.expander(label):
                st.caption(f"Evidence source: `{item['source']}`")
                st.write(item["text"])
    else:
        st.caption("No retrieved evidence items.")

    with st.expander("Extracted Prescription Text"):
        st.text(view["ocr_text"] or "No OCR text was returned.")

    st.subheader("AI Safety Explanation")
    st.write(view["explanation_notes"] or "No explanation notes were returned by the final checker.")
    st.caption(view["explanation_recap"])

    st.subheader("Final Report")
    report = build_markdown_report(view)
    st.download_button(
        "Download Report",
        data=report,
        file_name="rx_strategist_report.md",
        mime="text/markdown",
    )
    with st.expander("Report preview"):
        st.markdown(report)

    st.markdown(f'<div class="disclaimer">{DISCLAIMER}</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
