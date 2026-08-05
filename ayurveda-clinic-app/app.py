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
import streamlit as st
from indic_transliteration import sanscript


import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# --- 1. FIREBASE INITIALIZATION ---
if not firebase_admin._apps:
    cert_dict = dict(st.secrets["firebase"])
    cred = credentials.Certificate(cert_dict)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# --- 2. FRONT DESK REGISTRATION MODULE ---
def patient_registration_module():
    st.header("📝 Front Desk Registration")
    
    with st.form("registration_form", clear_on_submit=True):
        st.subheader("Demographics & Contact")
        col1, col2 = st.columns(2)
        
        with col1:
            first_name = st.text_input("First Name")
            age = st.number_input("Age", min_value=0, max_value=120, step=1)
            
        with col2:
            last_name = st.text_input("Last Name")
            contact = st.text_input("Contact Number")
            
        submitted = st.form_submit_button("Register & Send to Waiting Room")
        
        if submitted:
            if first_name and last_name:
                patient_data = {
                    "first_name": first_name.strip(),
                    "last_name": last_name.strip(),
                    "age": age,
                    "contact": contact.strip(),
                    "status": "Waiting", 
                    "timestamp": firestore.SERVER_TIMESTAMP
                }
                
                db.collection("patients").add(patient_data)
                st.success(f"✅ Patient {first_name} {last_name} is now in the waiting room!")
            else:
                st.error("Please provide at least a First and Last Name.")

# --- 3. LIVE WAITING ROOM & CONSULTATION MODULE ---
def live_waiting_room_module():
    st.header("⏳ Live Waiting Room Queue")
    
    try:
        # Query Firestore for patients waiting, ordered by arrival
        patients_ref = db.collection("patients").where("status", "==", "Waiting").order_by("timestamp")
        docs = patients_ref.stream()
        
        waiting_count = 0
        
        for doc in docs:
            waiting_count += 1
            data = doc.to_dict()
            doc_id = doc.id
            
            # Pull basic info submitted by the front desk
            name = f"{data.get('first_name', '')} {data.get('last_name', '')}"
            age = data.get('age', 'N/A')
            contact = data.get('contact', 'N/A')
            
            with st.expander(f"🩺 Patient: {name} (Age: {age} | Contact: {contact})"):
                with st.form(key=f"clinical_form_{doc_id}"):
                    
                    st.subheader("Patient Details & Vitals")
                    address = st.text_area("Address")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        bp = st.text_input("BP (e.g. 120/80)")
                    with col2:
                        weight = st.number_input("Weight (kg)", min_value=0.0, format="%.2f")
                    with col3:
                        temp = st.number_input("Temp (°F)", min_value=0.0, format="%.2f")
                    with col4:
                        pulse = st.number_input("Pulse (bpm)", min_value=0, step=1)
                        
                    st.subheader("Consultation Notes")
                    symptoms = st.text_area("Primary Symptoms & History")
                    diagnosis = st.text_input("Initial Diagnosis")
                    
                    diagnostic_files = st.file_uploader("Upload Diagnostics (PDF/Images)", type=['pdf', 'png', 'jpg'], accept_multiple_files=True)
                    
                    complete_consultation = st.form_submit_button("Save Full Profile & Complete Consultation")
                    
                    if complete_consultation:
                        db.collection("patients").document(doc_id).update({
                            "address": address,
                            "vitals": {
                                "bp": bp,
                                "weight": weight,
                                "temp": temp,
                                "pulse": pulse
                            },
                            "symptoms": symptoms,
                            "diagnosis": diagnosis,
                            "status": "Completed"
                        })
                        st.success("Consultation and full profile saved! Refreshing queue...")
                        st.rerun()
                        
        if waiting_count == 0:
            st.info("The waiting room is currently empty.")
            
    except Exception as e:
        st.error(f"Error fetching waiting room data: {e}")

# --- 4. MAIN CONSULTANT DASHBOARD NAVIGATION ---
def consultant_portal():
    st.header("Consultant Dashboard")
    
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        st.subheader("Please Log In")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        login_button = st.button("Login")
        
        if login_button:
            # Replace with your actual Firebase auth verification if needed
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
            st.header("Search Patients")
            st.info("Search functionality will render here.")
            
        with tab4:
            st.header("Clinic Statistics")
            st.info("Metrics and charts will render here.")

