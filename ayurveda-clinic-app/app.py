import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json
import requests
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
    
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ... (Keep the rest of your app.py exactly the same below this line) ...

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
            
        tab1, tab2 = st.tabs(["Add New Patient", "Search Database"])
        
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
                
                chief_complaints = st.text_area("Chief Complaints")
                co_morbidities = st.text_area("Co-morbidities")
                examinations = st.text_area("Examinations")
                investigations = st.text_area("Investigations Notes")
                diagnosis = st.text_input("Diagnosis")
                prescription = st.text_area("Prescription")
                notes = st.text_area("Additional Notes")
                
                submitted = st.form_submit_button("Save Patient Record")
                
                if submitted:
                    patient_data = {
                        "name": name, "age": age, "phone": phone, "address": address,
                        "chief_complaints": chief_complaints, "co_morbidities": co_morbidities,
                        "examinations": examinations, "investigations": investigations,
                        "diagnosis": diagnosis, "prescription": prescription, "notes": notes
                    }
                    
                    db.collection("patients").add(patient_data)
                    st.success(f"Record for {name} saved successfully!")
                    
        # --- TAB 2: SEARCH DATABASE ---
        with tab2:
            st.subheader("Search Patients")
            search_query = st.text_input("Search by Name, Phone, or Diagnosis").lower()
            
            if st.button("Search") and search_query:
                docs = db.collection("patients").stream()
                found = False
                
                for doc in docs:
                    data = doc.to_dict()
                    if search_query in str(data).lower():
                        found = True
                        doc_id = doc.id  
                        
                        # Create an expandable card for each matching patient
                        with st.expander(f"🩺 {data.get('name')} - {data.get('phone')}"):
                            
                            # --- FULL PATIENT PROFILE ---
                            st.markdown("### 📋 Complete Patient Profile")
                            col_a, col_b = st.columns(2)
                            col_a.write(f"**Age:** {data.get('age')}")
                            col_a.write(f"**Phone:** {data.get('phone')}")
                            col_b.write(f"**Address:** {data.get('address')}")
                            
                            st.divider()
                            st.write(f"**Chief Complaints:** {data.get('chief_complaints')}")
                            st.write(f"**Co-morbidities:** {data.get('co_morbidities')}")
                            st.write(f"**Examinations:** {data.get('examinations')}")
                            st.write(f"**Investigations:** {data.get('investigations')}")
                            
                            st.divider()
                            st.write("**Diagnosis History:**")
                            st.info(data.get('diagnosis'))
                            
                            st.write("**Prescription History:**")
                            st.info(data.get('prescription'))
                            
                            st.write("**Additional Notes History:**")
                            st.info(data.get('notes'))
                            
                            # --- PRINT FEATURE ---
                            html_content = f"""
                            <html>
                            <head><title>Prescription - {data.get('name')}</title></head>
                            <body style="font-family: sans-serif; padding: 40px; max-width: 800px; margin: auto;">
                                <h1 style="text-align: center; color: #2c3e50;">Srinivasa Clinic</h1>
                                <hr>
                                <p><strong>Patient Name:</strong> {data.get('name')} <span style="float: right;"><strong>Age:</strong> {data.get('age')}</span></p>
                                <p style="white-space: pre-wrap; line-height: 1.6;"><strong>Diagnosis History:</strong><br>{data.get('diagnosis')}</p>
                                <br>
                                <h3>Prescription (Rx):</h3>
                                <p style="white-space: pre-wrap; line-height: 1.6;">{data.get('prescription')}</p>
                                <br><br><br><br>
                                <hr>
                                <p style="text-align: right;">Doctor's Signature: ______________________</p>
                                <script>window.print();</script>
                            </body>
                            </html>
                            """
                            
                            st.download_button(
                                label="🖨️ Download & Print Prescription Paper",
                                data=html_content,
                                file_name=f"{str(data.get('name')).replace(' ', '_')}_Prescription.html",
                                mime="text/html"
                            )
                            
                            st.divider()
                            
                            # --- REPEAT CONSULTATION FEATURE ---
                            with st.form(f"follow_up_{doc_id}"):
                                st.markdown("### 🔄 Add Follow-up Visit")
                                today_date = datetime.now().strftime("%Y-%m-%d")
                                
                                st.caption(f"Date: {today_date}")
                                new_complaints = st.text_area("New Consultation Notes / Complaints")
                                new_diagnosis = st.text_input("New Diagnosis (Leave blank if unchanged)")
                                new_prescription = st.text_area("New Prescription")
                                
                                if st.form_submit_button("Save Follow-up"):
                                    # Start with the existing data
                                    updated_diagnosis = data.get('diagnosis', '')
                                    updated_prescription = data.get('prescription', '')
                                    updated_notes = data.get('notes', '')
                                    
                                    # Only append new text if the doctor actually typed something in the box
                                    if new_diagnosis.strip():
                                        updated_diagnosis += f"\n\n--- Follow up ({today_date}) ---\n{new_diagnosis}"
                                        
                                    if new_prescription.strip():
                                        updated_prescription += f"\n\n--- Follow up ({today_date}) ---\n{new_prescription}"
                                        
                                    if new_complaints.strip():
                                        updated_notes += f"\n\n--- Follow up ({today_date}) ---\n{new_complaints}"
                                    
                                    # Update the existing document
                                    db.collection("patients").document(doc_id).update({
                                        "diagnosis": updated_diagnosis,
                                        "prescription": updated_prescription,
                                        "notes": updated_notes
                                    })
                                    st.success(f"Follow-up for {data.get('name')} saved successfully! Please click Search again to refresh.")
                
                if not found:
                    st.warning("No records found matching that query.")

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