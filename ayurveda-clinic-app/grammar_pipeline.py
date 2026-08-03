import sqlite3
import json
import os

def build_grammar_database():
    print("🚀 Starting grammar pipeline...")
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # Pointing exactly to your existing grammar.json file!
    json_path = os.path.join(base_dir, 'grammar.json')
    db_path = os.path.join(base_dir, 'shabdakalpadruma.db')
    
    try:
        # 1. Read your existing JSON file
        with open(json_path, 'r', encoding='utf-8') as file:
            grammar_data = json.load(file)
            
        print(f"✅ Loaded {len(grammar_data)} grammatical roots from grammar.json!")
        print("💾 Injecting dataset into local SQLite database...")
        
        # 2. Connect to the existing dictionary database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 3. Create a dedicated grammar table alongside the dictionary table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS grammar (
                word TEXT PRIMARY KEY,
                dhatu TEXT,
                pratyaya TEXT,
                meaning TEXT
            )
        ''')
        
        # 4. Format the data for insertion
        sql_data = []
        for word, details in grammar_data.items():
            sql_data.append((
                word.strip(), 
                details.get("dhatu", ""), 
                details.get("pratyaya", ""), 
                details.get("meaning", "")
            ))
            
        # 5. Execute the insertion
        cursor.executemany('''
            INSERT OR REPLACE INTO grammar (word, dhatu, pratyaya, meaning)
            VALUES (?, ?, ?, ?)
        ''', sql_data)
        
        conn.commit()
        conn.close()
        
        print("🎉 Grammar Database successfully upgraded! Fast offline parsing is ready.")
        
    except FileNotFoundError:
        print("❌ Error: Could not find 'grammar.json'. Make sure it is in the same folder!")
    except Exception as e:
        print(f"❌ Error building dataset: {e}")

if __name__ == "__main__":
    build_grammar_database()