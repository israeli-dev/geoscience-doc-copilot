"""
PetroLens Executive v3.4 PRODUCTION
- Production project (not student defense)
- Barrel logo in title, API address removed (hardcoded), clean UI no "real"/"hallucination"
- Matches backend v3.4: 150k chars, 8192 tokens, separate models, max 2 retries
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

st.set_page_config(page_title="PetroLens Executive v3.4 Production", layout="wide", page_icon="🛢️")

# ----------------- PRODUCTION CONFIG - NO API INPUT -----------------
API_URL = "https://geoscience-doc-copilot.onrender.com/api/upload-report"
# For Cloud Run $300 credit, change to: https://geoscience-doc-copilot-xxxx-uc.a.run.app/api/upload-report

# ----------------- CORE CALCULATIONS -----------------
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
        "Source": {"score": int(min(100, (bd.get("source_rock", 18)/20)*100)), "prob": min(0.99, max(0.05, bd.get("source_rock", 18)/20)), "comment": "Source rock presence & maturity from report.", "detail": ""},
        "Reservoir": {"score": int(min(100, (bd.get("reservoir_quality", 30)/40)*100)), "prob": min(0.99, max(0.05, bd.get("reservoir_quality", 30)/40)), "comment": "Reservoir quality, porosity/permeability.", "detail": ""},
        "Trap": {"score": int(min(100, (bd.get("trap_seal", 16)/20)*100)), "prob": min(0.99, max(0.05, bd.get("trap_seal", 16)/20)), "comment": "Trap geometry defined on seismic.", "detail": ""},
        "Seal": {"score": int(min(100, (bd.get("trap_seal", 16)/20)*90)), "prob": min(0.99, max(0.05, (bd.get("trap_seal", 16)/20)*0.9)), "comment": "Seal capacity and integrity.", "detail": ""},
        "Charge": {"score": 85, "prob": 0.82, "comment": "Charge timing vs trap formation.", "detail": ""},
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
    story.append(Paragraph("PetroLens - Commercial Viability Report v3.4 Production", title_style))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | File: {filename} | Model: {model_used} | POSg: {posg_data['posg']*100:.1f}%", normal))
    story.append(Spacer(1, 8))
    viability_data = [
        ["Viability Score", f"{analysis.get('commercial_viability_score', 0)}/100"],
        ["Verdict", analysis.get('commercial_verdict', 'APPRAISE')],
        ["AFC Flag", analysis.get('AFC_flag', 'Med')],
        ["POSg (Geological CoS)", f"{posg_data['posg']*100:.1f}% = {' x '.join([f'{k}({v:.2f})' for k,v in posg_data['breakdown'].items()])}"]
    ]
    t = Table(viability_data, colWidths=[2.2*inch, 4.3*inch])
    t.setStyle(TableStyle([('BACKGROUND', (0,0), (0,-1), colors.HexColor("#e0e7ff")), ('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('FONTSIZE', (0,0), (-1,-1), 9), ('PADDING', (0,0), (-1,-1), 6)]))
    story.append(t)
    story.append(Spacer(1, 10))
    story.append(Paragraph("Executive Summary", h2))
    story.append(Paragraph(analysis.get('executive_summary', 'No summary available'), normal))
    story.append(Spacer(1, 8))
    story.append(Paragraph("Viability Breakdown / Petroleum System Confidence (0-100 Capped)", h2))
    breakdown_data = [["Component", "Score /100", "Prob", "Comment"]]
    for k,v in posg_data['elements'].items():
        breakdown_data.append([k, f"{v['score']}", f"{v['prob']:.2f}", v.get('comment','')[:90]])
    t2 = Table(breakdown_data, colWidths=[1.2*inch, 0.8*inch, 0.6*inch, 3.9*inch])
    t2.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e40af")), ('TEXTCOLOR', (0,0), (-1,0), colors.white), ('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('FONTSIZE', (0,0), (-1,-1), 8), ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f1f5f9")])]))
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
        ["STOIIP", vol.get('stoiip', analysis.get('stoiip','-'))],
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

# ----------------- SIDEBAR - PRODUCTION -----------------
with st.sidebar:
    st.markdown("### 🛢️ PetroLens Executive v3.4")
    st.caption("Production - Subsurface Intelligence")
    st.divider()
    st.markdown("**Petroleum System Analysis:**")
    st.info("• Source, Reservoir, Trap, Seal, Charge\n• POSg Multiplicative (Rose 1987)\n• Commercial Viability\n• Volumetrics & Forecast")
    st.divider()
    st.markdown("**Models**")
    st.caption("Flash: `gemini-3-flash-preview` (20/day free)\n\nPro: `gemini-3.1-pro-preview` (requires billing)")
    st.divider()
    st.caption("Build: 2026-09-24 • Production v3.4")

# ----------------- MAIN - BARREL LOGO LIKE OLD UI -----------------
st.title("🛢️ PetroLens - Subsurface Intelligence")
st.caption("v3.4 Production | Commercial Viability Gauge | POSg Multiplicative (Rose 1987) | Executive Reporting")

uploaded_file = st.file_uploader("Upload Geoscience Report (PDF/DOCX/TXT/MD)", type=["pdf","docx","txt","md"])
deep = st.checkbox("Deep Analysis (gemini-3.1-pro-preview)", value=False, help="Pro model only for deep business decision. Requires paid billing. Keep UNCHECKED for free-tier.")

if uploaded_file:
    st.info(f"📄 File: {uploaded_file.name} | Size: {uploaded_file.size/1024/1024:.2f} MB")

if uploaded_file and st.button("🚀 Generate Executive Analysis", type="primary", use_container_width=True):
    with st.spinner("Running petroleum system evaluation... (cold start 50s + analysis 30s). Please wait..."):
        try:
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type or "application/octet-stream")}
            data = {"deep": str(deep).lower()}
            try:
                resp = requests.post(API_URL, files=files, data=data, timeout=180)
            except requests.exceptions.ReadTimeout:
                st.error("⏱ Request timed out (cold start >100s)")
                st.markdown(f"1. Open **{API_URL.replace('/api/upload-report','')}** in new tab → Wait 30s\n2. Come back and click Generate again\n3. Add UptimeRobot ping every 5 min to keep service awake")
                st.stop()
            except requests.exceptions.ConnectionError as ce:
                st.error(f"🔌 Cannot reach backend")
                st.code(str(ce)[:500])
                st.stop()

            if resp.status_code == 429:
                try:
                    err_json = resp.json()
                    err_detail = err_json.get("detail", str(err_json)[:800])
                except:
                    err_detail = resp.text[:800]
                st.error("🚫 Quota Exceeded - 429")
                st.code(err_detail)
                st.warning("Free tier: 20/day. Wait 60s, create new project for 20 more, or enable billing for 1500/day. Resets 8am Lagos.")
                st.stop()
            if resp.status_code == 503:
                st.error("🔥 Service temporarily unavailable (503)")
                st.info("Wait 30-60 seconds and click Generate again.")
                st.stop()
            if resp.status_code >= 400:
                st.error(f"❌ Backend returned {resp.status_code}")
                try:
                    st.json(resp.json())
                except:
                    st.code(resp.text[:2000])
                st.stop()

            resp.raise_for_status()
            result = resp.json()
            a = result.get("analysis", {})
            if a.get("is_oil_gas_document") == False:
                st.error(f"🚫 REJECTED - Not Oil & Gas Document")
                st.write(f"**Detected Type:** {a.get('document_type_detected', 'Unknown')}")
                st.write(f"**Reason:** {a.get('rejection_reason') or a.get('executive_summary') or 'Not a petroleum geoscience report'}")
                st.info("Upload a geoscience report (well report, reservoir study, seismic interpretation).")
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
                        score = int(prob*100)
                        elements[key_cap] = {"score": score, "prob": prob, "comment": f"{key_cap} confidence from report", "detail": ""}
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
                fig_gauge1 = go.Figure(go.Indicator(
                    mode="gauge+number", value=posg*100, title={'text': "POSg - Geological CoS", 'font': {'size': 14}}, 
                    number={'suffix': "%", 'font': {'size': 28}}, 
                    gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "#10b981" if posg>=0.25 else "#ef4444"}, 'steps': [{'range': [0, 25], 'color': "#fee2e2"}, {'range': [25, 50], 'color': "#fef3c7"}, {'range': [50, 100], 'color': "#dcfce7"}]}))
                fig_gauge1.update_layout(height=250, margin=dict(l=20,r=20,t=40,b=20))
                st.plotly_chart(fig_gauge1, use_container_width=True)
                st.caption(f"Formula: {' × '.join([f'{k}({v:.2f})' for k,v in breakdown.items()])} = {posg:.3f}")
            with col_gauge2:
                viability = float(a.get('commercial_viability_score', 0))
                fig_gauge2 = go.Figure(go.Indicator(
                    mode="gauge+number", value=viability, title={'text': "Viability Score", 'font': {'size': 14}}, 
                    number={'suffix': "/100", 'font': {'size': 28}}, 
                    gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "#f59e0b"}, 'steps': [{'range': [0, 50], 'color': "#fee2e2"}, {'range': [50, 70], 'color': "#fef3c7"}, {'range': [70, 100], 'color': "#dcfce7"}]}))
                fig_gauge2.update_layout(height=250, margin=dict(l=20,r=20,t=40,b=20))
                st.plotly_chart(fig_gauge2, use_container_width=True)
            with col_verdict:
                st.metric("Verdict", a.get('commercial_verdict', 'APPRAISE'))
                st.metric("AFC Flag", a.get('AFC_flag', 'Med'))
                st.metric("Model", model_used.split(' ')[0][:18])

            st.subheader("Petroleum System Confidence - Bar (Capped at 100)")
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                x=list(elements.keys()), y=[v["score"] for v in elements.values()], 
                marker=dict(color=["#f59e0b","#fbbf24","#fde68a","#fb923c","#facc15"]), width=0.25, 
                text=[f"{v['score']}/100" for v in elements.values()], textposition='outside',
                hovertemplate="%{x}: %{y}/100<br>Prob: %{customdata:.2f}<extra></extra>",
                customdata=[v["prob"] for v in elements.values()]))
            fig2.add_hline(y=70, line_dash="dash", line_color="#22c55e", annotation_text="Commercial Threshold 70")
            fig2.update_layout(yaxis=dict(range=[0,100], title="Confidence /100 - CAPPED AT 100"), height=380, bargap=0.6, showlegend=False)
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
            summary = a.get('executive_summary','No summary available')
            st.markdown(f"<div style='background-color: #f0fdf4; border-left: 4px solid #22c55e; padding: 12px 16px; border-radius: 6px; color: #14532d;'>{summary}</div>", unsafe_allow_html=True)
            st.subheader("Risk Factors")
            risks = a.get('risk_factors', [])
            if risks:
                for i, r in enumerate(risks, 1):
                    st.markdown(f"{i}. {r}")
            else:
                st.caption("No risk factors returned")
            st.divider()
            pdf_buffer = create_executive_pdf(a, uploaded_file.name, posg_data, model_used)
            st.download_button(label="📄 Download Executive Report PDF v3.4 Production", data=pdf_buffer, file_name=f"PetroLens_Executive_v3_4_Production_{uploaded_file.name.split('.')[0]}_POSg{int(posg*100)}.pdf", mime="application/pdf", type="primary", use_container_width=True)
            st.caption(f"Model: {model_used} | POSg: {posg*100:.1f}% | File: {uploaded_file.name}")
        except Exception as e:
            st.error(f"❌ Error during analysis: {e}")
            st.exception(e)
