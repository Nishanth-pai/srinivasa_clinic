import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json
import requests
from bs4 import BeautifulSoup
import pandas as pd
import io
from datetime import datetime
import re
import time


# --- FIREBASE SETUP ---
# Check if the app is already initialized to prevent double-loading errors
if not firebase_admin._apps:
    # Convert Streamlit's secure [firebase] block back into a dictionary
    firebase_credentials = dict(st.secrets["firebase"])
    
    # Initialize using the secure dictionary instead of a local file
    cred = credentials.Certificate(firebase_credentials)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# --- 2. PAGE FUNCTIONS ---
def home_page():
    st.title("🌿 Ayurveda Clinic & Wellness")
    st.write("Welcome to our holistic healing center. We specialize in traditional Ayurvedic treatments, Kaya Chikitsa, and Panchakarma therapies.")
    st.divider()
    
    # WhatsApp Enquiry Integration
    st.subheader("Book a Consultation")
    st.write("Click the button below to schedule your appointment directly with our front desk.")
    
    phone_number = "919876543210" # Replace with actual number
    message = "Hello, I would like to enquire about a consultation booking."
    whatsapp_url = f"https://wa.me/{phone_number}?text={message.replace(' ', '%20')}"
    
    st.markdown(
        f'<a href="{whatsapp_url}" target="_blank">'
        f'<button style="background-color:#25D366; color:white; font-weight:bold; padding:10px 24px; border:none; border-radius:8px; cursor:pointer;">'
        f'💬 Chat on WhatsApp</button></a>', 
        unsafe_allow_html=True
    )

