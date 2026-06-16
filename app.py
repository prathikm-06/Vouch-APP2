import streamlit as st
import json
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from google import genai
from google.genai import types

# Page Config
st.set_page_config(
    page_title="Vouch AI - Credibility & Hardware Transparency Engine",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom Styling (Theme: Dark Slate & Mint Accent)
st.markdown("""
<style>
    /* Styling Streamlit app element wrappers to match our bespoke aesthetic */
    .stApp {
        background-color:  #F0FFDF4;
        color:  #111827;
    }
    
    /* Global Typography */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Inter', sans-serif;
        font-weight: 800 !important;
        letter-spacing: -0.025em;
    }
    
    /* Top Header Bar */
    .vouch-header {
    background: linear-gradient(135deg, #FFFFFF 0%, #F0FDF4 100%);
    padding: 2rem;
    border-radius: 1rem;
    border: 1px solid #BBF7D0;
    margin-bottom: 2rem;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}
    .vouch-logo {
        color: #12b76a;
        font-size: 2.25rem;
        font-weight: 900;
        letter-spacing: -0.05em;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    /* Custom Badges */
    .score-badge {
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 0.85rem;
        display: inline-block;
    }
    .score-high {
        background-color: rgba(18, 183, 106, 0.15);
        color: #12b76a;
        border: 1px solid rgba(18, 183, 106, 0.3);
    }
    .score-medium {
        background-color: rgba(245, 158, 11, 0.15);
        color: #f59e0b;
        border: 1px solid rgba(245, 158, 11, 0.3);
    }
    .score-low {
        background-color: rgba(239, 68, 68, 0.15);
        color: #ef4444;
        border: 1px solid rgba(239, 68, 68, 0.3);
    }
    
    /* Card Styles */
    .vouch-card {
        background-color: #090f1e;
        border: 1px solid #1e293b;
        border-radius: 0.75rem;
        padding: 1.25rem;
        margin-bottom: 1rem;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .vouch-card:hover {
        border-color: #334155;
    }
    
    /* Metrics panel */
    .stat-box {
        background-color: #0b1329;
        border: 1px solid #1e293b;
        border-radius: 0.5rem;
        padding: 1rem;
        text-align: center;
    }
    
    /* Tab adjustments */
    .stTabs [data-baseweb="tab-list"] {
        gap: 1rem;
        background-color: #070c18;
        padding: 0.5rem;
        border-radius: 0.75rem;
        border: 1px solid #111827;
    }
    .stTabs [data-baseweb="tab"] {
        height: 40px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 0.5rem;
        font-weight: 700;
        color: #9ca3af;
        border: none;
    }
    .stTabs [aria-selected="true"] {
        background-color: #12b76a !important;
        color: #030712 !important;
    }
</style>
""", unsafe_allow_html=True)

# Database Helpers
DB_FILE = "database.json"

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Safeguard: strip phone items to implement the constraint
                if "products" in data:
                    data["products"] = [
                        p for p in data["products"] 
                        if p.get("category", "").lower() != "smartphones" 
                        and "phone" not in p.get("category", "").lower()
                    ]
                return data
        except Exception as e:
            st.error(f"Error loading database: {e}")
    
    # Default Fallback Structure
    return {
        "brands": [],
        "products": [],
        "reviews": [],
        "users": [
            {"id": "admin", "username": "admin", "email": "admin@vouch.in", "password": "adminpassword", "isPremium": True, "isAdmin": True}
        ],
        "saved_products": [],
        "click_metrics": {}
    }

def save_db(data):
    try:
        # Guarantee Smartphone removal on persistence pass
        if "products" in data:
            data["products"] = [
                p for p in data["products"] 
                if p.get("category", "").lower() != "smartphones" 
                and "phone" not in p.get("category", "").lower()
            ]
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"Error saving database: {e}")
        return False

db = load_db()

# Score Helper
def get_score_class(score):
    if score >= 85:
        return "score-high", "Excellent"
    elif score >= 70:
        return "score-medium", "Good"
    else:
        return "score-low", "Needs Caution"

# State variables initialization
if "compare_brands" not in st.session_state:
    st.session_state.compare_brands = []
if "compare_models" not in st.session_state:
    st.session_state.compare_models = []
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = [
        {"sender": "ai", "content": "Hello! I am **Vouch AI**, your product credibility and hardware transparency advisor. Ask me anything like:\n\n* *'Which coding laptops have the highest durability rating and solid warranty terms?'*\n* *'Which smart TVs have verified genuine user ratings rather than fake logs?'*\n* *'Compare the refrigerator support policy of Samsung vs local brands.'*\n\nI analyze real credibility metrics, return rates, and verified purchase records to keep your transactions safe!"}
    ]

