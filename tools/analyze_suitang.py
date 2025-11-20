import mysql.connector
import sys

# Database configuration
config = {
    'user': 'sxm1129',
    'password': 'hs@A1b2c3d4e5',
    'host': '39.102.122.9',
    'port': '3306',
    'database': 'sxm1129',
    'charset': 'utf8mb4'
}

def analyze_suitang():
    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor(dictionary=True)

        # 1. Check Book Metadata
        print("--- Book Metadata ---")
        cursor.execute("SELECT * FROM books WHERE title = '隋唐演义'")
        book = cursor.fetchone()
        if not book:
            print("Book '隋唐演义' not found in books table!")
            return
        
        for k, v in book.items():
            print(f"{k}: {v}")
        
        book_id = book['id']

        # 2. Check Chapters Count
        print("\n--- Chapters Count ---")
        cursor.execute("SELECT COUNT(*) as count FROM chapters WHERE book_id = %s", (book_id,))
        count = cursor.fetchone()['count']
        print(f"Total Chapters: {count}")

        # 3. Check First Chapter (Preface)
        print("\n--- First Chapter (Preface) ---")
        cursor.execute("SELECT * FROM chapters WHERE book_id = %s ORDER BY id ASC LIMIT 1", (book_id,))
        first_chapter = cursor.fetchone()
        if first_chapter:
            print(f"Title: {first_chapter['title']}")
            print(f"Content Length: {len(first_chapter['content'])}")
            print(f"Content Preview: {first_chapter['content'][:100]!r}")

        # 3b. Check Real Chapter 1
        print("\n--- Real Chapter 1 ---")
        cursor.execute("SELECT * FROM chapters WHERE book_id = %s AND title LIKE '%%第一回 %%'", (book_id,))
        chap1 = cursor.fetchone()
        if chap1:
            print(f"Title: {chap1['title']}")
            content = chap1['content']
            print(f"Content Length: {len(content)}")
            print(f"Content Preview (Start): {content[:200]!r}")
            print(f"Content Preview (End): {content[-200:]!r}")

        # 3c. Check Real Chapter 2
        print("\n--- Real Chapter 2 ---")
        cursor.execute("SELECT * FROM chapters WHERE book_id = %s AND title LIKE '%%第二回 %%'", (book_id,))
        chap2 = cursor.fetchone()
        if chap2:
            print(f"Title: {chap2['title']}")
            content = chap2['content']
            print(f"Content Preview (Start): {content[:200]!r}")


        
        # 4. Check Chapter 3 (specifically mentioned in previous logs)
        print("\n--- Chapter 3 ---")
        cursor.execute("SELECT * FROM chapters WHERE book_id = %s AND title LIKE '%%第三回%%'", (book_id,))
        chap3 = cursor.fetchone()
        if chap3:
            print(f"Title: {chap3['title']}")
            content = chap3['content']
            print(f"Content Length: {len(content)}")
            print(f"Content Preview (Start): {content[:200]!r}")

        # 5. Check Random Chapter (e.g., 50)
        print("\n--- Chapter 50 ---")
        cursor.execute("SELECT * FROM chapters WHERE book_id = %s LIMIT 1 OFFSET 49", (book_id,))
        chap50 = cursor.fetchone()
        if chap50:
            print(f"Title: {chap50['title']}")
            content = chap50['content']
            print(f"Content Preview (Start): {content[:100]!r}")

        # 6. Check for Short Chapters
        print("\n--- Short Chapters (< 100 chars) ---")
        cursor.execute("SELECT * FROM chapters WHERE book_id = %s AND CHAR_LENGTH(content) < 100", (book_id,))
        short_chaps = cursor.fetchall()
        for chap in short_chaps:
            print(f"ID: {chap['id']}, Title: {chap['title']}, Content: {chap['content']!r}")

        # 7. Check Last Chapter
        print("\n--- Last Chapter ---")
        cursor.execute("SELECT * FROM chapters WHERE book_id = %s ORDER BY id DESC LIMIT 1", (book_id,))
        last_chap = cursor.fetchone()
        if last_chap:
            print(f"Title: {last_chap['title']}")
            content = last_chap['content']
            print(f"Content Length: {len(content)}")
            print(f"Content Preview (Start): {content[:200]!r}")
            print(f"Content Preview (End): {content[-200:]!r}")

        # 8. Inspect Newlines
        print("\n--- Newline Inspection (Chapter 1) ---")
        cursor.execute("SELECT content, content_length FROM chapters WHERE book_id = %s AND title LIKE '%%第一回 %%'", (book_id,))
        chap1 = cursor.fetchone()
        if chap1:
            content = chap1['content']
            db_len = chap1['content_length']
            calc_len = len(content)
            print(f"Raw Content Sample (first 500 chars): {content[:500]!r}")
            # Count occurrences of multiple newlines
            double_newlines = content.count('\n\n')
            triple_newlines = content.count('\n\n\n')
            print(f"Total length (DB column): {db_len}")
            print(f"Total length (Calculated): {calc_len}")
            print(f"Length Match: {db_len == calc_len}")
            print(f"Double newlines (\\n\\n): {double_newlines}")
            print(f"Triple newlines (\\n\\n\\n): {triple_newlines}")




    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    analyze_suitang()
