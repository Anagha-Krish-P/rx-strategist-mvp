"""
Rx-Strategist - AI-assisted prescription safety analysis
Flow: Cover -> Patient & Prescription -> Analysis -> Knowledge Graph -> Overview
Run:  streamlit run app.py
"""
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Rx-Strategist", page_icon="💊", layout="wide")

STEPS = ["Cover", "Patient & Prescription", "Analysis", "Knowledge Graph", "Overview"]

# ----------------------------------------------------------------------------
# 1. BACKEND ADAPTER  -  connect your real pipeline here
# ----------------------------------------------------------------------------
def run_pipeline(age, conditions, allergies, image_bytes, image_name):
    """
    Replace the body of this function with a call to your rx_strategist code
    (OCR -> medicine extraction -> deterministic verifier -> retrieval -> explanation).
    It must return a dict with the keys shown in the demo below.
    """
    # Example:
    #   from rx_strategist.pipeline import analyze
    #   raw = analyze(image_bytes, age=age, conditions=conditions, allergies=allergies)
    #   return {...map raw into the dict below...}

    return {  # demo data so the UI works before the backend is connected
        "status": "REVIEW",
        "headline": "Review recommended",
        "summary": "Potential safety concern detected.",
        "extracted_text": (
            "55-year-old female with hypertension and type 2 diabetes.\n"
            "Losartan 50 mg OD PO.\nMetformin 500 mg BID PO.\n"
            "Kidney function is normal. No known allergies."
        ),
        "medicines": [
            {"Medicine": "Losartan", "Dose": "50 mg", "Frequency": "once daily",
             "Verification": "APPROPRIATE", "Risk": "Low"},
            {"Medicine": "Metformin", "Dose": "500 mg", "Frequency": "twice daily",
             "Verification": "APPROPRIATE", "Risk": "Low"},
        ],
        "interactions": [
            {"a": "Losartan", "b": "Metformin",
             "why": "Demo interaction record",
             "recommendation": "Clinician review of this drug combination is recommended."},
        ],
        "patient_risks": [],
        "graph": [
            ("Losartan", "TREATS", "hypertension"),
            ("Losartan", "TREATS", "diabetic nephropathy"),
            ("Metformin", "TREATS", "type 2 diabetes"),
            ("Losartan", "INTERACTS_WITH", "Metformin"),
            ("Losartan:hypertension", "HAS_DOSAGE", "50 mg once daily"),
            ("Metformin:type 2 diabetes", "HAS_DOSAGE", "500 mg twice daily"),
        ],
        "evidence": [
            {"title": "Losartan and metformin interaction", "source": "losartan_metformin_interaction",
             "relevance": 0.6921,
             "text": "The demo knowledge base records an example interaction between losartan and "
                     "metformin. When both drugs appear on the same prescription, the deterministic "
                     "verifier flags INTERACTION_FOUND and the overall status becomes REVIEW."},
            {"title": "Metformin for type 2 diabetes", "source": "metformin_t2dm",
             "relevance": 0.4658, "text": "Metformin is a first-line therapy for type 2 diabetes."},
            {"title": "Dosage guardrails", "source": "dosage_guardrails",
             "relevance": 0.4061, "text": "Dose ranges used by the verifier to flag out-of-range prescriptions."},
        ],
        "explanation": (
            "Final decision matches the deterministic verification engine. Retrieved evidence and "
            "knowledge-graph context are attached for review and are not used to override "
            "APPROPRIATE or REVIEW. The deterministic verifier flagged this prescription for review "
            "because 1 drug-drug interaction record was found."
        ),
    }


