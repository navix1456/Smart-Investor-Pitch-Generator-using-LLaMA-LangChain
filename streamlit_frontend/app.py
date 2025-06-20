import streamlit as st
import requests
import os
import json

# --- CONFIG ---
BACKEND_URL = "http://localhost:8000"  # Change if your FastAPI backend runs elsewhere
STARTUP_FILE = "startup_info.json"
RESULTS_FILE = "investor_results.json"
ENRICHED_FILE = "enriched_investors.json"

# --- LOAD FROM FILES ON APP START ---
def load_json_file(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default

if "startup_loaded" not in st.session_state:
    startup_info = load_json_file(STARTUP_FILE, {})
    for k in ["startup_name", "description", "sector", "website"]:
        if k in startup_info:
            st.session_state[k] = startup_info[k]
    st.session_state["startup_loaded"] = True

if "results_loaded" not in st.session_state:
    st.session_state["investor_results"] = load_json_file(RESULTS_FILE, None)
    st.session_state["enriched_investors"] = load_json_file(ENRICHED_FILE, {})
    st.session_state["results_loaded"] = True

# --- SIDEBAR ---
st.sidebar.title("Smart Investor Pitch Generator")
st.sidebar.markdown("""
1. Enter your startup info
2. Search for investors
3. Generate a personalized pitch
""")

# --- MAIN APP ---
st.title("🚀 Smart Investor Pitch Generator")

# Step 1: Enter Startup Info
st.header("1. Startup Information")
with st.form("startup_form"):
    startup_name = st.text_input("Startup Name", value=st.session_state.get("startup_name", ""))
    description = st.text_area("Description", value=st.session_state.get("description", ""))
    sector = st.text_input("Sector/Industry", value=st.session_state.get("sector", ""))
    website = st.text_input("Website (optional)", value=st.session_state.get("website", ""))
    submitted = st.form_submit_button("Save Startup Info")

if submitted:
    st.session_state["startup_name"] = startup_name
    st.session_state["description"] = description
    st.session_state["sector"] = sector
    st.session_state["website"] = website
    # Save to file
    with open(STARTUP_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "startup_name": startup_name,
            "description": description,
            "sector": sector,
            "website": website
        }, f)
    st.success(f"Saved info for: {startup_name}")

# Step 2: Search for Investors
st.header("2. Search for Investors")
search_query = st.text_input("Search investors by name, keyword, or sector")

# Add a Clear All button to reset all data
if st.button("Clear All Data"):
    for k in ["startup_name", "description", "sector", "website", "investor_results", "enriched_investors"]:
        if k in st.session_state:
            del st.session_state[k]
    # Remove files
    for f in [STARTUP_FILE, RESULTS_FILE, ENRICHED_FILE]:
        if os.path.exists(f):
            os.remove(f)
    st.experimental_rerun()

if st.button("Search"):
    if not search_query:
        st.warning("Please enter a search query.")
    else:
        with st.spinner("Searching investors..."):
            try:
                resp = requests.post(
                    f"{BACKEND_URL}/search_investors",
                    json={"keywords": search_query, "num_results": 5}
                )
                if resp.status_code == 200:
                    results = resp.json()
                    st.session_state["investor_results"] = results
                    # Do NOT reset enriched_investors here, so previous enrichments are kept
                    # Save to file
                    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
                        json.dump(results, f)
                    total_results = len(results.get('linkedin', [])) + len(results.get('crunchbase', []))
                    st.success(f"Found {total_results} results.")
                else:
                    st.error(f"Error: {resp.text}")
            except Exception as e:
                st.error(f"API error: {e}")

