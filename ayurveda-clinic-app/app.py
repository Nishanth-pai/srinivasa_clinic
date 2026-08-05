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
import os
import sqlite3
from indic_transliteration import sanscript

# Streamlit requires page config to be the very first command
st.set_page_config(page_title="Ayurveda Clinic Portal", layout="wide") 

# --- 1. FIREBASE SETUP ---
if not firebase_admin._apps:
    firebase_credentials = dict(st.secrets["firebase"])
    cred = credentials.Certificate(firebase_credentials)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# --- 2. PAGE FUNCTIONS ---
def home_page():
    st.title("🌿 Ayurveda Clinic & Wellness")
    st.write("Welcome to our holistic healing center. We specialize in traditional Ayurvedic treatments, Kaya Chikitsa, and Panchakarma therapies.")
    st.divider()
    
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

def live_waiting_room_module():
    st.header("⏳ Live Waiting Room Queue")
    
    try:
        patients_ref = db.collection("patients").where("status", "==", "Waiting").order_by("timestamp")
        docs = patients_ref.stream()
        
        waiting_count = 0
        
        for doc in docs:
            waiting_count += 1
            data = doc.to_dict()
            doc_id = doc.id
            
            name = data.get('name', 'Unknown')
            age = data.get('age', 'N/A')
            phone = data.get('phone', 'N/A')
            initial_address = data.get('address', '') 
            initial_complaint = data.get('chief_complaints', '') 
            
            with st.expander(f"🩺 Patient: {name} (Age: {age} | Contact: {phone})"):
                with st.form(key=f"clinical_form_{doc_id}"):
                    
                    st.subheader("Patient Details & Vitals")
                    
                    # Visible and pre-filled in the Consultant Dashboard
                    address = st.text_area("Address", value=initial_address)
                    
                    v1, v2, v3, v4 = st.columns(4)
                    bp = v1.text_input("BP (e.g. 120/80)")
                    weight = v2.number_input("Weight (kg)", min_value=0.0, step=0.1)
                    temp = v3.number_input("Temp (°F)", value=98.6, step=0.1)
                    pulse = v4.number_input("Pulse (bpm)", min_value=0, step=1)
                    
                    st.divider()
                    st.subheader("Consultation Notes")
                    
                    chief_complaints = st.text_area("Chief Complaints", value=initial_complaint) 
                    
                    co_morbidities = st.text_area("Co-morbidities")
                    examinations = st.text_area("Examinations")
                    investigations = st.text_area("Investigations Notes")
                    diagnosis = st.text_input("Diagnosis")
                    prescription = st.text_area("Prescription")
                    
                    diagnostic_files = st.file_uploader("Upload Diagnostics (PDF/Images)", type=['pdf', 'png', 'jpg'], accept_multiple_files=True)
                    
                    # Two separate buttons for complete control
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        complete_consultation = st.form_submit_button("Save Full Profile & Complete Consultation", type="primary")
                    with col_btn2:
                        delete_patient = st.form_submit_button("❌ Delete Patient from Queue")
                    
                    if complete_consultation:
                        db.collection("patients").document(doc_id).update({
                            "address": address,
                            "bp": bp, "weight": weight, "temp": temp, "pulse": pulse,
                            "chief_complaints": chief_complaints,
                            "co_morbidities": co_morbidities,
                            "examinations": examinations,
                            "investigations": investigations,
                            "diagnosis": diagnosis,
                            "prescription": prescription,
                            "status": "Completed"
                        })
                        st.success("Consultation saved to database! Refreshing queue...")
                        st.rerun()
                        
                    if delete_patient:
                        db.collection("patients").document(doc_id).delete()
                        st.warning(f"Patient {name} has been removed from the database.")
                        st.rerun()
                        
        if waiting_count == 0:
            st.info("The waiting room is currently empty.")
            
    except Exception as e:
        st.error(f"Error fetching waiting room data: {e}")