# --- 5. APP EXECUTION ---
if __name__ == "__main__":
    consultant_portal()


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

# 1. Define your variables at the top
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'shabdakalpadruma.db')

# 2. The upgraded dictionary function
@st.cache_data(show_spinner=False, ttl=86400)
def fetch_native_dictionary(word):
    """
    Queries the local SQLite database for the Sanskrit word.
    Translates search to SLP1, and translates the results back to Devanagari.
    """
    try:
        # Convert Devanagari input to SLP1 for the search
        slp1_word = sanscript.transliterate(word, sanscript.DEVANAGARI, sanscript.SLP1)
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT definition FROM dictionary WHERE word = ? OR word = ?", (word, slp1_word))
        result = cursor.fetchone()
        
        conn.close()
        
        if result:
            raw_text = result[0]
            
            # Check if this is an SLP1 entry from the Cologne database
            if raw_text.startswith("[Sabda-kalpadruma Offline]"):
                # Split the English tag away from the definition
                parts = raw_text.split(" - ", 1)
                if len(parts) > 1:
                    tag = parts[0]
                    slp1_definition = parts[1]
                    
                    # Translate ONLY the definition back into Devanagari
                    devanagari_def = sanscript.transliterate(slp1_definition, sanscript.SLP1, sanscript.DEVANAGARI)
                    
                    # Glue the English tag and Devanagari definition back together
                    return f"{tag} - {devanagari_def}"
            
            # If it's from your custom dataset, return it as-is
            return raw_text
        else:
            return None
            
    except Exception as e:
        return f"Database Error: {e}"
    

@st.cache_data(show_spinner=False, ttl=86400)
def analyze_dhatu_pratyaya(word):
    """
    100% Offline Hybrid Architecture:
    1. Checks local SQLite JSON database first.
    2. Uses local 'sanskrit_parser' to mathematically split compounds if missing.
    """
    # --- PHASE 1: LOCAL DB SEARCH ---
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

    # --- PHASE 2: LOCAL ALGORITHMIC PARSING ---
    try:
        # We import the local NLP tools
        from sanskrit_parser.base.sanskrit_base import SanskritObject, DEVANAGARI
        from sanskrit_parser.parser.sandhi_analyzer import LexicalSandhiAnalyzer
        
        # Initialize the offline analyzer
        analyzer = LexicalSandhiAnalyzer()
        sanskrit_obj = SanskritObject(word, DEVANAGARI)
        
        # Mathematically split the word locally
        splits = analyzer.getSandhiSplits(sanskrit_obj)
        
        if splits:
            # Grab the most mathematically probable split path
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

   

# --- PORTAL FUNCTIONS ---

def student_portal():
    st.title("📚 Student Learning Corner")
    st.write("Welcome to the academic portal. Explore classical text analyses, grammar breakdowns, and clinical inventions.")
    
    # Define the three tabs
    tab1, tab2, tab3 = st.tabs(["Classical Text Analysis", "Real-Time Grammar", "Clinical Inventions"])
    
    # ==========================================
    # --- TAB 1: VERSE ANALYSIS (PROSODY) ---
    # ==========================================
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

    # ==========================================
    # --- TAB 2: REAL-TIME GRAMMAR & DICTIONARY ---
    # ==========================================
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
                
                # --- FIREBASE SAVE BUTTON ---
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

        # --- FIREBASE RETRIEVAL EXPANDER ---
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

    # ==========================================
        # --- DHATU & PRATYAYA ENGINE UI ---
        # ==========================================
        st.markdown("---")
        st.markdown("### ⚙️ Dhatu & Pratyaya Engine")
        
        if word_to_analyze:
            grammar_result = analyze_dhatu_pratyaya(word_to_analyze)
            
            if grammar_result:
                st.success("Grammar Breakdown Found!")
                
                # Create two columns for a clean side-by-side layout
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

    # ==========================================
    # --- TAB 3: CLINICAL INVENTIONS ---
    # ==========================================
    with tab3:
        st.write("Future updates for clinical inventions will be placed here.")
                


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