# --- Display Results if present ---
results = st.session_state.get("investor_results")
if results:
    total_results = len(results.get('linkedin', [])) + len(results.get('crunchbase', []))
    if total_results > 0:
        st.subheader("Investor Results")
        # LinkedIn Results
        if results.get('linkedin'):
            st.markdown("**LinkedIn Results:**")
            for i, res in enumerate(results['linkedin']):
                with st.container():
                    st.markdown(f"**{res['title']}**  ")
                    st.markdown(f"[View LinkedIn Profile]({res['url']})")
                    st.markdown(f"_{res['snippet']}_")
                    # Use a unique key based on name and url
                    enrich_key = f"linkedin_{res['title']}_{res['url']}"
                    if st.button("Auto Enrich", key=enrich_key):
                        with st.spinner("Enriching investor info..."):
                            try:
                                enrich_resp = requests.post(
                                    f"{BACKEND_URL}/auto_enrich_investor",
                                    json={"name": res['title']}
                                )
                                if enrich_resp.status_code == 200:
                                    enriched = enrich_resp.json()
                                    st.session_state["enriched_investors"][enrich_key] = enriched
                                    # Save enriched investors to file
                                    with open(ENRICHED_FILE, "w", encoding="utf-8") as f:
                                        json.dump(st.session_state["enriched_investors"], f)
                                else:
                                    st.error(f"Error: {enrich_resp.text}")
                            except Exception as e:
                                st.error(f"API error: {e}")
                    # Show enriched info if available
                    enriched = st.session_state["enriched_investors"].get(enrich_key)
                    if enriched:
                        with st.expander("Enriched Info"):
                            st.markdown(f"**Name:** {enriched.get('name','')}")
                            st.markdown(f"**Bio:** {enriched.get('bio','')}")
                            st.markdown(f"**Interests:** {enriched.get('interests','')}")
                            st.markdown(f"**LinkedIn:** {enriched.get('linkedin','')}")
                            st.markdown(f"**Notable Investments:** {enriched.get('notable_investments','')}")
                            st.markdown(f"**Location:** {enriched.get('location','')}")
                            if enriched.get('crunchbase_bio'):
                                st.markdown(f"**Crunchbase Bio:** {enriched.get('crunchbase_bio','')}")
                    st.markdown("---")
        # Crunchbase Results
        if results.get('crunchbase'):
            st.markdown("**Crunchbase Results:**")
            for i, res in enumerate(results['crunchbase']):
                with st.container():
                    st.markdown(f"**{res['title']}**  ")
                    st.markdown(f"[View Crunchbase Profile]({res['url']})")
                    st.markdown(f"_{res['snippet']}_")
                    # Use a unique key based on name and url
                    enrich_key = f"crunchbase_{res['title']}_{res['url']}"
                    if st.button("Auto Enrich", key=enrich_key):
                        with st.spinner("Enriching investor info..."):
                            try:
                                enrich_resp = requests.post(
                                    f"{BACKEND_URL}/auto_enrich_investor",
                                    json={"name": res['title']}
                                )
                                if enrich_resp.status_code == 200:
                                    enriched = enrich_resp.json()
                                    st.session_state["enriched_investors"][enrich_key] = enriched
                                    # Save enriched investors to file
                                    with open(ENRICHED_FILE, "w", encoding="utf-8") as f:
                                        json.dump(st.session_state["enriched_investors"], f)
                                else:
                                    st.error(f"Error: {enrich_resp.text}")
                            except Exception as e:
                                st.error(f"API error: {e}")
                    # Show enriched info if available
                    enriched = st.session_state["enriched_investors"].get(enrich_key)
                    if enriched:
                        with st.expander("Enriched Info"):
                            st.markdown(f"**Name:** {enriched.get('name','')}")
                            st.markdown(f"**Bio:** {enriched.get('bio','')}")
                            st.markdown(f"**Interests:** {enriched.get('interests','')}")
                            st.markdown(f"**LinkedIn:** {enriched.get('linkedin','')}")
                            st.markdown(f"**Notable Investments:** {enriched.get('notable_investments','')}")
                            st.markdown(f"**Location:** {enriched.get('location','')}")
                            if enriched.get('crunchbase_bio'):
                                st.markdown(f"**Crunchbase Bio:** {enriched.get('crunchbase_bio','')}")
                    st.markdown("---")

# Step 4: Generate Personalized Pitch
st.header("3. Generate Personalized Pitch")

# Only allow if there is at least one enriched investor
all_enriched = st.session_state.get("enriched_investors", {})
if all_enriched:
    enriched_keys = list(all_enriched.keys())
    enriched_labels = [all_enriched[k].get("name", k) for k in enriched_keys]
    selected_idx = st.selectbox("Select an investor to generate a pitch for:", range(len(enriched_keys)), format_func=lambda i: enriched_labels[i])
    selected_investor = all_enriched[enriched_keys[selected_idx]]

    # Startup info (from session state)
    s_name = st.session_state.get("startup_name", "")
    s_desc = st.session_state.get("description", "")
    s_sector = st.session_state.get("sector", "")
    s_website = st.session_state.get("website", "")
    # For demo, use simple mapping for required fields
    st.markdown("**Startup Info:**")
    st.markdown(f"- **Name:** {s_name}")
    st.markdown(f"- **Description:** {s_desc}")
    st.markdown(f"- **Sector:** {s_sector}")
    st.markdown(f"- **Website:** {s_website}")

    tone = st.selectbox("Select tone: ", ["professional", "friendly", "bold", "enthusiastic"])
    feedback = st.checkbox("Request feedback on the pitch?", value=True)

    if st.button("Generate Pitch"):
        with st.spinner("Generating pitch..."):
            try:
                # Prepare payload for /generate endpoint
                payload = {
                    "startup": {
                        "name": s_name,
                        "niche": s_sector,
                        "traction": s_desc,
                        "goals": s_desc,
                        "extra_info": s_website
                    },
                    "investor": {
                        "name": selected_investor.get("name", ""),
                        "bio": selected_investor.get("bio", ""),
                        "interests": selected_investor.get("interests", ""),
                        "linkedin": selected_investor.get("linkedin", ""),
                        "notable_investments": selected_investor.get("notable_investments", ""),
                        "location": selected_investor.get("location", "")
                    },
                    "tone": tone,
                    "feedback": feedback
                }
                resp = requests.post(f"{BACKEND_URL}/generate", json=payload)
                if resp.status_code == 200:
                    pitch = resp.json().get("result", "")
                    st.success("Pitch generated!")
                    st.markdown("---")
                    st.markdown("**Generated Pitch:**")
                    st.markdown(f"""```markdown\n{pitch}\n```""")
                    if st.button("Copy Pitch to Clipboard"):
                        st.experimental_set_clipboard(pitch)
                        st.info("Pitch copied to clipboard!")
                else:
                    st.error(f"Error: {resp.text}")
            except Exception as e:
                st.error(f"API error: {e}")
else:
    st.info("Enrich at least one investor to generate a personalized pitch.") 