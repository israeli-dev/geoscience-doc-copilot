"""
PetroLens Executive v3.5 PRODUCTION - FINAL with Dark/Light toggle restored
- Barrel logo, No API input (hardcoded), No "real"/"hallucination"
- Spinner bug fixed: error handling OUTSIDE spinner
- Production branding
- Dark/Light toggle added back
"""
import streamlit as st
import requests
import plotly.graph_objects as go
from datetime import datetime
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch

st.set_page_config(page_title="PetroLens Executive v3.5 Production", layout="wide", page_icon="🛢️")

# ----------------- THEME TOGGLE RESTORED -----------------
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

# ----------------- PRODUCTION CONFIG - HARDCODED, NO INPUT -----------------
API_URL = "https://geoscience-doc-copilot.onrender.com/api/upload-report"

def calc_posg(probs_dict):
    p = 1.0
    for v in probs_dict.values():
        p *= max(0.05, min(0.99, float(v)))
    return p

def normalize_elements(raw_breakdown):
    if isinstance(raw_breakdown, dict) and "Source" in raw_breakdown:
        elements = {}
        for k, v in raw_breakdown.items():
            score = int(min(100, max(0, float(v.get("score", 50)))))
            prob = float(min(0.99, max(0.05, float(v.get("prob", score/100)))))
            elements[k] = {"score": score, "prob": prob, "comment": v.get("comment",""), "detail": v.get("detail","")}
        return elements
    bd = raw_breakdown or {}
    elements = {
        "Source": {"score": int(min(100, (bd.get("source_rock", 18)/20)*100)), "prob": min(0.99, max(0.05, bd.get("source_rock", 18)/20)), "comment": "Source rock presence & maturity.", "detail": ""},
        "Reservoir": {"score": int(min(100, (bd.get("reservoir_quality", 30)/40)*100)), "prob": min(0.99, max(0.05, bd.get("reservoir_quality", 30)/40)), "comment": "Reservoir quality.", "detail": ""},
        "Trap": {"score": int(min(100, (bd.get("trap_seal", 16)/20)*100)), "prob": min(0.99, max(0.05, bd.get("trap_seal", 16)/20)), "comment": "Trap geometry.", "detail": ""},
        "Seal": {"score": int(min(100, (bd.get("trap_seal", 16)/20)*90)), "prob": min(0.99, max(0.05, (bd.get("trap_seal", 16)/20)*0.9)), "comment": "Seal capacity.", "detail": ""},
        "Charge": {"score": 85, "prob": 0.82, "comment": "Charge timing.", "detail": ""},
    }
    return elements

