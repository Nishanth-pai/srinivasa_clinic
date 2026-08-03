import sqlite3

def create_database():
    # 1. This creates a new file called 'shabdakalpadruma.db' in your folder
    conn = sqlite3.connect('shabdakalpadruma.db')
    cursor = conn.cursor()

    # 2. Create a table with two columns: 'word' and 'definition'
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dictionary (
            word TEXT PRIMARY KEY,
            definition TEXT
        )
    ''')

    # 3. Add some test clinical words to the database
    sample_data = [
        ("गुण", "[Offline DB] - Quality, attribute, property, or thread."),
        ("जलदोषात्", "[Offline DB] - From the contamination of water."),
        ("ग्रन्थं", "[Offline DB] - The treatise (as an object).")
    ]

    # Insert the words, ignoring duplicates if you run the script twice
    cursor.executemany('''
        INSERT OR IGNORE INTO dictionary (word, definition)
        VALUES (?, ?)
    ''', sample_data)

    conn.commit()
    conn.close()
    print("✅ shabdakalpadruma.db successfully created!")

if __name__ == "__main__":
    create_database()