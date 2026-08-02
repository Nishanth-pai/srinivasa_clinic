import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json
import requests
import pandas as pd
from datetime import datetime

# --- 1. FIREBASE INITIALIZATION ---
if not firebase_admin._apps:
    # Check if we are running on Streamlit Cloud (checking for the secret)
    if "FIREBASE_KEY" in st.secrets:
        # Load the secret string and convert it back to a dictionary
        key_dict = json.loads(st.secrets["FIREBASE_KEY"])
        cred = credentials.Certificate(key_dict)
    else:
        # Running locally on your Mac, use the physical file
        cred = credentials.Certificate('firebase_key.json')
    
    # Initialize the app with whichever credential method was chosen above
    firebase_admin.initialize_app(cred)

# Connect to the database (this stays OUTSIDE the if statement)
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
            st.subheader("📊 Clinic Statistics")
            
            # --- DATE FILTERS ---
            st.markdown("### 📅 Select Date Range")
            col_d1, col_d2 = st.columns(2)
            # Default to showing the last 30 days
            start_date = col_d1.date_input("Start Date", value=pd.to_datetime("today") - pd.DateOffset(days=30))
            end_date = col_d2.date_input("End Date", value=pd.to_datetime("today"))
            
            if st.button("Generate Dashboard"):
                all_docs = db.collection("patients").stream()
                
                total_patients = 0
                total_followups = 0
                ages = []
                diagnoses = []
                followup_dates = []
                
                # Convert standard dates to strings to match Firestore format (YYYY-MM-DD)
                start_str = start_date.strftime("%Y-%m-%d")
                end_str = end_date.strftime("%Y-%m-%d")
                
                for doc in all_docs:
                    data = doc.to_dict()
                    
                    # 1. Process Follow-ups within date range
                    visits = data.get('visits', [])
                    valid_visits = [v for v in visits if v.get('date') and start_str <= v.get('date') <= end_str]
                    total_followups += len(valid_visits)
                    
                    for v in valid_visits:
                        if v.get('diagnosis'):
                            diagnoses.append(v.get('diagnosis').strip().title())
                        if v.get('date'):
                            followup_dates.append(v.get('date')[:7])
                            
                    # 2. Process First Visits within date range (Fallback to very old date for legacy data without a stamp)
                    reg_date = data.get('registration_date', "2020-01-01")
                    
                    # A patient is included in this chart if they registered in the date range OR had a follow-up in the date range
                    if (start_str <= reg_date <= end_str) or len(valid_visits) > 0:
                        total_patients += 1
                        
                        if data.get('age'):
                            ages.append(data.get('age'))
                            
                        # Only add their primary diagnosis if they actually registered in this date window
                        if (start_str <= reg_date <= end_str) and data.get('diagnosis'):
                            diagnoses.append(data.get('diagnosis').strip().title())
                
                # --- High-Level Metrics ---
                col1, col2, col3 = st.columns(3)
                col1.metric("Patients in Range", total_patients)
                col2.metric("Follow-ups in Range", total_followups)
                col3.metric("Total Consultations", total_patients + total_followups)
                
                st.divider()
                
                # --- Charts ---
                col_chart1, col_chart2 = st.columns(2)
                
                with col_chart1:
                    st.markdown("**Age Distribution**")
                    if ages:
                        age_df = pd.DataFrame({'Age': ages})
                        bins = [0, 10, 20, 30, 40, 50, 60, 70, 80, 100]
                        labels = ['0-10', '11-20', '21-30', '31-40', '41-50', '51-60', '61-70', '71-80', '80+']
                        age_df['Age Group'] = pd.cut(age_df['Age'], bins=bins, labels=labels, right=False)
                        age_counts = age_df['Age Group'].value_counts().sort_index()
                        st.bar_chart(age_counts)
                    else:
                        st.info("No age data for this date range.")
                        
                with col_chart2:
                    st.markdown("**Most Common Diagnoses**")
                    if diagnoses:
                        diag_df = pd.DataFrame({'Diagnosis': diagnoses})
                        diag_counts = diag_df['Diagnosis'].value_counts().head(10) # Top 10
                        st.bar_chart(diag_counts)
                    else:
                        st.info("No diagnosis data for this date range.")
                
                st.divider()
                
                st.markdown("**Follow-up Visits per Month**")
                if followup_dates:
                    date_df = pd.DataFrame({'Month': followup_dates})
                    date_counts = date_df['Month'].value_counts().sort_index()
                    st.line_chart(date_counts)
                else:
                    st.info("No follow-up date data for this range.")

def student_portal():
    st.title("📚 Student Learning Corner")
    st.write("Welcome to the academic portal. Explore classical text analyses, clinical understandings, and new inventions.")
    
    tab1, tab2 = st.tabs(["Classical Text Analysis", "Clinical Inventions"])
    
    # --- TAB 1: VERSE ANALYSIS ---
    with tab1:
        st.subheader("Verse Breakdown & Prosody")
        st.write("Analyze the structure and clinical meaning of classical verses.")
        
        verse_input = st.text_area("Enter Verse (Sloka)", "तत्र पूर्वं ज्वरे कुर्याल्लङ्घनं...")
        
        if st.button("Analyze Verse"):
            st.markdown("### Structural Analysis")
            st.success("Verse successfully parsed.")
            st.write("**Pada 1:** तत्र पूर्वं ज्वरे कुर्याल्")
            st.write("**Pada 2:** लङ्घनं...")
            
            st.markdown("### Clinical Understanding")
            st.write("Detailed explanation of the mechanism of Langhana in early stages of Jvara.")

    # --- TAB 2: INVENTIONS & OBSERVATIONS ---
    with tab2:
        st.subheader("New Clinical Inventions")
        st.write("A space to document and share new formulations and clinical observations.")
        
        with st.expander("📝 Publish a new finding"):
            title = st.text_input("Title of Invention/Observation")
            content = st.text_area("Detailed Description")
            if st.button("Publish to Students"):
                st.success(f"'{title}' has been published to the learning corner!")

# --- 3. MAIN NAVIGATION ---
def main():
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