# ----------------------------------------------------------------------------
# 2. STYLE
# ----------------------------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');
    :root{
        --navy:#12304a; --blue:#1f4e79; --teal:#2f7d6b; --amber:#c98a12;
        --red:#b83a2e; --bg:#f4f7fb; --line:#d9e2ec; --muted:#5f7387;
    }
    html, body, [class*="css"], .stApp { font-family:'IBM Plex Sans',sans-serif; }
    .stApp { background:var(--bg); color:var(--navy); }
    .block-container { max-width:1150px; padding-top:1.5rem; }

    /* stepper */
    .stepper{ display:flex; gap:8px; flex-wrap:wrap; margin-bottom:1.2rem; }
    .pill{ padding:6px 14px; border-radius:999px; border:1px solid var(--line);
           font-size:.85rem; color:var(--muted); background:#fff; }
    .pill.done{ color:var(--teal); border-color:#bfdcd3; background:#eef7f4; }
    .pill.now{ color:#fff; background:var(--blue); border-color:var(--blue); font-weight:600; }

    /* cover */
    .hero{ background:var(--navy); color:#fff; border-radius:20px; padding:64px 48px 56px; }
    .rxmark{ width:72px; height:72px; border-radius:18px; background:#fff; color:var(--navy);
             display:flex; align-items:center; justify-content:center; font-weight:700;
             font-size:2rem; margin-bottom:24px; }
    .hero h1{ font-size:3.4rem; line-height:1.05; margin:0 0 12px; letter-spacing:-.02em; color:#fff; }
    .hero p{ font-size:1.2rem; max-width:620px; color:#c9d8e6; margin:0; }
    .flow{ display:flex; gap:12px; margin-top:32px; flex-wrap:wrap; }
    .flow span{ border:1px solid #3d5f7d; border-radius:10px; padding:8px 14px; font-size:.95rem; color:#e6eef6; }

    /* result banners */
    .banner{ border-radius:14px; padding:20px 24px; margin-bottom:16px; border:1px solid; }
    .banner.review{ background:#fff5e0; border-color:#f0d9a0; }
    .banner.ok{ background:#eaf6f1; border-color:#bfdcd3; }
    .banner.alert{ background:#fdecea; border-color:#f0b9b3; }
    .banner h3{ margin:0 0 4px; font-size:1.25rem; }
    .banner p{ margin:0; color:#33475a; }
    .finding{ background:#fff; border-left:5px solid var(--amber); border-radius:10px;
              padding:14px 18px; margin-bottom:10px; }
    .note{ color:var(--muted); font-size:.9rem; }
    div.stButton > button[kind="primary"]{ background:var(--blue); border-color:var(--blue); }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------------
# 3. STATE + NAVIGATION HELPERS
# ----------------------------------------------------------------------------
st.session_state.setdefault("step", 0)
st.session_state.setdefault("result", None)
st.session_state.setdefault("profile", {})


def go(n: int):
    st.session_state.step = max(0, min(n, len(STEPS) - 1))


def stepper():
    cur = st.session_state.step
    pills = ""
    for i, name in enumerate(STEPS):
        cls = "now" if i == cur else "done" if i < cur else ""
        pills += f'<span class="pill {cls}">{i + 1}. {name}</span>'
    st.markdown(f'<div class="stepper">{pills}</div>', unsafe_allow_html=True)


def nav(next_label="Continue", next_disabled=False):
    cur = st.session_state.step
    st.write("")
    left, _, right = st.columns([1, 3, 1])
    left.button("Back", on_click=go, args=(cur - 1,), use_container_width=True, key=f"back{cur}")
    if cur < len(STEPS) - 1:
        right.button(next_label, on_click=go, args=(cur + 1,), type="primary",
                     use_container_width=True, disabled=next_disabled, key=f"next{cur}")


def esc(s):
    return str(s).replace("\\", "\\\\").replace('"', '\\"')


# ----------------------------------------------------------------------------
# 4. PAGES
# ----------------------------------------------------------------------------
def page_cover():
    st.markdown(
        """
        <div class="hero">
            <div class="rxmark">Rx</div>
            <h1>Rx-Strategist</h1>
            <p>Check a prescription against the patient profile before it reaches the pharmacy.
               Every flag comes with the evidence behind it.</p>
            <div class="flow">
                <span>Read the prescription</span>
                <span>Verify dose and interactions</span>
                <span>Explain with evidence</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")
    c1, c2, c3 = st.columns(3)
    c1.markdown("**Reads handwritten and printed prescriptions**  \nUpload a photo and the medicines, doses and frequencies are extracted.")
    c2.markdown("**Rule-based safety verdict**  \nA deterministic verifier decides APPROPRIATE or REVIEW, so the result is repeatable.")
    c3.markdown("**Knowledge graph and sources**  \nEach finding links to the drugs, conditions and documents that support it.")
    st.write("")
    _, mid, _ = st.columns([2, 1.2, 2])
    mid.button("Start analysis", on_click=go, args=(1,), type="primary",
               use_container_width=True, key="start")
    st.caption("Final-year project  |  Your Name  |  Guide: Guide Name  |  Institution, 2026")
    st.caption("Decision-support prototype. It does not replace a doctor or pharmacist.")


def page_input():
    st.header("Patient profile and prescription")
    left, right = st.columns(2, gap="large")

    with left:
        st.subheader("Patient profile")
        age = st.number_input("Age", 0, 120, st.session_state.profile.get("age", 55))
        conditions = st.text_input("Medical conditions",
                                   st.session_state.profile.get("conditions", ""),
                                   placeholder="e.g. hypertension, type 2 diabetes",
                                   help="Separate conditions with commas.")
        allergies = st.text_input("Known allergies",
                                  st.session_state.profile.get("allergies", ""),
                                  placeholder="e.g. penicillin (leave empty if none)")

    with right:
        st.subheader("Prescription")
        upload = st.file_uploader("Upload prescription", type=["jpg", "jpeg", "png", "webp"])
        st.caption("Supported: JPG / PNG / WebP")
        if upload:
            st.image(upload, caption=upload.name, use_container_width=True)

    st.write("")
    if st.button("Analyze prescription", type="primary", use_container_width=True,
                 disabled=upload is None, key="analyze"):
        with st.spinner("Reading the prescription and running safety checks..."):
            st.session_state.profile = {"age": age, "conditions": conditions, "allergies": allergies}
            st.session_state.result = run_pipeline(
                age, conditions, allergies, upload.getvalue(), upload.name
            )
        go(2)
        st.rerun()
    if upload is None:
        st.caption("Upload a prescription image to enable analysis.")
    nav(next_disabled=st.session_state.result is None)


def page_results():
    r = st.session_state.result
    st.header("Prescription analysis")
    if not r:
        st.info("Run an analysis first. Go back and upload a prescription.")
        nav(next_disabled=True)
        return

    css = {"REVIEW": "review", "APPROPRIATE": "ok"}.get(r["status"], "alert")
    st.markdown(
        f'<div class="banner {css}"><h3>{r["headline"]}</h3><p>{r["summary"]}</p></div>',
        unsafe_allow_html=True,
    )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Medicines identified", len(r["medicines"]))
    m2.metric("Potential interactions", len(r["interactions"]))
    m3.metric("Patient risks", len(r["patient_risks"]))
    m4.metric("Evidence items", len(r["evidence"]))

    st.subheader("Medicines")
    st.dataframe(pd.DataFrame(r["medicines"]), use_container_width=True, hide_index=True)

    st.subheader("Safety findings")
    with st.expander(f"Drug-drug interactions ({len(r['interactions'])})", expanded=True):
        if not r["interactions"]:
            st.write("No interactions found.")
        for it in r["interactions"]:
            st.markdown(
                f'<div class="finding"><b>{it["a"]} and {it["b"]}</b></div>', unsafe_allow_html=True
            )
            st.markdown(f"**Why:** {it['why']}")
            st.markdown(f"**Recommendation:** {it['recommendation']}")
    with st.expander(f"Patient risks ({len(r['patient_risks'])})"):
        if not r["patient_risks"]:
            st.write("No allergy, age or condition risks found.")
        for risk in r["patient_risks"]:
            st.write("- " + str(risk))

    st.subheader("Evidence")
    for ev in r["evidence"]:
        with st.expander(f"{ev['title']}  (relevance {ev['relevance']:.4f})"):
            st.caption(f"Source: {ev['source']}")
            st.write(ev["text"])
    with st.expander("Extracted prescription text"):
        st.code(r["extracted_text"], language=None)

    st.subheader("AI safety explanation")
    st.write(r["explanation"])
    nav("View knowledge graph")


def build_dot(triples):
    drugs, conds = set(), set()
    for s, rel, o in triples:
        if rel == "TREATS":
            drugs.add(s.lower()); conds.add(o.lower())
        elif rel == "INTERACTS_WITH":
            drugs.update([s.lower(), o.lower()])

    lines = ['digraph G {', 'rankdir=LR; bgcolor="transparent";',
             'node [fontname="Helvetica", fontsize=12, style="filled,rounded", shape=box, penwidth=0];',
             'edge [fontname="Helvetica", fontsize=10];']
    for n in sorted(drugs):
        lines.append(f'"{esc(n)}" [label="{esc(n.title())}", fillcolor="#1f4e79", fontcolor="white"];')
    for n in sorted(conds - drugs):
        lines.append(f'"{esc(n)}" [label="{esc(n)}", fillcolor="#dcefe9", fontcolor="#12304a"];')
    for s, rel, o in triples:
        if rel == "TREATS":
            lines.append(f'"{esc(s.lower())}" -> "{esc(o.lower())}" [label="treats", color="#2f7d6b", fontcolor="#2f7d6b"];')
        elif rel == "INTERACTS_WITH":
            lines.append(f'"{esc(s.lower())}" -> "{esc(o.lower())}" [label="interacts with", dir=both, '
                         f'style=dashed, color="#b83a2e", fontcolor="#b83a2e", penwidth=2];')
    lines.append("}")
    return "\n".join(lines)


def page_graph():
    r = st.session_state.result
    st.header("Knowledge graph and interactions")
    if not r:
        st.info("Run an analysis first.")
        nav(next_disabled=True)
        return

    st.markdown(
        "Blue boxes are drugs, green boxes are conditions. "
        "Green arrows show what a drug treats, the dashed red line marks an interaction."
    )
    st.graphviz_chart(build_dot(r["graph"]), use_container_width=True)

    st.subheader("All relationships")
    df = pd.DataFrame(r["graph"], columns=["Subject", "Relationship", "Object"])
    st.dataframe(df, use_container_width=True, hide_index=True)

    # final report
    p = st.session_state.profile
    report = (
        f"# Rx-Strategist Safety Report\n\nGenerated: {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC\n\n"
        f"## Overall Assessment\n\n**{r['headline'].upper()}**\n\n{r['summary']}\n\n"
        f"## Patient Profile\n\n- Age: {p.get('age')}\n- Conditions: {p.get('conditions') or 'None recorded'}\n"
        f"- Allergies: {p.get('allergies') or 'None recorded'}\n\n"
        f"## Medicines\n\n" + "\n".join(
            f"- {m['Medicine']} {m['Dose']} {m['Frequency']} ({m['Verification']}, risk {m['Risk']})"
            for m in r["medicines"]) +
        "\n\n## Interactions\n\n" + ("\n".join(
            f"- {i['a']} + {i['b']}: {i['why']}. {i['recommendation']}" for i in r["interactions"])
            or "None") +
        f"\n\n## Explanation\n\n{r['explanation']}\n"
    )
    st.subheader("Final report")
    st.download_button("Download report", report, "rx_strategist_report.md", "text/markdown")
    with st.expander("Report preview"):
        st.markdown(report)
    nav("Project overview")


def page_overview():
    st.header("Project overview")
    st.write(
        "Prescription errors and missed drug interactions are a common cause of preventable harm. "
        "Rx-Strategist reads a prescription image, checks it against the patient profile and a "
        "knowledge base, and returns a safety verdict that a clinician can review and trace."
    )

    st.subheader("How it works")
    a, b, c, d, e = st.columns(5)
    a.markdown("**1. Read**  \nOCR extracts text from the prescription image.")
    b.markdown("**2. Extract**  \nMedicines, doses and frequencies are structured.")
    c.markdown("**3. Verify**  \nA deterministic engine checks doses, interactions and patient risks.")
    d.markdown("**4. Retrieve**  \nRelevant evidence and graph relations are attached.")
    e.markdown("**5. Explain**  \nAn AI summary restates the verdict in plain language.")

    st.subheader("Technologies")
    t1, t2, t3 = st.columns(3)
    with t1:
        st.markdown("**Interface**\n- Streamlit\n- Graphviz (graph view)\n- Pandas")
    with t2:
        st.markdown("**AI and retrieval**\n- Google Gemini API\n- Embedding-based retrieval\n- Knowledge graph (drug, condition, dosage relations)")
    with t3:
        st.markdown("**Engineering**\n- Python\n- Rule-based verifier\n- GitHub and Google Colab")

    st.subheader("Limits and next steps")
    st.markdown(
        "- The knowledge base is a demo set, not a full clinical monograph.\n"
        "- The AI explanation never overrides the verifier.\n"
        "- Next: a larger drug database, more interaction types, multi-language prescriptions."
    )
    st.info("Decision-support prototype. A qualified clinician must confirm every result.")
    st.write("")
    st.button("Start a new analysis", on_click=lambda: (go(1), st.session_state.update(result=None)))
    nav()


# ----------------------------------------------------------------------------
# 5. ROUTER
# ----------------------------------------------------------------------------
PAGES = [page_cover, page_input, page_results, page_graph, page_overview]

if st.session_state.step > 0:
    stepper()
PAGES[st.session_state.step]()
