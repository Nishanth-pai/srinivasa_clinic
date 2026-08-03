import sqlite3
import json
import os

def build_local_dictionary():
    print("🚀 Starting pipeline from local dataset.json...")
    
    # 1. Look for the local file instead of an internet URL
    base_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(base_dir, 'dataset.json')
    db_path = os.path.join(base_dir, 'shabdakalpadruma.db')
    
    try:
        # 2. Open and read the local JSON file
        with open(json_path, 'r', encoding='utf-8') as file:
            dictionary_data = json.load(file)
            
        print(f"✅ Loaded {len(dictionary_data)} entries from local dataset!")
        print("💾 Injecting dataset into local SQLite database...")
        
        # 3. Connect to your local SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dictionary (
                word TEXT PRIMARY KEY,
                definition TEXT
            )
        ''')
        
        # 4. Format the data for SQLite
        sql_data = []
        for word, meaning in dictionary_data.items():
            formatted_meaning = f"[Custom Clinical Dataset] - {meaning}"
            sql_data.append((word.strip(), formatted_meaning))
            
        # 5. Insert all rows into the database at once
        cursor.executemany('''
            INSERT OR REPLACE INTO dictionary (word, definition)
            VALUES (?, ?)
        ''', sql_data)
        
        conn.commit()
        conn.close()
        
        print("🎉 Database successfully upgraded! All words are now available offline.")
        
    except FileNotFoundError:
        print("❌ Error: Could not find 'dataset.json'. Make sure it is in the same folder!")
    except Exception as e:
        print(f"❌ Error building dataset: {e}")

if __name__ == "__main__":
    build_local_dictionary()