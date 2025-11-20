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
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM books")
    book_count = cursor.fetchone()[0]
    print(f"Total books in database: {book_count}")
    
    cursor.execute("SELECT COUNT(*) FROM chapters")
    chapter_count = cursor.fetchone()[0]
    print(f"Total chapters in database: {chapter_count}")
    
    cursor.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
