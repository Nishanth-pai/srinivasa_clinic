import sqlite3
import re
import os
import html

def extract_and_transfer():
    print("🚀 Starting data extraction from Cologne Sabda-kalpadruma...")
    
    # Define absolute paths for both databases
    base_dir = os.path.dirname(os.path.abspath(__file__))
    source_db_path = os.path.join(base_dir, 'cologne.sqlite')
    target_db_path = os.path.join(base_dir, 'shabdakalpadruma.db')
    
    try:
        # 1. Connect to the Cologne database
        source_conn = sqlite3.connect(source_db_path)
        source_cursor = source_conn.cursor()
        
        # 2. Connect to your app's database
        target_conn = sqlite3.connect(target_db_path)
        target_cursor = target_conn.cursor()
        
        # 3. Pull all words and definitions from the 'skd' table
        print("📥 Reading thousands of entries... please wait...")
        source_cursor.execute("SELECT key, data FROM skd")
        rows = source_cursor.fetchall()
        
        sql_data = []
        for row in rows:
            word = row[0]
            raw_definition = row[1]
            
            # --- CLEANING THE XML/HTML TAGS ---
            # Replace line break tags with a space so words don't mash together
            clean_def = re.sub(r'<lb/>', ' ', raw_definition)
            # Remove all other XML/HTML tags (like <H1>, <s>, <body>, etc.)
            clean_def = re.sub(r'<[^>]+>', '', clean_def)
            # Convert HTML entities (like &#x201C;) back to normal punctuation
            clean_def = html.unescape(clean_def)
            
            # Add our custom tag and prepare for insertion
            formatted_meaning = f"[Sabda-kalpadruma Offline] - {clean_def.strip()}"
            sql_data.append((word.strip(), formatted_meaning))
            
        print(f"✅ Successfully cleaned {len(sql_data)} entries!")
        print("💾 Injecting into Streamlit database...")
        
        # 4. Insert all the clean data into your app's dictionary table
        target_cursor.executemany('''
            INSERT OR REPLACE INTO dictionary (word, definition)
            VALUES (?, ?)
        ''', sql_data)
        
        target_conn.commit()
        print("🎉 Massive Data Transfer Complete! Your dictionary is fully loaded.")
        
    except FileNotFoundError:
        print("❌ Error: Could not find 'cologne.sqlite'. Did you move and rename it correctly?")
    except Exception as e:
        print(f"❌ Error during transfer: {e}")
    finally:
        # Close the connections safely
        source_conn.close()
        target_conn.close()

if __name__ == "__main__":
    extract_and_transfer()