def consultant_portal():
    st.header("Consultant Dashboard")
    
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        st.subheader("Please Log In")
        email = st.text_input("Email", key="consultant_email_login")
        password = st.text_input("Password", type="password", key="consultant_password_login")
        login_button = st.button("Login")
        
        if login_button:
            login_successful = True 
            if login_successful:
                st.session_state.logged_in = True
                st.rerun() 
                
    if st.session_state.logged_in:
        col1, col2 = st.columns([0.85, 0.15])
        with col1:
            st.success("Authentication successful. Welcome to the Consultant Dashboard.")
        with col2:
            if st.button("Logout"):
                st.session_state.logged_in = False
                st.rerun()
                
        # --- UNIFIED NAVIGATION BAR ---
        tab1, tab2, tab3, tab4 = st.tabs([
            "📝 Registration", 
            "⏳ Live Waiting Room", 
            "🔍 Search Database", 
            "📊 Clinic Statistics"
        ])

        with tab1:
            patient_registration_module()
            
        with tab2:
            live_waiting_room_module()
            
        with tab3:
            st.subheader("Search Patients")
            
            docs = db.collection("patients").where("status", "==", "Completed").stream()
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

        with tab4:
            st.subheader("📊 Clinic Statistics & Export")
            
            st.markdown("### 📅 Select Parameters & Date Range")
            col_d1, col_d2 = st.columns(2)
            start_date = col_d1.date_input("Start Date", value=pd.to_datetime("today") - pd.DateOffset(days=30))
            end_date = col_d2.date_input("End Date", value=pd.to_datetime("today"))
            
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
                        
                    for v in data.get('visits', []):
                        v_date = v.get('date', '')
                        if start_str <= v_date <= end_str:
                            records.append({
                                "Date": v_date,
                                "Patient Name": data.get('name', 'Unknown'),
                                "Age": data.get('age', 0),
                                "Phone": data.get('phone', ''),
                                "Diagnosis": v.get('diagnosis', '').strip().title(),
                                "Weight (kg)": None, 
                                "Pulse (bpm)": None, 
                                "BP": None,
                                "Visit Type": "Follow-up"
                            })
                            
                st.session_state.export_df = pd.DataFrame(records)
                st.session_state.show_stats = True

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
                    st.markdown("### 💾 Export Data")
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
    Handles traditional dandas (।, ॥), English pipes (|), and standard line breaks.
    """
    normalized_text = verse_text.replace("॥", "।").replace("\n", "।").replace("|", "।")
    raw_padas = [p.strip() for p in normalized_text.split("।") if p.strip()]
    structured_padas = {}
    for i, pada in enumerate(raw_padas):
        structured_padas[f"Pada {i+1}"] = pada
    return structured_padas

def get_prosody_details(pada_text):
    clean_text = pada_text.replace(" ", "")
    syllables = []
    temp = ""
    
    for i, char in enumerate(clean_text):
        temp += char
        if i + 1 < len(clean_text):
            next_char = clean_text[i+1]
            if next_char not in ['ा', 'ि', 'ी', 'ु', 'ू', 'ृ', 'ॄ', 'े', 'ै', 'ो', 'ौ', 'ं', 'ः', '्'] and char != '्':
                syllables.append(temp)
                temp = ""
        else:
            syllables.append(temp)
            
    guru_markers = ['ा', 'ी', 'ू', 'े', 'ै', 'ो', 'ौ', 'ं', 'ः']
    pattern = []
    
    for idx, syl in enumerate(syllables):
        is_guru = False
        if any(m in syl for m in guru_markers):
            is_guru = True
        if idx + 1 < len(syllables) and '्' in syllables[idx+1]:
            is_guru = True
        pattern.append("S" if is_guru else "I")
        
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
    html = "<div style='display: flex; flex-wrap: wrap; margin-bottom: 15px;'>"
    for i in range(0, len(syllables), 3):
        chunk_syl = syllables[i:i+3]
        chunk_pat = pattern[i:i+3]
        html += "<div style='display: flex; border: 2px solid #bdc3c7; border-radius: 8px; padding: 5px; margin-right: 12px; margin-bottom: 10px; background-color: #f9fbfd;'>"
        for syl, mark in zip(chunk_syl, chunk_pat):
            color = "#e74c3c" if mark == 'S' else "#3498db"
            html += f"<div style='display: flex; flex-direction: column; align-items: center; padding: 0 8px; font-family: sans-serif;'><span style='font-size: 16px; font-weight: bold; color: {color};'>{mark}</span><span style='font-size: 22px; color: #2c3e50;'>{syl}</span></div>"
        html += "</div>"
    html += "</div>"
    return html

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'shabdakalpadruma.db')

@st.cache_data(show_spinner=False, ttl=86400)
def fetch_native_dictionary(word):
    try:
        slp1_word = sanscript.transliterate(word, sanscript.DEVANAGARI, sanscript.SLP1)
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT definition FROM dictionary WHERE word = ? OR word = ?", (word, slp1_word))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            raw_text = result[0]
            if raw_text.startswith("[Sabda-kalpadruma Offline]"):
                parts = raw_text.split(" - ", 1)
                if len(parts) > 1:
                    tag = parts[0]
                    slp1_definition = parts[1]
                    devanagari_def = sanscript.transliterate(slp1_definition, sanscript.SLP1, sanscript.DEVANAGARI)
                    return f"{tag} - {devanagari_def}"
            return raw_text
        else:
            return None
    except Exception as e:
        return f"Database Error: {e}"
    
@st.cache_data(show_spinner=False, ttl=86400)
def analyze_dhatu_pratyaya(word):
    try:
        from indic_transliteration import sanscript
        slp1_word = sanscript.transliterate(word, sanscript.DEVANAGARI, sanscript.SLP1)
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT dhatu, pratyaya, meaning FROM grammar WHERE word = ? OR word = ?", (word, slp1_word))
        local_result = cursor.fetchone()
        conn.close()
        
        if local_result:
            return {
                "dhatu": f"{local_result[0]} [Local Database]",
                "pratyaya": local_result[1],
                "meaning": local_result[2]
            }
    except Exception as e:
        st.error(f"Local DB Error: {e}")

    try:
        from sanskrit_parser.base.sanskrit_base import SanskritObject, DEVANAGARI
        from sanskrit_parser.parser.sandhi_analyzer import LexicalSandhiAnalyzer
        
        analyzer = LexicalSandhiAnalyzer()
        sanskrit_obj = SanskritObject(word, DEVANAGARI)
        splits = analyzer.getSandhiSplits(sanskrit_obj)
        
        if splits:
            split_paths = splits.find_all_paths(1) 
            if split_paths:
                split_result = str(split_paths[0])
                return {
                    "dhatu": f"{word} [Algorithmic Split]",
                    "pratyaya": "sanskrit_parser output",
                    "meaning": split_result
                }
                
        return {
            "dhatu": f"{word} [Unrecognized]",
            "pratyaya": "N/A",
            "meaning": "No local breakdown found and algorithm could not split."
        }
    except Exception as e:
        return {
            "dhatu": "Engine Loading",
            "pratyaya": "N/A",
            "meaning": f"The offline parser is still initializing or downloading its base data: {e}"
        }

def student_portal():
    st.title("📚 Student Learning Corner")
    st.write("Welcome to the academic portal. Explore classical text analyses, grammar breakdowns, and clinical inventions.")
    
    tab1, tab2, tab3 = st.tabs(["Classical Text Analysis", "Real-Time Grammar", "Clinical Inventions"])
    
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
            
            known_verses = {
                "तत्र पूर्वं ज्वरे": "Detailed explanation of the mechanism of Langhana in early stages of Jvara.",
                "तस्यायुषः पुण्यतमो": "Explanation of the most sacred Veda (Ayurveda) for those seeking longevity.",
            }
            
            meaning_found = False
            for snippet, meaning in known_verses.items():
                if snippet in text_to_process:
                    st.write(meaning)
                    meaning_found = True
                    break
            
            if not meaning_found:
                st.info("The clinical meaning for this specific verse has not been added to the local database yet.")

    with tab2:
        st.markdown("### 🔍 Real-Time Grammar & Sandhi Sandbox")
        st.write("Type a combined Sanskrit word to instantly analyze its components, roots (Dhatu), and cases (Vibhakti).")
        
        st.subheader("Integrated Sanskrit Dictionary")
        word_to_analyze = st.text_input("Enter a word to parse (e.g., जलदोषात्, रामस्य, वृक्षे):").strip()
        
        if word_to_analyze:
            dictionary_meaning = fetch_native_dictionary(word_to_analyze)
            
            if dictionary_meaning:
                st.success("Definition Found:")
                st.markdown(dictionary_meaning)
                
                if st.button("Save to My Clinical Dictionary"):
                    try:
                        db.collection("amarakosha").document(word_to_analyze).set({
                            "word": word_to_analyze,
                            "definition": dictionary_meaning,
                            "source": "Sabda-kalpadruma / Monier-Williams"
                        })
                        st.toast(f"✨ '{word_to_analyze}' permanently saved to cloud!")
                    except Exception as e:
                        st.error("Failed to save to database. Check connection.")
            else:
                st.error(f"No definition found for '{word_to_analyze}'.")

        st.markdown("---")

        with st.expander("View Local Firebase Amarakosha Notes"):
            if word_to_analyze:
                try:
                    doc_ref = db.collection("amarakosha").document(word_to_analyze)
                    doc = doc_ref.get()
                    
                    if doc.exists:
                        st.info(f"📚 Cloud Entry for **{word_to_analyze}**:")
                        saved_data = doc.to_dict()
                        st.markdown(saved_data.get("definition", "No definition found."))
                    else:
                        st.write(f"No entry found in local cloud dictionary for root: {word_to_analyze}")
                except Exception as e:
                    st.write("Could not connect to Firebase to retrieve notes.")
            else:
                st.write("Type a word above to see its saved notes.")

        st.markdown("---")
        st.markdown("### ⚙️ Dhatu & Pratyaya Engine")
        
        if word_to_analyze:
            grammar_result = analyze_dhatu_pratyaya(word_to_analyze)
            
            if grammar_result:
                st.success("Grammar Breakdown Found!")
                
                col_dhatu, col_pratyaya = st.columns(2)
                with col_dhatu:
                    st.info(f"**🌱 Root (Dhatu / Pratipadika):**\n\n{grammar_result['dhatu']}")
                with col_pratyaya:
                    st.warning(f"**🧩 Suffix (Pratyaya):**\n\n{grammar_result['pratyaya']}")
                
                st.write(f"**Structural Meaning:** {grammar_result['meaning']}")
            else:
                st.info(f"Awaiting root identification in local database for: **{word_to_analyze}**")
        else:
            st.info("Type a word in the dictionary search box above to see its root and suffix breakdown.")

    with tab3:
        st.write("Future updates for clinical inventions will be placed here.")
                
def main():
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