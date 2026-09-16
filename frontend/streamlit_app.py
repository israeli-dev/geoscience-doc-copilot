import streamlit as st
import requests
import plotly.graph_objects as go
import os

BACKEND_URL = "http://127.0.0.1:8001/api/upload-report"

st.set_page_config(page_title="PetroLens AI", layout="wide", page_icon="🛢")
st.title("🛢 PetroLens AI - Reservoir Viability Engine")
st.caption("AI Petroleum Geologist for Niger Delta Prospects | FastAPI + Gemini 3 Flash")

with st.sidebar:
    st.header("How it works")
    st.write("1. Upload Agbada/Akata report (PDF)")
    st.write("2. AI extracts porosity, perm, TOC, trap")
    st.write("3. Applies commercial cutoff logic")
    st.write("4. Returns Viability Score 0-100")
    st.divider()
    BACKEND_URL = st.text_input("Backend URL", value=BACKEND_URL, help="Change to your Render URL when deployed")
    st.code("FastAPI + Gemini 3 + PyMuPDF", language="text")

uploaded_file = st.file_uploader("Upload Geoscience Report (PDF)", type=["pdf"])

if uploaded_file:
    with st.spinner("PetroLens is evaluating prospect..."):
        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
        try:
            response = requests.post(BACKEND_URL, files=files, timeout=90)
            response.raise_for_status()
            data = response.json()
            analysis = data["analysis"]
            score = int(analysis.get("commercial_viability_score", 0))
            verdict = analysis.get("commercial_verdict", "UNKNOWN")

            col1, col2 = st.columns([1, 1.5])
            with col1:
                color = "green" if score >= 70 else "orange" if score >= 45 else "red"
                fig = go.Figure(go.Indicator(
                    mode="gauge+number", value=score,
                    title={'text': f"Viability: {verdict}"},
                    gauge={'axis': {'range': [0, 100]}, 'bar': {'color': color},
                           'steps': [{'range': [0, 45], 'color': "#ffcccc"},
                                     {'range': [45, 70], 'color': "#fff3cd"},
                                     {'range': [70, 100], 'color': "#d4edda"}]}))
                st.plotly_chart(fig, use_container_width=True)
                st.metric("Pages Processed", data["pages"])
                st.metric("Chars Extracted", data["characters_extracted"])

            with col2:
                st.subheader("Commercial Score Breakdown")
                breakdown = analysis.get("viability_breakdown", {})
                for k, v in breakdown.items():
                    st.progress(int(v), text=f"{k.replace('_',' ').title()}: {v}")

                st.subheader("Key Extracted Parameters")
                st.json({
                    "Porosity": analysis.get("reservoir_quality", {}).get("porosity"),
                    "Permeability": analysis.get("reservoir_quality", {}).get("permeability"),
                    "TOC": analysis.get("source_rock", {}).get("TOC"),
                    "Trap Type": analysis.get("trap", {}).get("type"),
                    "AFC Flag": analysis.get("AFC_flag")
                })
                st.subheader("Risk Factors")
                for r in analysis.get("risk_factors", []):
                    st.write(f"- {r}")
                st.subheader("Executive Summary")
                st.write(analysis.get("executive_summary"))

        except Exception as e:
            st.error(f"Backend error: {e}\nCheck if backend is running at {BACKEND_URL}")