def consultant_portal():
    st.title("👨‍⚕️ Consultant Dashboard")
    
    # Check if the user is already logged in during this session
    if "user_token" not in st.session_state:
        st.session_state.user_token = None

    # Login Form
    if st.session_state.user_token is None:
        st.subheader("Please Log In")
        email = st.sidebar.text_input("Email")
        password = st.sidebar.text_input("Password", type="password")
        
        if st.sidebar.button("Log In"):
            api_key = st.secrets["FIREBASE_WEB_API_KEY"]
            url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
            payload = {"email": email, "password": password, "returnSecureToken": True}
            
            response = requests.post(url, json=payload)
            auth_data = response.json()
            
            if "idToken" in auth_data:
                st.session_state.user_token = auth_data["idToken"]
                st.sidebar.success("Logged in successfully!")
                st.rerun() # Refresh the page to show the dashboard
            else:
                st.sidebar.error("Invalid Email or Password.")
    
    # Dashboard (Only visible if logged in)
    if st.session_state.user_token is not None:
        if st.sidebar.button("Log Out"):
            st.session_state.user_token = None
            st.rerun()
            
        # Add the third tab for Statistics
   # Add the third tab for Statistics
        tab1, tab2, tab3 = st.tabs(["Add New Patient", "Search Database", "Clinic Statistics"])
        
        # --- TAB 1: REGISTRATION FORM ---
        with tab1:
            st.subheader("Patient Registration")
            with st.form("patient_form"):
                col1, col2 = st.columns(2)
                name = col1.text_input("Name")
                age = col1.number_input("Age", min_value=1, step=1)
                phone = col1.text_input("Phone Number")
                address = col2.text_area("Address")
                
                st.divider()
                
                # --- NEW VITALS SECTION ---
                st.markdown("**Vitals**")
                v1, v2, v3, v4 = st.columns(4)
                bp = v1.text_input("BP (e.g. 120/80)")
                weight = v2.number_input("Weight (kg)", min_value=0.0, step=0.1)
                temp = v3.number_input("Temp (°F)", value=98.6, step=0.1)
                pulse = v4.number_input("Pulse (bpm)", min_value=0, step=1)
                
                st.divider()
                
                chief_complaints = st.text_area("Chief Complaints")
                co_morbidities = st.text_area("Co-morbidities")
                examinations = st.text_area("Examinations")
                investigations = st.text_area("Investigations Notes")
                diagnosis = st.text_input("Diagnosis")
                prescription = st.text_area("Prescription")
                
                submitted = st.form_submit_button("Save Patient Record")
                
                if submitted:
                    today_date = datetime.now().strftime("%Y-%m-%d")
                    patient_data = {
                        "registration_date": today_date, # Date stamp for first visit stats
                        "name": name, "age": age, "phone": phone, "address": address,
                        "bp": bp, "weight": weight, "temp": temp, "pulse": pulse,
                        "chief_complaints": chief_complaints, "co_morbidities": co_morbidities,
                        "examinations": examinations, "investigations": investigations,
                        "diagnosis": diagnosis, "prescription": prescription,
                        "visits": [] 
                    }
                    
                    db.collection("patients").add(patient_data)
                    st.success(f"Record for {name} saved successfully!")
                    
        # --- TAB 2: SEARCH DATABASE ---
        with tab2:
            st.subheader("Search Patients")
            
            docs = db.collection("patients").stream()
            patient_dict = {}
            options = [""]
            
            for doc in docs:
                data = doc.to_dict()
                label = f"{data.get('name')} - {data.get('phone')}"
                options.append(label)
                patient_dict[label] = {"id": doc.id, "data": data}
            
            selected_patient = st.selectbox("Type a name or phone number to search:", options)
            
            if selected_patient != "":
                doc_id = patient_dict[selected_patient]["id"]
                data = patient_dict[selected_patient]["data"]
                
                with st.expander(f"🩺 {data.get('name')} - {data.get('phone')}", expanded=True):
                    
                    st.markdown("### 📋 Patient Summary")
                    visits = data.get('visits', [])
                    
                    if visits and visits[-1].get('diagnosis'):
                        latest_diagnosis = visits[-1]['diagnosis']
                    else:
                        latest_diagnosis = data.get('diagnosis', 'Not specified')
                        
                    col_a, col_b = st.columns(2)
                    col_a.write(f"**Name:** {data.get('name')}")
                    col_a.write(f"**Age:** {data.get('age')} | **Phone:** {data.get('phone')}")
                    
                    col_b.write(f"**Total Visits:** {len(visits) + 1}")
                    col_b.write(f"**Latest Diagnosis:** {latest_diagnosis}")
                    
                    # Display the new vitals in the patient profile
                    st.info(f"**Baseline Vitals:** BP: {data.get('bp', 'N/A')} | Weight: {data.get('weight', '0.0')}kg | Temp: {data.get('temp', '0.0')}°F | Pulse: {data.get('pulse', '0')}bpm")
                    
                    st.divider()
                    
                    st.markdown("### 🗓️ Visit History")
                    
                    with st.expander(f"First Visit - {data.get('diagnosis', 'No Diagnosis')}"):
                        st.write(f"**Complaints:** {data.get('chief_complaints')}")
                        st.write(f"**Diagnosis:** {data.get('diagnosis')}")
                        st.write(f"**Prescription:** {data.get('prescription')}")
                        
                        html_first = f"""
                        <html>
                        <body style="font-family: sans-serif; padding: 40px; max-width: 800px; margin: auto;">
                            <h1 style="text-align: center; color: #2c3e50;">Srinivasa Clinic</h1>
                            <hr>
                            <p><strong>Patient Name:</strong> {data.get('name')} <span style="float: right;"><strong>Age:</strong> {data.get('age')}</span></p>
                            <p><strong>Diagnosis:</strong> {data.get('diagnosis')}</p>
                            <p><strong>Complaints:</strong> {data.get('chief_complaints')}</p>
                            <br>
                            <h3>Prescription (Rx):</h3>
                            <p style="white-space: pre-wrap; line-height: 1.6;">{data.get('prescription')}</p>
                            <br><br><br><br><hr>
                            <p style="text-align: right;">Doctor's Signature: ______________________</p>
                            <script>window.print();</script>
                        </body>
                        </html>
                        """
                        st.download_button("🖨️ Print First Visit", data=html_first, file_name=f"{str(data.get('name'))}_FirstVisit.html", mime="text/html", key=f"print_orig_{doc_id}")
                    
                    for idx, visit in enumerate(visits):
                        with st.expander(f"Follow-up: {visit.get('date')} - {visit.get('diagnosis')}"):
                            st.write(f"**Complaints:** {visit.get('complaints')}")
                            st.write(f"**Diagnosis:** {visit.get('diagnosis')}")
                            st.write(f"**Prescription:** {visit.get('prescription')}")
                            
                            html_followup = f"""
                            <html>
                            <body style="font-family: sans-serif; padding: 40px; max-width: 800px; margin: auto;">
                                <h1 style="text-align: center; color: #2c3e50;">Srinivasa Clinic</h1>
                                <hr>
                                <p><strong>Patient Name:</strong> {data.get('name')} <span style="float: right;"><strong>Age:</strong> {data.get('age')}</span></p>
                                <p><strong>Date:</strong> {visit.get('date')}</p>
                                <p><strong>Diagnosis:</strong> {visit.get('diagnosis')}</p>
                                <p><strong>Complaints:</strong> {visit.get('complaints')}</p>
                                <br>
                                <h3>Prescription (Rx):</h3>
                                <p style="white-space: pre-wrap; line-height: 1.6;">{visit.get('prescription')}</p>
                                <br><br><br><br><hr>
                                <p style="text-align: right;">Doctor's Signature: ______________________</p>
                                <script>window.print();</script>
                            </body>
                            </html>
                            """
                            st.download_button("🖨️ Print This Visit", data=html_followup, file_name=f"{str(data.get('name'))}_{visit.get('date')}.html", mime="text/html", key=f"print_{doc_id}_{idx}")

                    st.divider()
                    
                    with st.form(f"follow_up_{doc_id}"):
                        st.markdown("### 🔄 Add Follow-up Visit")
                        today_date = datetime.now().strftime("%Y-%m-%d")
                        st.caption(f"Date: {today_date}")
                        
                        new_complaints = st.text_area("Complaints / Notes for today")
                        new_diagnosis = st.text_input("Current Diagnosis", value=latest_diagnosis)
                        new_prescription = st.text_area("Prescription for today")
                        
                        if st.form_submit_button("Save Follow-up"):
                            new_visit = {
                                "date": today_date,
                                "complaints": new_complaints,
                                "diagnosis": new_diagnosis,
                                "prescription": new_prescription
                            }
                            updated_visits = visits + [new_visit]
                            db.collection("patients").document(doc_id).update({"visits": updated_visits})
                            st.success("Follow-up saved!")
                            st.rerun()

        # --- TAB 3: CLINIC STATISTICS ---
        with tab3:
            st.subheader("📊 Clinic Statistics & Export")
            
            # --- FILTERS ---
            st.markdown("### 📅 Select Parameters & Date Range")
            col_d1, col_d2 = st.columns(2)
            start_date = col_d1.date_input("Start Date", value=pd.to_datetime("today") - pd.DateOffset(days=30))
            end_date = col_d2.date_input("End Date", value=pd.to_datetime("today"))
            
            # Multiselect for dynamic categories
            available_params = ["Age", "Diagnosis", "Weight", "Pulse", "BP"]
            selected_params = st.multiselect("Select categories to analyze:", available_params, default=["Age", "Diagnosis"])
            
            if st.button("Generate Dashboard"):
                all_docs = db.collection("patients").stream()
                
                start_str = start_date.strftime("%Y-%m-%d")
                end_str = end_date.strftime("%Y-%m-%d")
                
                records = []
                
                for doc in all_docs:
                    data = doc.to_dict()
                    reg_date = data.get('registration_date', "2020-01-01")
                    
                    # 1. Process First Visits
                    if start_str <= reg_date <= end_str:
                        records.append({
                            "Date": reg_date,
                            "Patient Name": data.get('name', 'Unknown'),
                            "Age": data.get('age', 0),
                            "Phone": data.get('phone', ''),
                            "Diagnosis": data.get('diagnosis', '').strip().title(),
                            "Weight (kg)": data.get('weight', 0.0),
                            "Pulse (bpm)": data.get('pulse', 0),
                            "BP": data.get('bp', ''),
                            "Visit Type": "First Visit"
                        })
                        
                    # 2. Process Follow-ups
                    for v in data.get('visits', []):
                        v_date = v.get('date', '')
                        if start_str <= v_date <= end_str:
                            records.append({
                                "Date": v_date,
                                "Patient Name": data.get('name', 'Unknown'),
                                "Age": data.get('age', 0),
                                "Phone": data.get('phone', ''),
                                "Diagnosis": v.get('diagnosis', '').strip().title(),
                                "Weight (kg)": None, # Baseline vitals only
                                "Pulse (bpm)": None, 
                                "BP": None,
                                "Visit Type": "Follow-up"
                            })
                            
                # Save the data to session state so it survives the download button refresh
                st.session_state.export_df = pd.DataFrame(records)
                st.session_state.show_stats = True

            # --- DISPLAY RESULTS & EXPORT ---
            if st.session_state.get("show_stats") and "export_df" in st.session_state:
                df = st.session_state.export_df
                
                if df.empty:
                    st.warning("No records found for this date range.")
                else:
                    total_consultations = len(df)
                    total_unique = df['Patient Name'].nunique()
                    
                    col1, col2 = st.columns(2)
                    col1.metric("Total Consultations in Range", total_consultations)
                    col2.metric("Unique Patients in Range", total_unique)
                    
                    st.divider()
                    
                    # --- DYNAMIC CHARTS ---
                    if "Age" in selected_params:
                        st.markdown("**Age Distribution**")
                        bins = [0, 10, 20, 30, 40, 50, 60, 70, 80, 100]
                        labels = ['0-10', '11-20', '21-30', '31-40', '41-50', '51-60', '61-70', '71-80', '80+']
                        valid_ages = pd.to_numeric(df['Age'], errors='coerce').dropna()
                        if not valid_ages.empty:
                            age_groups = pd.cut(valid_ages, bins=bins, labels=labels, right=False).value_counts().sort_index()
                            st.bar_chart(age_groups)
                        else:
                            st.info("No valid age data.")
                            
                    if "Diagnosis" in selected_params:
                        st.markdown("**Most Common Diagnoses**")
                        valid_diag = df['Diagnosis'].replace("", float("NaN")).dropna()
                        if not valid_diag.empty:
                            st.bar_chart(valid_diag.value_counts().head(10))
                        else:
                            st.info("No valid diagnosis data.")
                            
                    if "Weight" in selected_params:
                        st.markdown("**Weight Overview (Baseline Registrations)**")
                        valid_weights = pd.to_numeric(df['Weight (kg)'], errors='coerce').dropna()
                        valid_weights = valid_weights[valid_weights > 0]
                        if not valid_weights.empty:
                            st.line_chart(valid_weights.reset_index(drop=True))
                        else:
                            st.info("No valid weight data in this range.")
                            
                    if "Pulse" in selected_params:
                        st.markdown("**Pulse Overview (Baseline Registrations)**")
                        valid_pulse = pd.to_numeric(df['Pulse (bpm)'], errors='coerce').dropna()
                        valid_pulse = valid_pulse[valid_pulse > 0]
                        if not valid_pulse.empty:
                            st.line_chart(valid_pulse.reset_index(drop=True))
                        else:
                            st.info("No valid pulse data in this range.")
                            
                    if "BP" in selected_params:
                        st.markdown("**Blood Pressure Log (Baseline Registrations)**")
                        valid_bp = df[['Date', 'Patient Name', 'BP']].dropna(subset=['BP'])
                        valid_bp = valid_bp[valid_bp['BP'] != ""]
                        if not valid_bp.empty:
                            st.dataframe(valid_bp, use_container_width=True)
                        else:
                            st.info("No BP data recorded in this range.")
                            
                    st.divider()
                    
                    # --- EXPORT TO EXCEL ---
                    st.markdown("### 💾 Export Data")
                    
                    # Create the Excel file in memory
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        df.to_excel(writer, index=False, sheet_name='Clinic_Stats')
                        
                    st.download_button(
                        label="📥 Download Full Data as Excel (.xlsx)",
                        data=buffer.getvalue(),
                        file_name=f"Clinic_Stats_{start_date}_to_{end_date}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
def split_into_padas(verse_text):
    """
    Cleans and splits a Sanskrit verse into its constituent padas.
    Handles traditional dandas (।, ॥) and standard line breaks.
    """
    normalized_text = verse_text.replace("॥", "।").replace("\n", "।")
    
    # Split the text at the single danda and remove any extra whitespace
    raw_padas = [p.strip() for p in normalized_text.split("।") if p.strip()]
    
    # Organize into a dictionary format
    structured_padas = {}
    for i, pada in enumerate(raw_padas):
        structured_padas[f"Pada {i+1}"] = pada
        
    return structured_padas

def split_into_padas(verse_text):
    """
    Cleans and splits a Sanskrit verse into its constituent padas.
    Handles traditional dandas (।, ॥), English pipes (|), and standard line breaks.
    """
    # Now catches English keyboard pipes and standardizes everything
    normalized_text = verse_text.replace("॥", "।").replace("\n", "।").replace("|", "।")
    
    # Split the text at the danda and remove any extra whitespace
    raw_padas = [p.strip() for p in normalized_text.split("।") if p.strip()]
    
    # Organize into a dictionary format
    structured_padas = {}
    for i, pada in enumerate(raw_padas):
        structured_padas[f"Pada {i+1}"] = pada
        
    return structured_padas

def get_prosody_details(pada_text):
    """
    Approximates the syllables, Laghu (I) / Guru (S) pattern, 
    and Chandas for a given Sanskrit pada (even if merged).
    """
    # Remove spaces to analyze pure syllables
    clean_text = pada_text.replace(" ", "")
    
    syllables = []
    temp = ""
    
    # 1. Break down into Syllables (Aksharas)
    for i, char in enumerate(clean_text):
        temp += char
        if i + 1 < len(clean_text):
            next_char = clean_text[i+1]
            if next_char not in ['ा', 'ि', 'ी', 'ु', 'ू', 'ृ', 'ॄ', 'े', 'ै', 'ो', 'ौ', 'ं', 'ः', '्'] and char != '्':
                syllables.append(temp)
                temp = ""
        else:
            syllables.append(temp)
            
    # 2. Assign Laghu (I) or Guru (S)
    guru_markers = ['ा', 'ी', 'ू', 'े', 'ै', 'ो', 'ौ', 'ं', 'ः']
    pattern = []
    
    for idx, syl in enumerate(syllables):
        is_guru = False
        if any(m in syl for m in guru_markers):
            is_guru = True
        if idx + 1 < len(syllables) and '्' in syllables[idx+1]:
            is_guru = True
            
        pattern.append("S" if is_guru else "I")
        
    # 3. Smart Chandas Identification (Now handles merged Padas with NO dandas)
    syl_count = len(syllables)
    
    if syl_count == 8:
        chandas = "Anushtubh (8 syllables)"
    elif syl_count == 16:
        chandas = "Anushtubh (16 syllables - 2 Merged Padas)"
    elif syl_count == 32:
        chandas = "Anushtubh (32 syllables - Full Verse)"
    elif syl_count == 11:
        chandas = "Trishtubh Family (11 syllables - e.g., Indravajra)"
    elif syl_count == 22:
        chandas = "Trishtubh Family (22 syllables - 2 Merged Padas)"
    elif syl_count == 12:
        chandas = "Jagati Family (12 syllables - e.g., Vamshastha)"
    elif syl_count == 24:
        chandas = "Jagati Family (24 syllables - 2 Merged Padas)"
    elif syl_count == 14:
        chandas = "Vasantatilaka (14 syllables)"
    elif syl_count == 28:
        chandas = "Vasantatilaka (28 syllables - 2 Merged Padas)"
    elif syl_count == 19:
        chandas = "Shardulavikridita (19 syllables)"
    elif syl_count == 38:
        chandas = "Shardulavikridita (38 syllables - 2 Merged Padas)"
    else:
        chandas = f"Mixed / Unknown ({syl_count} syllables)"
        
    return syllables, pattern, chandas

def render_laghu_guru_html(syllables, pattern):
    """Generates HTML to stack the Laghu/Guru marks and group them into Ganas (sets of 3)."""
    html = "<div style='display: flex; flex-wrap: wrap; margin-bottom: 15px;'>"
    
    # Iterate through syllables in chunks of 3 (Ganas)
    for i in range(0, len(syllables), 3):
        chunk_syl = syllables[i:i+3]
        chunk_pat = pattern[i:i+3]
        
        # Create a visually distinct box for each Gana
        html += "<div style='display: flex; border: 2px solid #bdc3c7; border-radius: 8px; padding: 5px; margin-right: 12px; margin-bottom: 10px; background-color: #f9fbfd;'>"
        
        # Render the syllables inside the box
        for syl, mark in zip(chunk_syl, chunk_pat):
            color = "#e74c3c" if mark == 'S' else "#3498db"
            html += f"<div style='display: flex; flex-direction: column; align-items: center; padding: 0 8px; font-family: sans-serif;'><span style='font-size: 16px; font-weight: bold; color: {color};'>{mark}</span><span style='font-size: 22px; color: #2c3e50;'>{syl}</span></div>"
        
        # Close the Gana box
        html += "</div>"
        
    html += "</div>"
    return html
# ... (your existing get_prosody_details and render_laghu_guru_html functions are here) ...

@st.cache_data(show_spinner=False, ttl=86400)
def fetch_native_dictionary(word):
    """
    Diagnostic dictionary engine.
    This version removes the cache to force live network requests and 
    will print the exact server error to your screen if it fails.
    """
    raw_word = word.strip()
    
    base_stem = raw_word
    if raw_word.endswith("ः") or raw_word.endswith("ं"):
        base_stem = raw_word[:-1]
    elif raw_word.endswith("म्"):
        base_stem = raw_word[:-2]
        
    classical_base = base_stem.replace("र्त", "र्त्त").replace("र्ति", "र्त्ति").replace("र्य", "र्य्य").replace("र्व", "र्व्व")
    
    search_variations = [
        raw_word, base_stem, f"{base_stem}ः", f"{base_stem}म्", f"{base_stem}ं", 
        classical_base, f"{classical_base}ः", f"{classical_base}म्", f"{classical_base}ं"
    ]
    
    search_variations = list(dict.fromkeys(search_variations))
    
    def fetch_from_api(search_term, dict_code="SKDScan"):
        url = f"https://www.sanskrit-lexicon.uni-koeln.de/scans/{dict_code}/2020/web/webtc/getword.php?input=deva&output=deva&key={search_term}"
        try:
            # We add headers to pretend we are a normal web browser, not a Python bot
            headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, timeout=8)
            
            # Diagnostic Check: Did the server block us?
            if response.status_code == 403:
                return "SERVER_BLOCKED"
                
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                raw_text = soup.get_text(separator=' ', strip=True)
                if "not found" in raw_text.lower() or "error" in raw_text.lower():
                    return None
                clean_text = re.sub(r"\[\s*ID=\d+\s*\]", "", raw_text)
                return clean_text.replace("  ", " ").strip()
                
            return f"HTTP_ERROR_{response.status_code}"
            
        except requests.exceptions.Timeout:
            return "TIMEOUT"
        except Exception as e:
            return f"CODE_ERROR"

    # PHASE 1: Query Sabda-kalpadruma
    for variant in search_variations:
        result = fetch_from_api(variant, "SKDScan")
        
        # Catch explicit errors from the server
        if result == "SERVER_BLOCKED":
            return "⚠️ **Connection Blocked:** The Cologne database is currently rejecting requests from Streamlit Cloud due to rate-limiting. Please try again in a few hours."
        elif result in ["TIMEOUT", "CODE_ERROR"] or str(result).startswith("HTTP_ERROR"):
            return f"⚠️ **Network Issue:** The server returned an error ({result})."
            
        if result:
            prefix = "" if variant == raw_word else f"*(Found in Sabda-kalpadruma as: **{variant}**)*\n\n"
            return prefix + result
            
        time.sleep(0.3)
            
    # PHASE 2: Fallback to Monier-Williams
    for variant in [base_stem, raw_word]:
        result = fetch_from_api(variant, "MWScan")
        
        if result == "SERVER_BLOCKED":
            return "⚠️ **Connection Blocked:** The Cologne database is currently rejecting requests from Streamlit Cloud."
            
        if result:
            prefix = f"*(Word not in Sabda-kalpadruma. Found in Monier-Williams as: **{variant}**)*\n\n"
            return prefix + result
            
        time.sleep(0.3)
            
    return None

    # PHASE 1: Query Sabda-kalpadruma
    for variant in search_variations:
        result = fetch_from_api(variant, "SKDScan")
        if result:
            prefix = "" if variant == raw_word else f"*(Found in Sabda-kalpadruma as: **{variant}**)*\n\n"
            return prefix + result
        time.sleep(0.3) # <-- Pauses for 0.3 seconds to prevent server bans
            
    # PHASE 2: Fallback to Monier-Williams
    for variant in [base_stem, raw_word]:
        result = fetch_from_api(variant, "MWScan")
        if result:
            prefix = f"*(Word not in Sabda-kalpadruma. Found in Monier-Williams as: **{variant}**)*\n\n"
            return prefix + result
        time.sleep(0.3) # <-- Pauses for 0.3 seconds here too
            
    return None

    # 1. First attempt: Search exactly what the user typed
    result = fetch_from_api(word)
    
    if result:
        return result
        
    # 2. Second attempt: Apply classical Paninian doubling rules if the first search fails
    # E.g., मूर्ति -> मूर्त्ति, कार्य -> कार्य्य, सर्व -> सर्व्व
    classical_word = word.replace("र्त", "र्त्त").replace("र्ति", "र्त्ति").replace("र्य", "र्य्य").replace("र्व", "र्व्व")
    
    if classical_word != word:
        # Silently try the search again with the classical spelling
        return fetch_from_api(classical_word)
        
    return None

