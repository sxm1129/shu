import mysql.connector

config = {
  'user': 'sxm1129',
  'password': 'hs@A1b2c3d4e5',
  'host': '39.102.122.9',
  'port': 3306,
  'database': 'sxm1129',
  'charset': 'utf8mb4'
}

def verify():
    try:
        cnx = mysql.connector.connect(**config)
        cursor = cnx.cursor()
        
        # Count books
        cursor.execute("SELECT COUNT(*) FROM books")
        book_count = cursor.fetchone()[0]
        print(f"Total books: {book_count}")
        
        # Count chapters
        cursor.execute("SELECT COUNT(*) FROM chapters")
        chapter_count = cursor.fetchone()[0]
        print(f"Total chapters: {chapter_count}")
        
        # Check metadata fields
        print("\nSample Book Metadata:")
        cursor.execute("SELECT title, book_title, author, copyright_year, last_modified FROM books LIMIT 5")
        for row in cursor:
            print(row)

        # Check content sample
        print("\nSample Chapter Content (first 100 chars):")
        cursor.execute("SELECT book_name, title, LEFT(content, 100) FROM chapters WHERE content IS NOT NULL AND content != '' LIMIT 5")
        for row in cursor:
            print(f"Book: {row[0]}, Chapter: {row[1]}")
            print(f"Content: {row[2]}...")
            print("-" * 20)

        # Books with most chapters
        print("\nTop 10 books by chapter count:")
        cursor.execute("""
            SELECT b.title, COUNT(c.id) as count 
            FROM books b 
            JOIN chapters c ON b.id = c.book_id 
            GROUP BY b.id 
            ORDER BY count DESC 
            LIMIT 10
        """)
        for title, count in cursor:
            print(f"{title}: {count}")
            
        # Check '呐喊'
        print("\nChapters for '呐喊':")
        cursor.execute("""
            SELECT c.chapter_index, c.title 
            FROM chapters c 
            JOIN books b ON c.book_id = b.id 
            WHERE b.title LIKE '%呐喊%'
            ORDER BY c.chapter_index
        """)
        for idx, title in cursor:
            print(f"{idx}: {title}")

        # Check '朝花夕拾'
        print("\nChapters for '朝花夕拾':")
        cursor.execute("""
            SELECT c.chapter_index, c.title 
            FROM chapters c 
            JOIN books b ON c.book_id = b.id 
            WHERE b.title LIKE '%朝花夕拾%'
            ORDER BY c.chapter_index
        """)
        for idx, title in cursor:
            print(f"{idx}: {title}")
            
        cursor.close()
        cnx.close()
    except mysql.connector.Error as err:
        print(err)

if __name__ == "__main__":
    verify()
