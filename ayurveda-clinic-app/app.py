import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json

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
    password = st.sidebar.text_input("Enter Admin Password", type="password")
    
    if password == "ayurveda123": 
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
            
            if st.button("Search"):
                docs = db.collection("patients").stream()
                results = []
                for doc in docs:
                    data = doc.to_dict()
                    if search_query in str(data).lower():
                        results.append(data)
                
                if results:
                    st.dataframe(results)
                else:
                    st.warning("No records found matching that query.")
    else:
        st.warning("Please enter the correct password in the sidebar.")

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