# --- PORTAL FUNCTIONS ---

def student_portal():
    st.title("📚 Student Learning Corner")
    # ... (the rest of your student portal code continues below) ...

def student_portal():
    st.title("📚 Student Learning Corner")
    st.write("Welcome to the academic portal. Explore classical text analyses, grammar breakdowns, and clinical inventions.")
    
    # Added a third tab for the Grammar Sandbox
    tab1, tab2, tab3 = st.tabs(["Classical Text Analysis", "Real-Time Grammar", "Clinical Inventions"])
    
    # --- TAB 1: VERSE ANALYSIS (PROSODY) ---
    with tab1:
        st.subheader("Verse Breakdown & Prosody")
        st.write("Analyze the structure, meter (Chandas), and clinical meaning of classical verses.")
        
        col1, col2 = st.columns(2)
        verse_input = col1.text_area("1. Enter Raw Verse (Sloka)", "")
        split_input = col2.text_area("2. Enter Split Version (Padacheda)", "")
        
        if st.button("Analyze Verse") and verse_input:
            st.divider()
            
            text_to_process = split_input if split_input.strip() else verse_input
            pada_dictionary = split_into_padas(text_to_process)
            
            st.markdown("### 🧩 Structural Breakdown")
            st.info(f"**Total Padas Identified:** {len(pada_dictionary)}")
            
            for pada_name, pada_text in pada_dictionary.items():
                with st.container():
                    st.markdown(f"#### {pada_name}")
                    st.write(f"**Text:** {pada_text}")
                    
                    syllables, pattern, chandas = get_prosody_details(pada_text)
                    html_output = render_laghu_guru_html(syllables, pattern)
                    st.markdown(html_output, unsafe_allow_html=True)
                    
                    st.caption(f"**Identified Meter:** {chandas}")
                    st.markdown("<hr style='margin-top: 5px; margin-bottom: 15px;'>", unsafe_allow_html=True)
            
            st.markdown("### Clinical Understanding")
            
            # A mini-dictionary to hold your verse meanings
            known_verses = {
                "तत्र पूर्वं ज्वरे": "Detailed explanation of the mechanism of Langhana in early stages of Jvara.",
                "तस्यायुषः पुण्यतमो": "Explanation of the most sacred Veda (Ayurveda) for those seeking longevity.",
                # You can easily add more verses and meanings here in the future!
            }
            
            # Check if any of our known verse snippets are inside the text the user pasted
            meaning_found = False
            for snippet, meaning in known_verses.items():
                if snippet in text_to_process:
                    st.write(meaning)
                    meaning_found = True
                    break # Stop searching once we find a match
            
            # If the verse isn't in our dictionary, show a default message
            if not meaning_found:
                st.info("The clinical meaning for this specific verse has not been added to the local database yet.")

    # --- TAB 2: REAL-TIME GRAMMAR ANALYSIS ---
    with tab2:
        st.subheader("🔍 Real-Time Grammar & Sandhi Sandbox")
        st.write("Type a combined Sanskrit word to instantly analyze its components, roots (Dhatu), and cases (Vibhakti).")
        
        # Streamlit automatically updates the page as you type in this box
        word_to_analyze = st.text_input("Enter a word to parse (e.g., जलदोषात्, रामस्य, वृक्षे):").strip()
        
        if word_to_analyze:
            st.divider()
            st.markdown(f"### Live Analysis: **{word_to_analyze}**")
            
            col_g1, col_g2 = st.columns(2)
            
            with col_g1:
                st.markdown("### ✂️ 1. Padacheda (Word Splitting)")
                # A basic Sandhi splitting heuristic for common clinical terms
                if "दोषात्" in word_to_analyze:
                    base_word = word_to_analyze.replace("दोषात्", "")
                    st.info(f"**{base_word}** + **दोष** (with Panchami suffix)")
                elif "स्य" in word_to_analyze and not word_to_analyze.endswith("स्य"):
                    # Basic split for compound words containing 'sya'
                    parts = word_to_analyze.split("स्य")
                    st.info(f"**{parts[0]}** + **{parts[1]}**")
                else:
                    st.info(f"**{word_to_analyze}** (Primary Base Form)")
                    
                st.markdown("### 🌱 2. Dhatu (Root) & Pratyaya")
                # Simple lookup for common clinical Dhatus
                dhatu_dict = {
                    "ज्वर": "ज्वर् (to be hot / to have fever)",
                    "कुर्या": "कृ (to do / to make)",
                    "लङ्घन": "लङ्घ् (to leap / to fast)",
                    "दोष": "दुष् (to spoil / to be impure)",
                    "वेद": "विद् (to know)"
                }
                
                dhatu_found = False
                for key, root in dhatu_dict.items():
                    if key in word_to_analyze:
                        st.success(f"**Root identified:** {root}")
                        dhatu_found = True
                        break
                
                if not dhatu_found:
                    st.success("Awaiting root identification in local database...") 
                
            with col_g2:
                st.markdown("### 🏷️ 3. Shabdaroopa (Noun Case / Vibhakti)")
                # Rule-based Vibhakti identification based on suffixes
                if word_to_analyze.endswith("त्") or word_to_analyze.endswith("त"):
                    st.warning("**Panchami Vibhakti (Ablative Case)**\n\n*Meaning:* 'From' or 'Because of' (e.g., Because of the Dosha)")
                elif word_to_analyze.endswith("स्य"):
                    st.warning("**Shashti Vibhakti (Genitive Case)**\n\n*Meaning:* 'Of' or 'Belonging to' (e.g., Of the Dosha)")
                elif word_to_analyze.endswith("म्") or word_to_analyze.endswith("ं"):
                    st.warning("**Dvitiya Vibhakti (Accusative Case)**\n\n*Meaning:* Object of the action (e.g., To the Dosha)")
                elif word_to_analyze.endswith("े"):
                    st.warning("**Saptami Vibhakti (Locative Case)**\n\n*Meaning:* 'In', 'On', or 'At' (e.g., In the fever)")
                elif word_to_analyze.endswith("ेन"):
                    st.warning("**Tritiya Vibhakti (Instrumental Case)**\n\n*Meaning:* 'By' or 'With' (e.g., With the Dosha)")
                elif word_to_analyze.endswith("ाय"):
                    st.warning("**Chaturthi Vibhakti (Dative Case)**\n\n*Meaning:* 'For' (e.g., For the Dosha)")
                else:
                    st.warning("**Prathama Vibhakti (Nominative Case) / Unidentified**\n\n*Meaning:* Subject of the sentence")
                
                st.markdown("### 📖 4. Integrated Sanskrit Dictionary")
                
                search_term = word_to_analyze.replace("ात्", "").replace("स्य", "").replace("म्", "").replace("े", "").replace("ेन", "").replace("ाय", "")
                
                st.info(f"Fetching classical definition for root: **{search_term}**")
                
                # Call our new Python scraper instead of opening a link
                dictionary_result = fetch_native_dictionary(search_term)
                
                if dictionary_result:
                    # Display it cleanly in a nice UI box
                    st.success("**Definition Found:**")
                    st.write(dictionary_result)
                    
                    # Option to save it to your own database
                    if st.button("Save to My Clinical Dictionary"):
                        st.write("*(Ready to push to Firebase Amarakosha database)*")
                else:
                    st.error(f"No definition found for '{search_term}'.")
                    
                st.markdown("<hr style='margin-top: 15px; margin-bottom: 15px;'>", unsafe_allow_html=True)
                
                with st.expander("View Local Firebase Amarakosha Notes"):
                    try:
                        amarakosha_ref = db.collection("amarakosha").where("word", "==", search_term).stream()
                        found_in_db = False
                        for doc in amarakosha_ref:
                            data = doc.to_dict()
                            st.write(f"**Synonyms (Paryaya):** {data.get('synonyms', 'None listed')}")
                            st.write(f"**Category (Varga):** {data.get('varga', 'Unknown')}")
                            found_in_db = True
                            
                        if not found_in_db:
                            st.caption(f"No entry found in local cloud dictionary for root: **{search_term}**")
                    except Exception as e:
                        st.caption("Database connection ready. Add an 'amarakosha' collection to Firebase to enable local notes.")

    # --- 3. MAIN NAVIGATION ---
def main():
    # If you already have st.set_page_config at the very top of your file, you can remove this next line to avoid a duplicate error. Otherwise, keep it here.
    st.set_page_config(page_title="Ayurveda Clinic Portal", layout="wide") 
    
    st.sidebar.title("Navigation")
    menu = ["Home & Booking", "Consultant Login", "Student Corner"]
    choice = st.sidebar.radio("Go to:", menu)

    if choice == "Home & Booking":
        home_page()
    elif choice == "Consultant Login":
        consultant_portal()
    elif choice == "Student Corner":
        student_portal()

if __name__ == '__main__':
    main()