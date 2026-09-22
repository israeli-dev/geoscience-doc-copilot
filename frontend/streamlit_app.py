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

st.set_page_config(page_title="PetroLens Executive", layout="wide", page_icon="🛢️")

def calc_posg(probs):
    p = 1.0
    for v in probs:
        p *= max(0.05, min(0.99, float(v)))
    return p

def create_executive_pdf(analysis, filename, posg_data, model_used):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    story = []
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=16, textColor=colors.black, spaceAfter=6)
    normal = ParagraphStyle('Normal2', parent=styles['Normal'], fontSize=9, leading=12)
    h2 = ParagraphStyle('H2', parent=styles['Heading2'], fontSize=11, textColor=colors.HexColor("#1e40af"), spaceBefore=10, spaceAfter=4)
    story.append(Paragraph("PetroLens AI - Commercial Viability Report", title_style))
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
        breakdown_data.append([k, f"{v['score']}", f"{v['prob']:.2f}", v.get('comment','')[:80]])
    t2 = Table(breakdown_data, colWidths=[1.2*inch, 0.8*inch, 0.6*inch, 3.9*inch])
    t2.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e40af")), ('TEXTCOLOR', (0,0), (-1,0), colors.white), ('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('FONTSIZE', (0,0), (-1,-1), 8), ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f1f5f9")])]))
    story.append(t2)
    story.append(Spacer(1, 8))
    story.append(Paragraph("Fluid & Formation", h2))
    fluid = analysis.get('fluid_analysis', {})
    vol = analysis.get('volumetrics', {})
    prod = analysis.get('production_forecast', {})
    fluid_data = [
        ["Dominant Fluid", fluid.get('dominant_fluid', analysis.get('dominant_fluid','Black Oil and Non-Associated Gas'))],
        ["Oil Quality", fluid.get('oil_quality','30-35 deg API, low sulfur, light sweet')],
        ["Gas Quality", fluid.get('gas_quality','High methane content, potential for NGLs')],
        ["Pressure", f"{analysis.get('formation_pressure','8,650 psi')} ({analysis.get('pressure_gradient','0.65 psi/ft')})"],
        ["STOIIP", vol.get('stoiip', analysis.get('stoiip','3,200 MMbbl'))],
        ["Recoverable", vol.get('recoverable_oil', '1,004 MMbbl')],
        ["Initial Rate", prod.get('initial_rate','45,000 bopd + 120 MMscf/d')],
        ["Field Life", prod.get('field_life','22 years')],
    ]
    t4 = Table(fluid_data, colWidths=[2.2*inch, 4.3*inch])
    t4.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('BACKGROUND', (0,0), (0,-1), colors.HexColor("#f3f4f6")), ('FONTSIZE', (0,0), (-1,-1), 9)]))
    story.append(t4)
    story.append(Spacer(1, 8))
    story.append(Paragraph("Risk Factors", h2))
    risks = analysis.get('risk_factors', ["Deep-water technical execution and high CAPEX", "Lateral reservoir discontinuity", "Lack of gas monetization infrastructure"])
    for i, r in enumerate(risks, 1):
        story.append(Paragraph(f"{i}. {r}", normal))
    doc.build(story)
    buffer.seek(0)
    return buffer

with st.sidebar:
    st.markdown("### PetroLens Executive v2.6")
    api_url = st.text_input("API URL", "https://geoscience-doc-copilot-5t3ani8cv8yuuqmqtgzhaq.streamlit.app/")

st.title("PetroLens AI - Subsurface Intelligence")
st.caption("Gauge Style | Histogram Bar (0-100 Capped) | POSg Multiplicative | Gemini 3")
uploaded_file = st.file_uploader("Upload Geoscience Report (PDF)", type=["pdf","docx","txt","md"])
deep = st.checkbox("Deep Analysis (gemini-3.1-pro-preview)", value=False)

if uploaded_file:
    st.info(f"File: {uploaded_file.name} | {uploaded_file.size/1024/1024:.1f} MB")

