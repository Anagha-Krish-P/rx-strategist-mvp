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
  @import url("https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap");
  html, body, [class*="stApp"] {
    font-family: "Plus Jakarta Sans", sans-serif;
    color: #0f172a;
  }
  .stApp { background: #eef2f7; }
  header[data-testid="stHeader"],
  [data-testid="stToolbar"],
  #MainMenu, footer { display: none !important; }
  .block-container {
    padding-top: 1.15rem;
    padding-bottom: 2.75rem;
    max-width: 1180px;
  }
  .rx-topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    background: #ffffff;
    border: 1px solid #d7e2ee;
    border-radius: 18px;
    padding: 16px 20px;
    margin-bottom: 18px;
    box-shadow: 0 10px 30px rgba(15, 23, 42, 0.04);
  }
  .rx-brand-row { display: flex; align-items: center; gap: 14px; }
  .rx-mark {
    width: 42px;
    height: 42px;
    border-radius: 12px;
    background: linear-gradient(180deg, #12837a 0%, #0f766e 100%);
    color: #fff;
    font-weight: 800;
    font-size: 0.95rem;
    display: flex;
    align-items: center;
    justify-content: center;
    letter-spacing: -0.04em;
    flex-shrink: 0;
  }
  .rx-brand { font-size: 1.28rem; font-weight: 800; letter-spacing: -0.04em; color: #0b3b5a; line-height: 1.1; }
  .rx-sub { color: #64748b; margin-top: 3px; font-size: 0.84rem; font-weight: 500; }
  .rx-ready {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: #f0fdfa;
    color: #0f766e;
    border: 1px solid #99f6e4;
    border-radius: 999px;
    padding: 8px 14px;
    font-size: 0.78rem;
    font-weight: 700;
    white-space: nowrap;
  }
  .rx-ready span {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #14b8a6;
    box-shadow: 0 0 0 4px rgba(20, 184, 166, 0.18);
    display: inline-block;
  }
  div[data-testid="stHorizontalBlock"] { align-items: stretch !important; }
  div[data-testid="stHorizontalBlock"] > div {
    display: flex !important;
    flex-direction: column;
  }
  [data-testid="stVerticalBlockBorderWrapper"] {
    background: #ffffff;
    border: 1px solid #d7e2ee !important;
    border-radius: 18px !important;
    box-shadow: 0 10px 28px rgba(15, 23, 42, 0.04);
    flex: 1;
    height: 100%;
  }
  .rx-kicker {
    margin: 0 0 6px;
    font-size: 0.7rem;
    letter-spacing: 0.12em;
    font-weight: 800;
    color: #0f766e;
  }
  .rx-section-title {
    margin: 0 0 14px;
    font-size: 1.05rem;
    color: #0b3b5a;
    font-weight: 800;
  }
  .rx-hint { color: #64748b; font-size: 0.78rem; margin-top: 6px; }
  .rx-preview img {
    max-height: 220px;
    object-fit: contain;
    border-radius: 10px;
    border: 1px solid #e2e8f0;
    background: #f8fafc;
  }
  [data-testid="stImageCaption"] { color: #64748b !important; font-size: 0.75rem !important; }
  .status-low, .status-review, .status-unknown {
    border-radius: 18px;
    padding: 18px 22px;
    border: 1px solid transparent;
    margin: 8px 0 16px;
  }
  .status-low { background: #f0fdfa; border-color: #99f6e4; border-left: 5px solid #0f766e; }
  .status-review { background: #fff7ed; border-color: #fed7aa; border-left: 5px solid #b45309; }
  .status-unknown { background: #f8fafc; border-color: #e2e8f0; border-left: 5px solid #64748b; }
  .status-kicker {
    font-size: 0.7rem;
    letter-spacing: 0.12em;
    font-weight: 800;
    color: #64748b;
    margin-bottom: 6px;
  }
  .status-title { font-size: 1.45rem; font-weight: 800; margin: 0; color: #0b3b5a; }
  .status-low .status-title { color: #0f766e; }
  .status-review .status-title { color: #b45309; }
  .status-copy { margin: 6px 0 0; color: #475569; }
  .metric-card {
    background: #ffffff;
    border: 1px solid #d7e2ee;
    border-radius: 16px;
    padding: 16px;
    min-height: 96px;
    box-shadow: 0 8px 20px rgba(15, 23, 42, 0.04);
  }
  .metric-label { font-size: 0.75rem; color: #64748b; font-weight: 700; }
  .metric-value { font-size: 1.85rem; font-weight: 800; color: #0b3b5a; margin-top: 6px; line-height: 1; }
  .finding {
    background: #fff;
    border: 1px solid #e2e8f0;
    border-left: 4px solid #b45309;
    border-radius: 12px;
    padding: 14px 16px;
    margin-bottom: 10px;
  }
  .kg-line {
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 0.84rem;
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 8px 12px;
    margin-bottom: 6px;
    color: #0b3b5a;
  }
  .disclaimer {
    color: #64748b;
    font-size: 0.82rem;
    margin-top: 22px;
    padding-top: 14px;
    border-top: 1px solid #d7e2ee;
  }
  div[data-testid="stButton"] > button {
    background: #0f766e;
    border: 1px solid #0f766e;
    height: 2.8rem;
    font-weight: 700;
    border-radius: 12px;
  }
  div[data-testid="stButton"] > button:hover {
    background: #115e59;
    border-color: #115e59;
  }
  [data-testid="stFileUploaderDropzone"] { border-radius: 12px !important; }
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


def _metric_card(label: str, value) -> None:
    st.markdown(
        f"""
        <div class="metric-card">
          <div class="metric-label">{label}</div>
          <div class="metric-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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
        <div class="rx-topbar">
          <div class="rx-brand-row">
            <div class="rx-mark">Rx</div>
            <div>
              <div class="rx-brand">Rx-Strategist</div>
              <div class="rx-sub">AI-assisted Prescription Safety Analysis</div>
            </div>
          </div>
          <div class="rx-ready"><span></span>System Status: Ready</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns(2, gap="large")
    with left:
        with st.container(border=True):
            st.markdown('<p class="rx-kicker">INTAKE</p>', unsafe_allow_html=True)
            st.markdown('<p class="rx-section-title">Patient Profile</p>', unsafe_allow_html=True)
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

    with right:
        with st.container(border=True):
            st.markdown('<p class="rx-kicker">DOCUMENT</p>', unsafe_allow_html=True)
            st.markdown('<p class="rx-section-title">Prescription</p>', unsafe_allow_html=True)
            upload = st.file_uploader(
                "Upload Prescription",
                type=["jpg", "jpeg", "png", "webp"],
                accept_multiple_files=False,
            )
            st.markdown(
                '<div class="rx-hint">Supported: JPG / PNG / WebP</div>',
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
                st.image(
                    st.session_state.image_bytes,
                    caption=upload.name,
                    use_container_width=True,
                )
            else:
                st.session_state.file_id = None
                st.session_state.image_bytes = None
                st.session_state.image_name = None
                st.session_state.result = None
                st.session_state.view = None

    with st.container(border=True):
        notice, action = st.columns([2.4, 1], vertical_alignment="center")
        with notice:
            st.caption("Review patient details, then run analysis. Findings are assistive only.")
        with action:
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

    m1, m2, m3, m4 = st.columns(4, gap="medium")
    metrics = view["metrics"]
    with m1:
        _metric_card("Medicines Identified", metrics["medicines"])
    with m2:
        _metric_card("Potential Interactions", metrics["interactions"])
    with m3:
        _metric_card("Patient Risks", metrics["patient_risks"])
    with m4:
        _metric_card("Evidence Items", metrics["evidence"])

    with st.container(border=True):
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
