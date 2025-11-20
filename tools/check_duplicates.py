import mysql.connector

config = {
    'user': 'sxm1129',
    'password': 'hs@A1b2c3d4e5',
    'host': '39.102.122.9',
    'port': '3306',
    'database': 'sxm1129',
    'charset': 'utf8mb4'
}

try:
    conn = mysql.connector.connect(**config)
    cursor = conn.cursor(dictionary=True)
    
    # Check for duplicate titles
    cursor.execute("""
        SELECT title, COUNT(*) as count 
        FROM books 
        GROUP BY title 
        HAVING count > 1
        ORDER BY count DESC
    """)
    
    duplicates = cursor.fetchall()
    
    if duplicates:
        print(f"Found {len(duplicates)} duplicate book titles:")
        for dup in duplicates:
            print(f"  - '{dup['title']}': {dup['count']} times")
    else:
        print("No duplicate book titles found.")
    
    # Check for duplicate filenames
    cursor.execute("""
        SELECT filename, COUNT(*) as count 
        FROM books 
        GROUP BY filename 
        HAVING count > 1
        ORDER BY count DESC
    """)
    
    dup_files = cursor.fetchall()
    
    if dup_files:
        print(f"\nFound {len(dup_files)} duplicate filenames:")
        for dup in dup_files:
            print(f"  - '{dup['filename']}': {dup['count']} times")
    else:
        print("\nNo duplicate filenames found.")
    
    cursor.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