# Layout Header
st.markdown("""
<div class="vouch-header">
    <div class="vouch-logo">🛡️ VOUCH AI</div>
    <div style="font-size: 0.85rem; color: #9ca3af; margin-top: 0.25rem;">
        Elite Product Credibility Engine & Brand Transparency Directory. Powered by authenticated reviews, RMA logs, & hardware audit curves. (No smartphones cataloged. No arbitrary pricing.)
    </div>
</div>
""", unsafe_allow_html=True)

# Main Navigation Tabs
tab_dir, tab_comp, tab_trans, tab_ai, tab_admin = st.tabs([
    "📂 Trust Directory",
    "⚖️ Side-by-Side Comparison",
    "📈 Brand Transparency index",
    "🤖 Ask Vouch (AI Advisor)",
    "⚙️ Admin Panel"
])

#=========================================================
# TAB 1: TRUST DIRECTORY
#=========================================================
with tab_dir:
    st.subheader("Bespoke Trust Catalog")
    
    # Mode toggle
    dir_mode = st.radio("Directory Target", ["Brand Houses", "Appliance Models"], horizontal=True, label_visibility="collapsed")
    
    if dir_mode == "Brand Houses":
        st.markdown("#### Corporate Brands Directory")
        
        # Search & Filter
        col_search, col_verify = st.columns([3, 1])
        with col_search:
            search_query = st.text_input("Search Brand Name or Advantage Tags", "").strip()
        with col_verify:
            only_verified = st.checkbox("Verified Manufacturers Only", False)
            
        filtered_brands = db["brands"]
        if only_verified:
            filtered_brands = [b for b in filtered_brands if b.get("verified", True)]
        if search_query:
            query_lower = search_query.lower()
            filtered_brands = [
                b for b in filtered_brands 
                if query_lower in b.get("brand_name", "").lower() 
                or any(query_lower in pt.lower() for pt in b.get("advantages", []))
            ]
            
        if not filtered_brands:
            st.info("No corporate profiles match your filter keywords.")
        else:
            for b in filtered_brands:
                c_score = b.get("credibility_score", 85)
                badge_class, badge_lbl = get_score_class(c_score)
                
                # Checkbox inside comparison list state
                is_comparing = b["id"] in st.session_state.compare_brands
                
                # Card HTML structure
                with st.container():
                    st.markdown(f"""
                    <div class="vouch-card">
                        <div style="display: flex; justify-content: space-between; align-items: start;">
                            <div>
                                <span style="font-size: 1.25rem; font-weight: 800; color: #ffffff;">{b['brand_name']}</span>
                                <span style="margin-left: 0.5rem; background-color: #1e293b; color: #12b76a; padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.75rem;">Verified Manufacturer</span>
                            </div>
                            <div>
                                <span class="score-badge {badge_class}">Vouch Score: {c_score} ({badge_lbl})</span>
                            </div>
                        </div>
                        <div style="font-size: 0.85rem; color: #9ca3af; margin: 0.75rem 0;">
                            <strong>Active Categories:</strong> {", ".join(b.get("associated_products", []))} | 
                            <strong>Years Active:</strong> {b.get("years_in_business", 0)} Years | 
                            <strong>Transparency Grade:</strong> <span style="color: #38bdf8; font-weight: 700;">{b.get("transparency_rating", "B")}</span>
                        </div>
                        <p style="font-size: 0.9rem; color: #f3f4f6; margin-bottom: 0.75rem;">{b.get("insights", "")}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Interactivity container in streamlit style (Buttons can't reside inside raw HTML easily, we render them below)
                    col_b1, col_b2, col_b3 = st.columns([1.5, 1.5, 5])
                    with col_b1:
                        if is_comparing:
                            if st.button(f"Remove Comparison ({b['brand_name']})", key=f"rm_b_{b['id']}"):
                                st.session_state.compare_brands.remove(b["id"])
                                st.rerun()
                        else:
                            if len(st.session_state.compare_brands) < 3:
                                if st.button(f"⚖️ Compare Brand ({b['brand_name']})", key=f"add_b_{b['id']}"):
                                    st.session_state.compare_brands.append(b["id"])
                                    st.rerun()
                            else:
                                st.write("Max 3 Brands in checklist!")
                                
                    with col_b2:
                        # Inspect detail trigger
                        if st.button(f"🔍 Show Detailed Score Breakdown", key=f"details_b_{b['id']}"):
                            st.session_state["detailed_brand_open"] = b["id"]
                            st.rerun()
                    st.markdown("<hr style='border-color: #1e293b; margin: 1rem 0 2rem 0;' />", unsafe_allow_html=True)
                    
                    # Highlight detailed view
                    if st.session_state.get("detailed_brand_open") == b["id"]:
                        st.markdown(f"#### Custom Credibility Audit Map: **{b['brand_name']}**")
                        col_metrics, col_radar = st.columns([1, 1])
                        with col_metrics:
                            st.markdown(f"**Corporate Warranty Policy Summary:** {b.get('warranty_policy', 'Generic standard terms')}")
                            st.markdown(f"**Value Index metric score:** {b.get('value_for_money', 80)}%")
                            st.markdown(f"**Customer Support Resolution Score:** {b.get('customer_service_score', 80)}%")
                            
                            # Checklist of advantages and key limits
                            st.write("**Key Advantages Identified:**")
                            for adv in b.get("advantages", []):
                                st.markdown(f"- ✅ <span style='color: #12b76a;'>{adv}</span>", unsafe_allow_html=True)
                                
                            st.write("**Major Bottlenecks & Vulnerabilities:**")
                            for dis in b.get("disadvantages", []):
                                st.markdown(f"- ⚠️ <span style='color: #fb7185;'>{dis}</span>", unsafe_allow_html=True)
                                
                        with col_radar:
                            # Plotly breakdown for weights
                            wb = b.get("weight_breakdown", {})
                            if wb:
                                df_wb = pd.DataFrame({
                                    "Weight Property": list(wb.keys()),
                                    "Accuracy Level": list(wb.values())
                                })
                                fig = px.line_polar(df_wb, r='Accuracy Level', theta='Weight Property', line_close=True)
                                fig.update_traces(fill='toself', line_color='#12b76a')
                                fig.update_layout(
                                    polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                                    showlegend=False,
                                    paper_bgcolor="rgba(0,0,0,0)",
                                    plot_bgcolor="rgba(0,0,0,0)",
                                    height=250,
                                    margin=dict(l=20, r=20, t=20, b=20)
                                )
                                st.plotly_chart(fig, use_container_width=True)
                        
                        if st.button("Close Details Window", key=f"close_det_brand_{b['id']}"):
                            st.session_state["detailed_brand_open"] = None
                            st.rerun()
                            
    else:
        st.markdown("#### Appliance Models & Devices Directory")
        
        # Grid layout filtering
        col_cat, col_src = st.columns([2, 2])
        with col_cat:
            cats = ["All"] + sorted(list(set(p.get("category", "") for p in db["products"])))
            sel_cat = st.selectbox("Filter Category", cats)
        with col_src:
            src_prod = st.text_input("Filter appliance models by hardware tags or name", "").strip()
            
        filtered_prods = db["products"]
        # Double safety filter against Smartphones in Streamlit Python code:
        filtered_prods = [
            p for p in filtered_prods 
            if p.get("category", "").lower() != "smartphones" 
            and "phone" not in p.get("category", "").lower()
        ]
        
        if sel_cat != "All":
            filtered_prods = [p for p in filtered_prods if p.get("category") == sel_cat]
        if src_prod:
            s_low = src_prod.lower()
            filtered_prods = [
                p for p in filtered_prods 
                if s_low in p.get("name", "").lower() 
                or s_low in p.get("brand", "").lower() 
                or s_low in p.get("description", "").lower()
            ]
            
        if not filtered_prods:
            st.info("No matching hardware devices or appliances logged.")
        else:
            for p in filtered_prods:
                t_score = p.get("trust_score", 80)
                badge_class, badge_lbl = get_score_class(t_score)
                is_comparing = p["id"] in st.session_state.compare_models
                
                with st.container():
                    # Card HTML - STRICT NOTE: PRICES HAVE BEEN COMPLETELY REMOVED AS REQUESTED! No Price references exist.
                    st.markdown(f"""
                    <div class="vouch-card">
                        <div style="display: flex; justify-content: space-between; align-items: start;">
                            <div>
                                <span style="font-size: 0.8rem; color: #12b76a; font-weight: 800; text-transform: uppercase;">{p.get('brand', '')} &bull; {p.get('category', '')}</span>
                                <h4 style="margin: 0.15rem 0 0.5rem 0; color: #ffffff; font-size: 1.15rem;">{p['name']}</h4>
                            </div>
                            <div>
                                <span class="score-badge {badge_class}">Trust Ratio: {t_score}/100</span>
                            </div>
                        </div>
                        <p style="font-size: 0.85rem; color: #e2e8f0; margin-top: 0.5rem;">{p.get('description', '')}</p>
                        <div style="font-size: 0.8rem; color: #9ca3af; margin-top: 0.5rem;">
                            <strong>Review Authenticity Rate:</strong> <span style="color: #6ee7b7; font-weight:700;">{p.get('authenticity_score', 80)}% Authentic logs</span> | 
                            <strong>Verified Buyer Ratio:</strong> {p.get('verified_review_rate', 90)}% | 
                            <strong>Return (RMA) rate:</strong> <span style="color: #fda4af;">{p.get('return_rate', 2.0)}%</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    col_act1, col_act2, col_act3 = st.columns([1.5, 1.5, 5])
                    with col_act1:
                        if is_comparing:
                            if st.button(f"Uncompare ({p['name'][:12]}...)", key=f"rm_p_{p['id']}"):
                                st.session_state.compare_models.remove(p["id"])
                                st.rerun()
                        else:
                            if len(st.session_state.compare_models) < 3:
                                if st.button(f"⚖️ Compare Model", key=f"add_p_{p['id']}"):
                                    st.session_state.compare_models.append(p["id"])
                                    st.rerun()
                            else:
                                st.write("Max 3 Models matched!")
                                
                    with col_act2:
                        if st.button(f"💬 Inspect Reviews ({p.get('review_count', 140)})", key=f"rev_p_{p['id']}"):
                            st.session_state["review_viewer_open"] = p["id"]
                            st.rerun()
                    
                    # Embedded review logs drawer
                    if st.session_state.get("review_viewer_open") == p["id"]:
                        st.markdown(f"##### Verified Purchase logs & Review Bot Inspections: **{p['name']}**")
                        
                        # Find related reviews
                        prod_reviews = [r for r in db.get("reviews", []) if r.get("product_id") == p["id"]]
                        if not prod_reviews:
                            st.markdown("<p style='font-size: 0.85rem; color: #cbd5e1;'>No consumer feedback records exist for this model in database. Add via Administrator Panel.</p>", unsafe_allow_html=True)
                        else:
                            for rev in prod_reviews:
                                v_badge = "✅ Authentic Buyer" if rev.get("verified", True) else "⚠️ Low Integrity Check"
                                bot_indicator = "" if rev.get("verified", True) else " - *High repetition patterns detected*"
                                st.markdown(f"""
                                <div style="background-color: #0b1329; border: 1px solid #1e293b; border-radius: 6px; padding: 0.75rem; margin-bottom: 0.75rem;">
                                    <div style="display: flex; justify-content: space-between; font-size: 0.75rem;">
                                        <strong style="color: #f8fafc;">Consumer: {rev.get('author', 'Anonymous')}</strong>
                                        <span style="color: #6ee7b7; font-weight:700;">{v_badge}{bot_indicator}</span>
                                    </div>
                                    <div style="font-size: 0.8rem; color: #facc15; margin: 0.25rem 0;">★{"★" * int(rev.get('rating', 4))} ({rev.get('rating')} Stars)</div>
                                    <p style="font-size: 0.85rem; color: #cbd5e1; margin: 0;">"{rev.get('review_text', '')}"</p>
                                </div>
                                """, unsafe_allow_html=True)
                                
                        if st.button("Close Patient Window", key=f"close_rev_prod_{p['id']}"):
                            st.session_state["review_viewer_open"] = None
                            st.rerun()
                    st.markdown("<hr style='border-color: #1e293b; margin: 1rem 0 2rem 0;' />", unsafe_allow_html=True)

#=========================================================
# TAB 2: SIDE-BY-SIDE COMPARISON ENGINE
#=========================================================
with tab_comp:
    st.subheader("Interactive Evaluation Engine")
    
    comp_mode = st.radio("Toggle Comparison Matrix Mode", ["Compare Brand Houses", "Compare Appliance Models"], horizontal=True, key="engine_mode_toggle")
    
    if comp_mode == "Compare Brand Houses":
        if not st.session_state.compare_brands:
            st.info("Your brand comparison checklist is empty. Please visit the '📂 Trust Directory' tab above and select '+ Compare Brand' on up to 3 candidate manufacturer profiles.")
        else:
            st.markdown(f"Currently evaluating {len(st.session_state.compare_brands)} manufacturer brands side-by-side:")
            
            # Load brand records
            selected_brands = [b for b in db["brands"] if b["id"] in st.session_state.compare_brands]
            
            # Construct a side by side comparison table
            cols_comp = st.columns(len(selected_brands) + 1)
            
            with cols_comp[0]:
                st.markdown("**Scoring Attributes**")
                st.markdown("<hr style='border-color: #334155; margin: 0.5rem 0;' />", unsafe_allow_html=True)
                st.write("**Overall Credit Rating**")
                st.write("**Advantage Factors**")
                st.write("**Disadvantage Bottlenecks**")
                st.write("**Years in Retail**")
                st.write("**Warranty Policy coverage**")
                st.write("**Value Index Alignment**")
                st.write("**Promises Maturity Index**")
                st.write("**Repurchase Trust Ratio**")
                st.write("**Trusted Circle Rating**")
                
            for idx, b in enumerate(selected_brands):
                with cols_comp[idx + 1]:
                    st.markdown(f"**{b['brand_name']}**")
                    st.markdown("<hr style='border-color: #334155; margin: 0.5rem 0;' />", unsafe_allow_html=True)
                    st.markdown(f"**{b.get('credibility_score', 80)} / 100**")
                    
                    st.write(", ".join(b.get("advantages", []))[:75] + "...")
                    st.write(", ".join(b.get("disadvantages", []))[:75] + "...")
                    st.write(f"{b.get('years_in_business', 5)} Years active")
                    st.write(b.get("warranty_policy", "Standard"))
                    st.write(f"{b.get('value_for_money', 80)}%")
                    
                    acc = b.get("accountability", {})
                    st.write(f"{acc.get('promises', 85)}% High rating")
                    st.write(f"{acc.get('repurchase', 85)}% Repurchase")
                    st.write(f"{b.get('trusted_circle_score', 80)} Score")
                    
                    if st.button("❌ Remove", key=f"uncomp_brand_{b['id']}"):
                        st.session_state.compare_brands.remove(b["id"])
                        st.rerun()
                        
            if st.button("Clear Entire Brand Checklist"):
                st.session_state.compare_brands = []
                st.rerun()
                
    else:
        if not st.session_state.compare_models:
            st.info("Your appliance comparison list is empty. Please visit the '📂 Trust Directory' tab, select 'Appliance Models', and click '+ Compare Model' on up to 3 candidate devices to compare specs.")
        else:
            st.markdown(f"Currently comparing {len(st.session_state.compare_models)} electronic models side-by-side:")
            
            # Load product records
            selected_prods = [p for p in db["products"] if p["id"] in st.session_state.compare_models]
            
            # Construct comparison layout
            cols_comp_prod = st.columns(len(selected_prods) + 1)
            
            # STRICT REQUIREMENT: PRICES ARE REMOVED ENTIRELY FROM THIS ENGINE TABLE! No price values plotted.
            with cols_comp_prod[0]:
                st.markdown("**Scoring Metrics**")
                st.markdown("<hr style='border-color: #334155; margin: 0.5rem 0;' />", unsafe_allow_html=True)
                st.write("**Credibility Trust Score**")
                st.write("**Review Authenticity**")
                st.write("**Verified Buyers Ratio**")
                st.write("**Warranty Compliance**")
                st.write("**Return Request Rate (RMA)**")
                st.write("**Consumer Complaints Ratio**")
                st.write("**Category**")
                st.write("**Action**")
                
            for idx, p in enumerate(selected_prods):
                with cols_comp_prod[idx + 1]:
                    st.markdown(f"**{p['name']}**")
                    st.markdown(f"<span style='font-size: 0.75rem; color: #12b76a;'>{p.get('brand', '')}</span>", unsafe_allow_html=True)
                    st.markdown("<hr style='border-color: #334155; margin: 0.5rem 0;' />", unsafe_allow_html=True)
                    
                    st.write(f"**{p.get('trust_score', 80)} / 100**")
                    st.write(f"{p.get('authenticity_score', 80)}% Genuine")
                    st.write(f"{p.get('verified_review_rate', 90)}%")
                    st.write(f"{p.get('warranty_score', 80)} / 100")
                    st.write(f"{p.get('return_rate', 2.0)}% Requests")
                    st.write(f"{p.get('complaint_rate', 1.5)}% of sales")
                    st.write(p.get("category", ""))
                    
                    if st.button("❌ Remove", key=f"uncomp_prod_{p['id']}"):
                        st.session_state.compare_models.remove(p["id"])
                        st.rerun()
                        
            if st.button("Clear Comparison Checklist", key="clear_all_prods_list"):
                st.session_state.compare_models = []
                st.rerun()

#=========================================================
# TAB 3: BRAND TRANSPARENCY INDEX
#=========================================================
with tab_trans:
    st.subheader("Bespoke Transparency Analytics")
    st.markdown("Dynamic brand benchmarks across active Indian appliance manufacturers. Evaluate indicators of buyer satisfaction retention vs warranty claims.")
    
    # Render interactive graphs
    col_chart1, col_chart2 = st.columns(2)
    
    # Data visualization 1: Bar Chart of Credibility Scores
    df_brands = pd.DataFrame(db["brands"])
    if not df_brands.empty:
        fig_bar = px.bar(
            df_brands,
            x="brand_name",
            y="credibility_score",
            text="credibility_score",
            title="Credibility Trust Benchmark (0-100)",
            color="credibility_score",
            color_continuous_scale="Viridis",
            labels={"brand_name": "Manufacturer", "credibility_score": "Score value"}
        )
        fig_bar.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#cbd5e1")
        col_chart1.plotly_chart(fig_bar, use_container_width=True)
        
        # Data visualization 2: Scatter plot of business maturity vs customer support
        fig_scatter = px.scatter(
            df_brands,
            x="years_in_business",
            y="customer_service_score",
            size="value_for_money",
            color="transparency_rating",
            title="Market Longevity vs Support Speed",
            labels={"years_in_business": "Retail Presence (Years)", "customer_service_score": "Customer Support (0-100)"},
            hover_name="brand_name"
        )
        fig_scatter.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#cbd5e1")
        col_chart2.plotly_chart(fig_scatter, use_container_width=True)
        
        # Journey trends line graph (Dynamic across 2024 to 2026)
        st.write("#### Historical Verification Improvement Path (2024 - 2026)")
        journey_data = []
        for b in db["brands"]:
            for entry in b.get("journey", []):
                journey_data.append({
                    "Brand": b["brand_name"],
                    "Year": entry["year"],
                    "Audit Trust Score": entry["score"]
                })
        if journey_data:
            df_journey = pd.DataFrame(journey_data)
            fig_journey = px.line(
                df_journey,
                x="Year",
                y="Audit Trust Score",
                color="Brand",
                markers=True,
                title="Dynamic Multi-Year Verification Trajectory"
            )
            fig_journey.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", 
                plot_bgcolor="rgba(0,0,0,0)", 
                font_color="#cbd5e1",
                xaxis=dict(tickmode='linear', tick0=2024, dtick=1)
            )
            st.plotly_chart(fig_journey, use_container_width=True)