def create_executive_pdf(analysis, filename, posg_data, model_used):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    story = []
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=16, textColor=colors.black, spaceAfter=6)
    normal = ParagraphStyle('Normal2', parent=styles['Normal'], fontSize=9, leading=12)
    h2 = ParagraphStyle('H2', parent=styles['Heading2'], fontSize=11, textColor=colors.HexColor("#1e40af"), spaceBefore=10, spaceAfter=4)
    story.append(Paragraph("PetroLens - Commercial Viability Report v3.5 Production", title_style))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | File: {filename} | Model: {model_used} | POSg: {posg_data['posg']*100:.1f}%", normal))
    story.append(Spacer(1, 8))
    viability_data = [
        ["Viability Score", f"{analysis.get('commercial_viability_score', 0)}/100"],
        ["Verdict", analysis.get('commercial_verdict', 'APPRAISE')],
        ["AFC Flag", analysis.get('AFC_flag', 'Med')],
        ["POSg", f"{posg_data['posg']*100:.1f}%"]
    ]
    t = Table(viability_data, colWidths=[2.2*inch, 4.3*inch])
    t.setStyle(TableStyle([('BACKGROUND', (0,0), (0,-1), colors.HexColor("#e0e7ff")), ('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('FONTSIZE', (0,0), (-1,-1), 9), ('PADDING', (0,0), (-1,-1), 6)]))
    story.append(t)
    story.append(Spacer(1, 10))
    story.append(Paragraph("Executive Summary", h2))
    story.append(Paragraph(analysis.get('executive_summary', 'No summary'), normal))
    story.append(Spacer(1, 8))
    story.append(Paragraph("Petroleum System Confidence", h2))
    breakdown_data = [["Component", "Score", "Prob", "Comment"]]
    for k,v in posg_data['elements'].items():
        breakdown_data.append([k, f"{v['score']}", f"{v['prob']:.2f}", v.get('comment','')[:90]])
    t2 = Table(breakdown_data, colWidths=[1.2*inch, 0.8*inch, 0.6*inch, 3.9*inch])
    t2.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e40af")), ('TEXTCOLOR', (0,0), (-1,0), colors.white), ('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('FONTSIZE', (0,0), (-1,-1), 8)]))
    story.append(t2)
    story.append(Spacer(1, 8))
    story.append(Paragraph("Fluid & Formation", h2))
    fluid = analysis.get('fluid_analysis', {})
    vol = analysis.get('volumetrics', {})
    prod = analysis.get('production_forecast', {})
    fluid_data = [
        ["Dominant Fluid", fluid.get('dominant_fluid', analysis.get('dominant_fluid','-'))],
        ["Oil Quality", fluid.get('oil_quality','-')],
        ["Gas Quality", fluid.get('gas_quality','-')],
        ["Pressure", f"{analysis.get('formation_pressure','-')} ({analysis.get('pressure_gradient','-')})"],
        ["STOIIP", vol.get('stoiip', '-')],
        ["Recoverable", vol.get('recoverable_oil', '-')],
        ["Initial Rate", prod.get('initial_rate','-')],
        ["Field Life", prod.get('field_life','-')],
    ]
    t4 = Table(fluid_data, colWidths=[2.2*inch, 4.3*inch])
    t4.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('BACKGROUND', (0,0), (0,-1), colors.HexColor("#f3f4f6")), ('FONTSIZE', (0,0), (-1,-1), 9)]))
    story.append(t4)
    story.append(Spacer(1, 8))
    story.append(Paragraph("Risk Factors", h2))
    risks = analysis.get('risk_factors', [])
    for i, r in enumerate(risks, 1):
        story.append(Paragraph(f"{i}. {r}", normal))
    doc.build(story)
    buffer.seek(0)
    return buffer

# SIDEBAR PRODUCTION with DARK/LIGHT TOGGLE
with st.sidebar:
    st.markdown("### 🛢️ PetroLens Executive v3.5")
    st.caption("Production - Subsurface Intelligence")
    st.divider()
    
    # --- TOGGLE RESTORED ---
    st.markdown("#### 🎨 Appearance")
    dark_mode = st.toggle("🌙 Dark Mode", value=st.session_state.dark_mode, help="Switch between Light and Dark theme")
    st.session_state.dark_mode = dark_mode
    if dark_mode:
        st.caption("🌙 Dark mode active")
    else:
        st.caption("☀️ Light mode active")
    st.divider()
    
    st.markdown("**Petroleum System:** Source, Reservoir, Trap, Seal, Charge")
    st.markdown("**POSg:** Multiplicative (Rose 1987)")
    st.divider()
    st.caption("Models: Flash (20/day free) / Pro (billing)")
    st.caption("Build: 2026-09-25 • v3.5 Production + Theme Toggle")

# APPLY THEME CSS
if st.session_state.dark_mode:
    # DARK MODE CSS - make page black/white toggle
    st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #fafafa; }
    .stMarkdown, p, li, h1, h2, h3 { color: #fafafa !important; }
    .stCaption { color: #a0a0a0 !important; }
    div[data-testid="stMetricValue"] { color: #fafafa !important; }
    div[data-testid="stMetricLabel"] { color: #a0a0a0 !important; }
    .stFileUploader, div[data-testid="stFileUploader"] { background-color: #1e1e1e; }
    </style>
    """, unsafe_allow_html=True)
else:
    # LIGHT MODE CSS
    st.markdown("""
    <style>
    .stApp { background-color: #ffffff; color: #000000; }
    .stMarkdown, p, li, h1, h2, h3 { color: #000000 !important; }
    .stCaption { color: #666666 !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛢️ PetroLens - Subsurface Intelligence")
st.caption("v3.5 Production | Commercial Viability Gauge | POSg Multiplicative | Executive Reporting | 🌗 Theme Toggle Restored")

uploaded_file = st.file_uploader("Upload Geoscience Report (PDF/DOCX/TXT/MD)", type=["pdf","docx","txt","md"])

if uploaded_file is None:
    st.info("👆 Upload a petroleum geoscience report to analyze commercial viability.")
    # Show theme preview
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Light Mode:** Clean white background for presentations")
    with col2:
        st.markdown("**Dark Mode:** Easy on eyes for night work")
    st.stop()

# Wake up Render backend (free tier sleeps)
with st.spinner("⏳ Waking up backend (Render free tier 50s)..."):
    try:
        requests.get("https://geoscience-doc-copilot.onrender.com/", timeout=10)
    except:
        pass

# Upload and analyze
with st.spinner("🔬 Analyzing report with Gemini 3 Flash... (may take 30-60s)"):
    try:
        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
        data = {"model": "flash"}
        resp = requests.post(API_URL, files=files, data=data, timeout=120)
    except requests.exceptions.ReadTimeout:
        st.error("⏱️ Backend waking up — Render free tier needs 50s. Please wait 30s and retry upload.")
        st.stop()
    except Exception as e:
        st.error(f"❌ Connection error: {e}")
        st.stop()

if resp.status_code != 200:
    try:
        err = resp.json()
        msg = err.get("detail", str(err))
    except:
        msg = resp.text[:500]
    if "overloaded" in msg.lower() or resp.status_code == 503:
        st.error("⚠️ Gemini model overloaded (503). Please wait 60 seconds and retry — Flash free tier 20/day limit.")
    else:
        st.error(f"❌ Backend error {resp.status_code}: {msg}")
    st.stop()

# Success path
try:
    result = resp.json()
    a = result.get("analysis", {})
    
    if a.get("is_oil_gas_document") == False:
        st.error("🚫 REJECTED - Not Oil & Gas Document")
        st.write(f"**Detected:** {a.get('document_type_detected', 'Unknown')}")
        st.write(f"**Reason:** {a.get('rejection_reason') or a.get('executive_summary') or 'Not petroleum'}")
        st.info("Upload a geoscience report.")
        st.stop()

    model_used = result.get("model_used", "gemini-3-flash-preview")
    if "petroleum_system" in a and isinstance(a["petroleum_system"], dict):
        elements = normalize_elements(a["petroleum_system"])
        breakdown = {k.lower(): v["prob"] for k,v in elements.items()}
        posg = a.get("posg") or calc_posg(breakdown)
    else:
        bd = a.get("viability_breakdown", {}) or a.get("posg_breakdown", {})
        if bd and all(isinstance(v, (int,float)) and v <= 1 for v in bd.values()):
            breakdown = {k.lower(): float(v) for k,v in bd.items()}
            elements = {}
            for k, prob in breakdown.items():
                key_cap = k.capitalize()
                elements[key_cap] = {"score": int(prob*100), "prob": prob, "comment": f"{key_cap} confidence", "detail": ""}
            for req in ["Source","Reservoir","Trap","Seal","Charge"]:
                if req not in elements:
                    elements[req] = {"score": 70, "prob": 0.70, "comment": f"{req} inferred", "detail": ""}
            posg = a.get("posg") or calc_posg(breakdown)
        else:
            elements = normalize_elements(bd)
            breakdown = {k.lower(): v["prob"] for k,v in elements.items()}
            posg = a.get("posg") or calc_posg(breakdown)
    
    for k in elements:
        elements[k]["score"] = int(min(100, max(0, elements[k].get("score", 0))))
        elements[k]["prob"] = float(min(0.99, max(0.05, elements[k].get("prob", 0.5))))
    posg = float(min(0.99, max(0.01, posg)))
    posg_data = {"posg": posg, "breakdown": breakdown, "elements": elements}

    col_gauge1, col_gauge2, col_verdict = st.columns([2,2,1])
    with col_gauge1:
        fig_gauge1 = go.Figure(go.Indicator(mode="gauge+number", value=posg*100, title={'text': "POSg - Geological CoS", 'font': {'size': 14, 'color': 'white' if st.session_state.dark_mode else 'black'}}, number={'suffix': "%", 'font': {'size': 28, 'color': 'white' if st.session_state.dark_mode else 'black'}}, gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "#10b981" if posg>=0.25 else "#ef4444"}, 'steps': [{'range': [0, 25], 'color': "#fee2e2"}, {'range': [25, 50], 'color': "#fef3c7"}, {'range': [50, 100], 'color': "#dcfce7"}]}))
        fig_gauge1.update_layout(height=250, margin=dict(l=20,r=20,t=40,b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='white' if st.session_state.dark_mode else 'black'))
        st.plotly_chart(fig_gauge1, use_container_width=True)
        st.caption(f"Formula: {' × '.join([f'{k}({v:.2f})' for k,v in breakdown.items()])} = {posg:.3f}")
    with col_gauge2:
        viability = float(a.get('commercial_viability_score', 0))
        fig_gauge2 = go.Figure(go.Indicator(mode="gauge+number", value=viability, title={'text': "Viability Score", 'font': {'size': 14, 'color': 'white' if st.session_state.dark_mode else 'black'}}, number={'suffix': "/100", 'font': {'size': 28, 'color': 'white' if st.session_state.dark_mode else 'black'}}, gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "#f59e0b"}, 'steps': [{'range': [0, 50], 'color': "#fee2e2"}, {'range': [50, 70], 'color': "#fef3c7"}, {'range': [70, 100], 'color': "#dcfce7"}]}))
        fig_gauge2.update_layout(height=250, margin=dict(l=20,r=20,t=40,b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='white' if st.session_state.dark_mode else 'black'))
        st.plotly_chart(fig_gauge2, use_container_width=True)
    with col_verdict:
        st.metric("Verdict", a.get('commercial_verdict', 'APPRAISE'))
        st.metric("AFC Flag", a.get('AFC_flag', 'Med'))
        st.metric("Model", model_used.split(' ')[0][:18])

    st.subheader("Petroleum System Confidence - Bar (Capped at 100)")
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=list(elements.keys()), y=[v["score"] for v in elements.values()], marker=dict(color=["#f59e0b","#fbbf24","#fde68a","#fb923c","#facc15"]), width=0.25, text=[f"{v['score']}/100" for v in elements.values()], textposition='outside', hovertemplate="%{x}: %{y}/100<br>Prob: %{customdata:.2f}<extra></extra>", customdata=[v["prob"] for v in elements.values()]))
    fig2.add_hline(y=70, line_dash="dash", line_color="#22c55e", annotation_text="Commercial Threshold 70")
    fig2.update_layout(yaxis=dict(range=[0,100], title="Confidence /100 - CAPPED AT 100"), height=380, bargap=0.6, showlegend=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='white' if st.session_state.dark_mode else 'black'))
    st.plotly_chart(fig2, use_container_width=True)
    st.markdown("**Key Phrases Commentary**")
    for k,v in elements.items():
        st.markdown(f"- **{k}** ({v['score']}/100, P={v['prob']:.2f}): {v.get('comment','')}")
    st.divider()
    st.subheader("Fluid & Formation")
    fluid = a.get("fluid_analysis", {})
    vol = a.get("volumetrics", {})
    prod = a.get("production_forecast", {})
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"- **Dominant Fluid:** {fluid.get('dominant_fluid', a.get('dominant_fluid','-'))}\n- **Oil Quality:** {fluid.get('oil_quality','-')}\n- **Gas Quality:** {fluid.get('gas_quality','-')}\n- **Pressure:** {a.get('formation_pressure','-')} ({a.get('pressure_gradient','-')})")
    with c2:
        st.markdown(f"- **STOIIP:** {vol.get('stoiip', a.get('stoiip','-'))}\n- **Recoverable Oil:** {vol.get('recoverable_oil', a.get('recoverable_oil','-'))}\n- **Initial Rate:** {prod.get('initial_rate', a.get('initial_rate','-'))}\n- **Field Life / Plateau:** {prod.get('field_life','-')} / {prod.get('plateau','-')}")
    st.subheader("Executive Summary")
    bg = "#1e293b" if st.session_state.dark_mode else "#f0fdf4"
    border = "#334155" if st.session_state.dark_mode else "#22c55e"
    text_color = "#e2e8f0" if st.session_state.dark_mode else "#14532d"
    summary = a.get('executive_summary','No summary available')
    st.markdown(f"<div style='background-color: {bg}; border-left: 4px solid {border}; padding: 12px 16px; border-radius: 6px; color: {text_color};'>{summary}</div>", unsafe_allow_html=True)
    st.subheader("Risk Factors")
    risks = a.get('risk_factors', [])
    if risks:
        for i, r in enumerate(risks, 1):
            st.markdown(f"{i}. {r}")
    else:
        st.caption("No risk factors returned")
    st.divider()
    pdf_buffer = create_executive_pdf(a, uploaded_file.name, posg_data, model_used)
    st.download_button(label="📄 Download Executive Report PDF v3.5 Production", data=pdf_buffer, file_name=f"PetroLens_Executive_v3_5_Production_{uploaded_file.name.split('.')[0]}_POSg{int(posg*100)}.pdf", mime="application/pdf", type="primary", use_container_width=True)
    st.caption(f"Model: {model_used} | POSg: {posg*100:.1f}% | File: {uploaded_file.name}")
except Exception as e:
    st.error(f"❌ Error during analysis: {e}")
    st.exception(e)
