"""Streamlit frontend for Supplier Sourcing Agent."""
from __future__ import annotations

import os
import time

import pandas as pd
import plotly.express as px
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Supplier Sourcing Agent",
    page_icon="🏭",
    layout="wide",
)

# ---------- Header ----------
st.title("🏭 Supplier & Product Sourcing Agent")
st.caption("16-agent LangGraph pipeline · Alibaba · IndiaMART · GlobalSources · 1688")

# ---------- Sidebar: Spec input ----------
with st.sidebar:
    st.header("📋 Product Spec")
    product_name = st.text_input("Product name", "Eco-friendly bamboo toothbrush")
    description = st.text_area("Description", "Adult bamboo toothbrush with soft nylon bristles, biodegradable handle.")
    moq = st.number_input("MOQ (units)", min_value=1, value=500)
    target_price = st.number_input("Target price / unit", min_value=0.01, value=0.80, step=0.05, format="%.2f")
    currency = st.selectbox("Currency", ["USD", "EUR", "GBP", "INR"], index=0)
    certs_str = st.text_input("Certifications (comma-separated)", "FSC, FDA")
    ship_to = st.selectbox("Ship to", ["US", "DE", "UK", "FR", "IN", "CA", "AU", "JP", "BR"], index=1)
    timeline = st.number_input("Timeline (days)", min_value=7, value=30)

    st.divider()
    start_btn = st.button("🚀 Find Suppliers", type="primary", use_container_width=True)


def _start_job() -> str | None:
    payload = {
        "spec": {
            "product_name": product_name,
            "description": description,
            "moq": int(moq),
            "target_price": float(target_price),
            "currency": currency,
            "certifications": [c.strip() for c in certs_str.split(",") if c.strip()],
            "ship_to_country": ship_to,
            "timeline_days": int(timeline),
        }
    }
    try:
        r = requests.post(f"{BACKEND_URL}/jobs", json=payload, timeout=10)
        r.raise_for_status()
        return r.json()["job_id"]
    except Exception as e:
        st.error(f"Failed to start job: {e}")
        return None