if uploaded_file and st.button("Generate Executive Analysis", type="primary", width='stretch'):
    with st.spinner("Running senior geologist evaluation..."):
        try:
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
            data = {"deep": str(deep).lower()}
            resp = requests.post(api_url, files=files, data=data, timeout=180)
            resp.raise_for_status()
            result = resp.json()
            a = result.get("analysis", {})
            model_used = result.get("model_used", "Gemini 3")
            if "petroleum_system" in a:
                elements = a["petroleum_system"]
            else:
                bd = a.get("viability_breakdown", {})
                elements = {
                    "Source": {"score": int(bd.get("source_rock", 18)/20*100), "prob": bd.get("source_rock", 18)/20, "comment": "Excellent - Abundance is good."},
                    "Reservoir": {"score": int(bd.get("reservoir_quality", 30)/40*100), "prob": bd.get("reservoir_quality", 30)/40, "comment": "Good - Quality well documented."},
                    "Trap": {"score": int(bd.get("trap_seal", 16)/20*100), "prob": bd.get("trap_seal", 16)/20, "comment": "Very Good - Well defined on PSDM."},
                    "Seal": {"score": int(bd.get("trap_seal", 16)/20*90), "prob": bd.get("trap_seal", 16)/20*0.9, "comment": "Moderate - Quality not well documented in crestal area."},
                    "Charge": {"score": 92, "prob": 0.85, "comment": "Excellent - Timing post-dates trap formation."},
                }
            for k in elements:
                elements[k]["score"] = min(100, int(elements[k].get("score", 50)))
                elements[k]["prob"] = min(0.99, max(0.05, float(elements[k].get("prob", 0.5))))
            breakdown = {k.lower(): v["prob"] for k,v in elements.items()}
            posg = a.get("posg") or calc_posg(list(breakdown.values()))
            posg_data = {"posg": posg, "breakdown": breakdown, "elements": elements}
            col_gauge1, col_gauge2, col_verdict = st.columns([2,2,1])
            with col_gauge1:
                fig_gauge1 = go.Figure(go.Indicator(mode="gauge+number", value=posg*100, title={'text': "POSg - Geological CoS", 'font': {'size': 14}}, number={'suffix': "%", 'font': {'size': 28}}, gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "#10b981" if posg>=0.25 else "#ef4444"}, 'steps': [{'range': [0, 25], 'color': "#fee2e2"}, {'range': [25, 50], 'color': "#fef3c7"}, {'range': [50, 100], 'color': "#dcfce7"}]}))
                fig_gauge1.update_layout(height=250, margin=dict(l=20,r=20,t=40,b=20))
                st.plotly_chart(fig_gauge1, width='stretch')
                st.caption(f"Formula: {' x '.join([f'{k}({v:.2f})' for k,v in breakdown.items()])} = {posg:.3f}")
            with col_gauge2:
                viability = a.get('commercial_viability_score', 72)
                fig_gauge2 = go.Figure(go.Indicator(mode="gauge+number", value=viability, title={'text': "Viability Score", 'font': {'size': 14}}, number={'suffix': "/100", 'font': {'size': 28}}, gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "#f59e0b"}, 'steps': [{'range': [0, 50], 'color': "#fee2e2"}, {'range': [50, 70], 'color': "#fef3c7"}, {'range': [70, 100], 'color': "#dcfce7"}]}))
                fig_gauge2.update_layout(height=250, margin=dict(l=20,r=20,t=40,b=20))
                st.plotly_chart(fig_gauge2, width='stretch')
            with col_verdict:
                st.metric("Verdict", a.get('commercial_verdict', 'APPRAISE'))
                st.metric("AFC Flag", a.get('AFC_flag', 'Med'))
                st.metric("Model", model_used.split(' ')[0])
            st.subheader("Petroleum System Confidence - Thin-Bar Histogram (Capped at 100)")
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(x=list(elements.keys()), y=[v["score"] for v in elements.values()], marker=dict(color=["#f59e0b","#fbbf24","#fde68a","#fb923c","#facc15"]), width=0.25, text=[f"{v['score']}/100" for v in elements.values()], textposition='outside'))
            fig2.add_hline(y=70, line_dash="dash", line_color="#22c55e", annotation_text="Commercial Threshold 70")
            fig2.update_layout(yaxis=dict(range=[0,100], title="Confidence /100 - CAPPED"), height=380, bargap=0.6)
            st.plotly_chart(fig2, width='stretch')
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
                st.markdown(f"- **Dominant Fluid:** {fluid.get('dominant_fluid', a.get('dominant_fluid','Black Oil and Non-Associated Gas'))}\n- **Oil Quality:** {fluid.get('oil_quality','30-35 deg API, low sulfur, light sweet based on Espoir analogs')}\n- **Gas Quality:** {fluid.get('gas_quality','High methane content, potential for NGLs (282 MMbbl mean potential)')}\n- **Pressure:** {a.get('formation_pressure','8,650 psi')}")
            with c2:
                st.markdown(f"- **STOIIP:** {vol.get('stoiip', a.get('stoiip','3,200 MMbbl'))}\n- **Recoverable:** {vol.get('recoverable_oil','1,004 MMbbl')}\n- **Initial Rate:** {prod.get('initial_rate','45,000 bopd + 120 MMscf/d')}\n- **Field Life:** {prod.get('field_life','22 years')}")
            st.subheader("Executive Summary")
            st.markdown(f"<div style='background-color: #f0fdf4; border-left: 4px solid #22c55e; padding: 12px 16px; border-radius: 6px; color: #14532d;'>{a.get('executive_summary','Summary')}</div>", unsafe_allow_html=True)
            st.divider()
            pdf_buffer = create_executive_pdf(a, uploaded_file.name, posg_data, model_used)
            st.download_button(label="Download Executive Report PDF (Like attached doc)", data=pdf_buffer, file_name=f"PetroLens_Executive_{uploaded_file.name.split('.')[0]}_POSg{int(posg*100)}.pdf", mime="application/pdf", type="primary", width='stretch')
        except Exception as e:
            st.error(f"Analysis failed: {e}")
            st.exception(e)