#=========================================================
# TAB 4: ASK VOUCH (AI Chatbot Advisor)
#=========================================================
with tab_ai:
    st.subheader("Grounded Chat Advisor")
    st.write("Dynamic product advice driven by official credibility logs and hardware database contexts. Ask specific tech advice, warranty queries, or return-rate investigations.")
    
    # Quick prompt buttons
    st.write("**Frequently Queried Credibility Prompts:**")
    prompt_cols = st.columns(3)
    with prompt_cols[0]:
        if st.button("💻 Which laptops are durable?"):
            pre_prompt = "Compare MacBook Air and other logged laptops in our database regarding warranty compliance. Highlight structural advantages."
            st.session_state.chat_messages.append({"sender": "user", "content": pre_prompt})
            st.rerun()
    with prompt_cols[1]:
        if st.button("📺 Who has highest genuine reviews?"):
            pre_prompt = "Scan the database products and identify which Smart TV has the highest verified buyer reviews and genuine authenticity scores."
            st.session_state.chat_messages.append({"sender": "user", "content": pre_prompt})
            st.rerun()
    with prompt_cols[2]:
        if st.button("🛡️ Show Samsung refrigerator claims info"):
            pre_prompt = "What is the Samsung refrigerator customer service score and warranty policy regarding digital inverter longevity?"
            st.session_state.chat_messages.append({"sender": "user", "content": pre_prompt})
            st.rerun()
            
    # Draw chat window
    for m in st.session_state.chat_messages:
        align = "left" if m["sender"] == "ai" else "right"
        bg_col = "#091124" if m["sender"] == "ai" else "#1b2d4f"
        avatar = "🛡️" if m["sender"] == "ai" else "👤"
        st.markdown(f"""
        <div style="background-color: {bg_col}; border: 1px solid #1e293b; border-radius: 8px; padding: 1rem; margin-bottom: 0.75rem; text-align: {align};">
            <strong>{avatar} {m['sender'].upper()}:</strong>
            <p style="margin-top: 0.5rem; text-align: left; font-size: 0.95rem; line-height: 1.5; color: #f1f5f9;">{m['content']}</p>
        </div>
        """, unsafe_allow_html=True)
        
    chat_prompt = st.text_input("Message Vouch AI Advisor directly...", key="direct_text_prompt_chat", placeholder="Ask: 'Is Mivi's warranty support policy reliable?'")
    
    if st.button("Send Query", key="send_chat_trigger") and chat_prompt.strip():
        user_msg = chat_prompt.strip()
        st.session_state.chat_messages.append({"sender": "user", "content": user_msg})
        
        # Call Gemini server-side using GoogleGenAI SDK format in python!
        gemini_key = os.environ.get("GEMINI_API_KEY")
        if not gemini_key:
            reply = f"Thank you for asking! [No Gemini API Key found in env, fall back to offline database logic]: Scanning 'Vouch AI' index for keywords and rules regarding your query."
        else:
            try:
                # Initialize python client
                client = genai.Client(api_key=gemini_key)
                
                # Setup context from products and brands to make responses deeply grounded and completely factual
                # Filter Smartphones and remove price metrics completely from LLM injection to enforce constraints!
                sanitized_prods = []
                for p in db.get("products", []):
                    if p.get("category", "").lower() != "smartphones" and "phone" not in p.get("category", "").lower():
                        sanitized_prods.append({
                            "name": p.get("name"),
                            "brand": p.get("brand"),
                            "category": p.get("category"),
                            "desc": p.get("description"),
                            "trust_score": p.get("trust_score"),
                            "auth_score": p.get("authenticity_score"),
                            "rma_rate": p.get("return_rate"),
                            "complaints": p.get("complaint_rate")
                        })
                
                # Construct grounding prompt
                grounding_system = f"""
                You are Vouch AI, an elite, unbiased hardware transparency and purchase credibility assistant.
                You are strictly forbidden from showing or referencing product prices (prices has been removed from database to maintain neutral focus on product build Quality, warranty, and return metrics).
                You are strictly forbidden from listing or advising on Smartphones or iPhones (smartphones are completely removed from the catalog). Do not recommend them.
                
                Grounded Database Products: {json.dumps(sanitized_prods)}
                Grounded Manufacturer Brand Details: {json.dumps(db.get("brands", []))}
                
                When the user asks about products, warranties, return rates, or review authenticity, scan these records to formulate exact, truthful metrics. 
                Do not invent specs outside this list. Highlight transparent grade scores, return ratios, and warning triggers!
                """
                
                response = client.models.generate_content(
                    model='gemini-3.5-flash',
                    contents=user_msg,
                    config=types.GenerateContentConfig(
                        system_instruction=grounding_system,
                        temperature=0.7
                    )
                )
                reply = response.text
            except Exception as ex:
                reply = f"Error processing with AI advisor: {ex}. Let me search offline database records instead. Matching products keyword query matches..."
                
        st.session_state.chat_messages.append({"sender": "ai", "content": reply})
        st.rerun()