def _poll(job_id: str) -> dict | None:
    try:
        r = requests.get(f"{BACKEND_URL}/jobs/{job_id}", timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Poll failed: {e}")
        return None


# ---------- Run ----------
if start_btn:
    job_id = _start_job()
    if job_id:
        st.session_state["job_id"] = job_id
        st.session_state["job_done"] = False

job_id = st.session_state.get("job_id")

if job_id and not st.session_state.get("job_done"):
    st.subheader(f"⚙️ Running job `{job_id}`")
    progress_bar = st.progress(0)
    status_box = st.empty()
    log_box = st.empty()

    while True:
        job = _poll(job_id)
        if not job:
            break
        progress_bar.progress(job["progress"] / 100)
        status_box.info(f"**Stage:** `{job['current_stage']}`  ·  Progress: {job['progress']}%")
        log_box.code("\n".join(job["log"][-8:]) or "...")
        if job["status"] in ("done", "error"):
            st.session_state["job_done"] = True
            st.session_state["job_data"] = job
            break
        time.sleep(1.2)

# ---------- Results ----------
if st.session_state.get("job_done"):
    job = st.session_state["job_data"]
    if job["status"] == "error":
        st.error(f"Job failed: {job.get('error')}")
    else:
        st.success(f"✅ Done — {len(job['suppliers'])} suppliers vetted")
        suppliers = sorted(job["suppliers"], key=lambda x: x["rank"])
        spec = job["spec"]

        tab1, tab2, tab3, tab4 = st.tabs(
            ["📊 Decision Matrix", "🏆 Top Suppliers", "✉️ Inquiry Emails", "📥 Download"]
        )

        with tab1:
            df = pd.DataFrame([
                {
                    "Rank": s["rank"],
                    "Supplier": s["name"],
                    "Platform": s["platform"],
                    "Country": s["country"],
                    "Trust": s["trust_score"],
                    "Final": s["final_score"],
                    "Quoted": s["quoted_price"],
                    "Landed": s["landed_cost"],
                    "MOQ": s["moq"],
                    "Lead (d)": s["lead_time_days"],
                    "Cert ✓": "✅" if s["cert_verified"] else "❌",
                    "Flags": len(s["red_flags"]),
                }
                for s in suppliers
            ])
            st.dataframe(df, use_container_width=True, hide_index=True)

            col1, col2 = st.columns(2)
            with col1:
                fig = px.scatter(
                    df, x="Landed", y="Trust", size="Final", color="Platform",
                    hover_name="Supplier", title="Trust vs Landed Cost",
                )
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                top10 = df.head(10)
                fig2 = px.bar(top10, x="Supplier", y="Final", color="Platform", title="Top 10 — Final Score")
                fig2.update_layout(xaxis_tickangle=-35, xaxis_title=None)
                st.plotly_chart(fig2, use_container_width=True)

        with tab2:
            for s in suppliers[:10]:
                with st.expander(f"#{s['rank']}  {s['name']}  —  {s['country']}  ·  score {s['final_score']}"):
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Trust", f"{s['trust_score']}/100")
                    c2.metric("Quoted", f"${s['quoted_price']:.2f}")
                    c3.metric("Landed", f"${s['landed_cost']:.2f}")
                    c4.metric("MOQ", s["moq"])

                    st.write(f"**Years active:** {s['years_active']}  ·  **Response rate:** {int(s['response_rate']*100)}%  ·  **Reviews:** {s['review_count']} (★ {s['avg_rating']})")
                    st.write(f"**Certifications:** {', '.join(s['certifications']) or '—'}  ·  **Verified for spec:** {'✅' if s['cert_verified'] else '❌'}")
                    if s["red_flags"]:
                        st.warning("🚩 " + " · ".join(s["red_flags"]))
                    st.markdown(f"**Negotiation strategy:** {s['negotiation_strategy']}")
                    bd = s["landed_cost_breakdown"]
                    if bd:
                        st.caption(
                            f"FOB ${bd.get('fob',0):.2f} + Shipping ${bd.get('shipping_per_unit',0):.2f} + "
                            f"Duty ${bd.get('duty',0):.2f} + VAT ${bd.get('vat',0):.2f} = **${bd.get('total',0):.2f}**"
                        )

        with tab3:
            for s in suppliers[:10]:
                if not s["inquiry_email"]:
                    continue
                with st.expander(f"✉️ #{s['rank']}  {s['name']}  →  {s['contact_email']}"):
                    st.text_area("Email body", value=s["inquiry_email"], height=240, key=f"em_{s['id']}")
                    st.markdown("**Sample request:**")
                    st.code(s["sample_request"])

        with tab4:
            st.write("Download a ZIP containing PDF report, CSV of all suppliers, and one .txt per inquiry email.")
            if st.button("📦 Build & Download Report ZIP", type="primary"):
                try:
                    r = requests.get(f"{BACKEND_URL}/jobs/{job['job_id']}/report", timeout=30)
                    r.raise_for_status()
                    st.download_button(
                        "⬇️ Download sourcing_report.zip",
                        data=r.content,
                        file_name=f"sourcing_{job['job_id']}.zip",
                        mime="application/zip",
                    )
                except Exception as e:
                    st.error(f"Failed: {e}")
else:
    if not job_id:
        st.info("👈 Enter a product spec in the sidebar and click **Find Suppliers** to start.")
        st.markdown(
            """
            ### How it works
            1. **SpecParser** normalises your input (HS code, materials)
            2. **4 Sourcer agents** search Alibaba / IndiaMART / GlobalSources / Made-in-China in parallel
            3. **5 Vetting agents** score trust, sentiment, certs, red flags, compliance
            4. **6 Negotiation agents** benchmark prices, draft culturally-tuned emails, compute landed cost, rank top 10
            5. Download a ZIP report with PDF + CSV + per-supplier email drafts
            """
        )