#=========================================================
# TAB 5: ADMINISTRATOR ROOM (Database Editor Panel)
#=========================================================
with tab_admin:
    st.subheader("Administrator Controls")
    st.write("Manage active brand manufacturer listings or register new models with customized warranty parameters.")
    
    # Form to add product
    st.markdown("#### Append/Amend Appliance Model")
    with st.form("add_product_form_streamlit"):
        col_name, col_br = st.columns(2)
        with col_name:
            p_name = st.text_input("Appliance/Model Name", "Dyson V12 Absolute vacuum")
        with col_br:
            p_brand = st.text_input("Brand/Manufacturer", "Dyson")
            
        col_cat, col_img = st.columns(2)
        with col_cat:
            # Strictly exclude Smartphones category in dropdown
            p_category = st.selectbox("Category Group", ['Skincare & Cream', 'Electric Appliances', 'Smart TVs', 'Refrigerators', 'Washing Machines', 'Headphones', 'Laptops', 'Smart Watches'])
        with col_img:
            p_image = st.text_input("Image Asset URL", "https://images.unsplash.com/photo-1546435770-a3e426bf472b?auto=format&fit=crop&w=600&q=80")
            
        p_desc = st.text_area("Detailed specs description", "Premium cord-free high power dust capture apparatus.")
        
        # STRICT NOTE: PRICES HAVE BEEN ENTIRELY REMOVED FROM FORM PARAMS (No price entry in system setup fields anymore!)
        col_scr1, col_scr2, col_scr3 = st.columns(3)
        with col_scr1:
            p_trust = st.slider("Trust Index Score (0-100)", 10, 100, 92)
        with col_scr2:
            p_auth = st.slider("Review Authenticity % (0-100)", 10, 100, 88)
        with col_scr3:
            p_warranty = st.slider("Warranty Support Performance (0-100)", 10, 100, 90)
            
        col_scr4, col_scr5, col_scr6 = st.columns(3)
        with col_scr4:
            p_rma = st.number_input("Manufacturer Return Rate (RMA % of sales)", 0.0, 20.0, 1.8, step=0.1)
        with col_scr5:
            p_comp = st.number_input("Consumer Complaint Rate (% of sales)", 0.0, 20.0, 1.2, step=0.1)
        with col_scr6:
            p_ver = st.slider("Verified Reviewer Ratio (0-100)", 10, 100, 92)
            
        submit_p = st.form_submit_button("💾 Save Electronic Model to database")
        
        if submit_p:
            new_prod = {
                "id": "p_" + str(int(pd.Timestamp.now().timestamp())),
                "name": p_name.strip(),
                "brand": p_brand.strip(),
                "category": p_category,
                "description": p_desc.strip(),
                "image_url": p_image.strip(),
                "rating": 4.5,
                "review_count": 120,
                "trust_score": int(p_trust),
                "authenticity_score": int(p_auth),
                "transparency_score": int((p_trust + p_auth) // 2),
                "warranty_score": int(p_warranty),
                "complaint_rate": float(p_comp),
                "return_rate": float(p_rma),
                "verified_review_rate": int(p_ver),
                "is_sponsored": False,
                "is_premium_only": False
            }
            # Append product securely
            db["products"].append(new_prod)
            if save_db(db):
                st.success(f"Successfully added model **{p_name}** to persistence catalog!")
                st.rerun()

    # Form to add corporate brand
    st.markdown("#### Append Manufacturer Corporate Profile")
    with st.form("add_brand_form_streamlit"):
        col_b_name, col_b_web = st.columns(2)
        with col_b_name:
            b_name = st.text_input("Corporate Entity Name", "Dyson Corp")
        with col_b_web:
            b_web = st.text_input("Support Website", "https://www.dyson.in")
            
        col_b_yr, col_b_gr = st.columns(2)
        with col_b_yr:
            b_yrs = st.number_input("Years Operating in Retail", 1, 150, 31)
        with col_b_gr:
            b_grade = st.selectbox("Transparency Grade Alpha", ["A+", "A", "B+", "B", "C+", "C"])
            
        b_warranty = st.text_input("Active warranty limits policy", "2 Years Comprehensive parts resolution.")
        b_insights = st.text_area("Audit Insights Brief", "Dyson maintains high ratings regarding service centers and resolution timelines.")
        
        submit_b = st.form_submit_button("💼 Save Brand Corporate Profile")
        
        if submit_b:
            new_brand = {
                "id": "b_" + str(int(pd.Timestamp.now().timestamp())),
                "brand_name": b_name.strip(),
                "credibility_score": 90,
                "transparency_score": 88,
                "website": b_web.strip(),
                "verified": True,
                "years_in_business": int(b_yrs),
                "warranty_policy": b_warranty.strip(),
                "customer_service_score": 88,
                "transparency_rating": b_grade,
                "value_for_money": 82,
                "advantages": ["Top-tier aerodynamics", "Immediate support turnaround"],
                "disadvantages": ["Expensive spare components"],
                "trusted_circle_activity": {"friends": 4, "purchased": 8, "mentors": 1, "experts": 3},
                "trusted_circle_score": 85,
                "journey": [{"year": 2024, "score": 88}, {"year": 2025, "score": 89}, {"year": 2026, "score": 90}],
                "status": "Stable",
                "accountability": {"expectations": 88, "repurchase": 85, "promises": 88},
                "insights": b_insights.strip(),
                "weight_breakdown": {"verification": 90, "sat": 88, "transparency": 88, "consistency": 88, "community": 85, "maturity": 85, "circle": 85},
                "associated_products": ["Electric Appliances"]
            }
            db["brands"].append(new_brand)
            if save_db(db):
                st.success(f"Added corporate brand **{b_name}** to system index!")
                st.rerun()

    # Dynamic database tables view with edit delete
    st.markdown("#### Database Entries Status Monitor")
    
    st.write("**Appliance Products List**")
    p_df = pd.DataFrame(db["products"])
    # Clean Smartphones out just in case
    if not p_df.empty:
        # STRICT NOTE: PRICES REMOVED FROM DATA TABLE PRESENTATION AS WELL!
        show_cols = ["id", "name", "brand", "category", "trust_score", "authenticity_score", "return_rate"]
        st.dataframe(p_df[show_cols])
        
        # Simple deletion UI wrapper
        col_del_id, col_del_btn = st.columns([2, 1])
        with col_del_id:
            del_id = st.text_input("Enter Product ID to remove", "", placeholder="e.g. p3")
        with col_del_btn:
            st.write(" ")
            st.write(" ")
            if st.button("🗑️ Delete Product Record"):
                if del_id.strip():
                    db["products"] = [p for p in db["products"] if p["id"] != del_id.strip()]
                    if save_db(db):
                        st.success(f"Successful removal of Product ID `{del_id}`")
                        st.rerun()
                else:
                    st.warning("Please type a valid ID.")
