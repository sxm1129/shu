import os
import csv
import re
import mysql.connector
from mysql.connector import errorcode

# Database Configuration
config = {
  'user': 'sxm1129',
  'password': 'hs@A1b2c3d4e5',
  'host': '39.102.122.9',
  'port': 3306,
  'database': 'sxm1129',
  'charset': 'utf8mb4'
}

BOOKS_DIR = '/Users/hs/workspace/github/shu/books'
INDEX_FILE = '/Users/hs/workspace/github/shu/index.csv'
OCR_REGEX_FILE = '/Users/hs/workspace/github/shu/ill_ocr_regex.txt'

def get_db_connection():
    try:
        return mysql.connector.connect(**config)
    except mysql.connector.Error as err:
        print(f"Error connecting to database: {err}")
        exit(1)

def load_ocr_regexes():
    regexes = []
    if os.path.exists(OCR_REGEX_FILE):
        with open(OCR_REGEX_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                pattern = line.strip()
                if pattern:
                    try:
                        regexes.append(re.compile(pattern))
                    except re.error:
                        print(f"Invalid regex in ocr file: {pattern}")
    return regexes

def clean_text(text, regexes):
    for regex in regexes:
        text = regex.sub('', text)
    return text

def load_book_metadata():
    metadata = {}
    if os.path.exists(INDEX_FILE):
        with open(INDEX_FILE, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Assuming '书名' is the key for book title
                title = row.get('书名')
                if title:
                    metadata[title] = row
    return metadata

def split_chapters(content):
    # Prioritized patterns
    # High priority: Specific formats, TOC titles
    high_priority_patterns = [
        r'(^|\n)\s*正文\s+第[0-9一二三四五六七八九十百千]+回\s+.*',
        r'(^|\n)\s*第[0-9一二三四五六七八九十百千]+回\s+.*',
        r'(^|\n)\s*卷[0-9一二三四五六七八九十百千]+.*',
        r'(^|\n)\s*.*?\(\d+-.*?\)', # 呐喊 style: Title(Num-Subtitle)
    ]
    
    # Low priority: Generic numbers
    low_priority_patterns = [
        r'(^|\n)\s*Chapter\s+\d+.*',
        r'(^|\n)\s*[0-9一二三四五六七八九十百千]+\s*(\n|$)',
    ]
    
    # TOC handling
    search_start_pos = 0
    # Look for TOC header
    toc_match = re.search(r'《.*?》目录：\n(.*?)\n\n', content, re.DOTALL)
    if toc_match:
        search_start_pos = toc_match.end() # Start searching AFTER the TOC
        toc_content = toc_match.group(1)
        toc_titles = [line.strip() for line in toc_content.split('\n') if line.strip()]
        
        if toc_titles:
            # Create a pattern for TOC titles
            escaped_titles = [re.escape(t) for t in toc_titles]
            # Match title on its own line
            title_pattern = r'(^|\n)\s*(' + '|'.join(escaped_titles) + r')\s*(\n|$)'
            high_priority_patterns.append(title_pattern)

    best_matches = []
    best_pattern = None
    
    # Helper to find valid matches
    def get_valid_matches(pattern, content, start_pos):
        try:
            matches = list(re.finditer(pattern, content))
        except re.error:
            return []
        return [m for m in matches if m.start() >= start_pos]

    # Try high priority first
    for p in high_priority_patterns:
        matches = get_valid_matches(p, content, search_start_pos)
        if len(matches) > 0:
            # If we find matches with a high priority pattern, we prefer it.
            # We pick the one with the MOST matches among high priority ones.
            if len(matches) > len(best_matches):
                best_matches = matches
                best_pattern = p
    
    # If no high priority matches found (or very few?), try low priority
    # Only fall back if we found NOTHING or very few matches? 
    # Let's say if we found 0 matches.
    if not best_matches:
        for p in low_priority_patterns:
            matches = get_valid_matches(p, content, search_start_pos)
            if len(matches) > 1:
                if len(matches) > len(best_matches):
                    best_matches = matches
                    best_pattern = p
    
    chapters = []
    if best_matches:
        # Split based on matches
        for i, match in enumerate(best_matches):
            # The content before the first chapter is usually intro/preface
            if i == 0:
                start = match.start()
                # Use search_start_pos to skip TOC if present
                preface_start = search_start_pos
                if start > preface_start:
                    preface = content[preface_start:start].strip()
                    if preface:
                        chapters.append({'title': '序/前言', 'content': preface})
            
            chapter_title = match.group().strip()
            if i < len(best_matches) - 1:
                end = best_matches[i+1].start()
            else:
                end = len(content)
            
            chapter_content = content[match.end():end].strip()
            chapters.append({'title': chapter_title, 'content': chapter_content})
            
    else:
        # No chapters detected, treat as single chapter
        chapters.append({'title': '全文', 'content': content})
        
    return chapters

def process_books():
    cnx = get_db_connection()
    cursor = cnx.cursor()
    
    # Clear existing data
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    cursor.execute("TRUNCATE TABLE chapters")
    cursor.execute("TRUNCATE TABLE books")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    cnx.commit()
    
    ocr_regexes = load_ocr_regexes()
    metadata_map = load_book_metadata()
    
    # Walk through books directory
    for root, dirs, files in os.walk(BOOKS_DIR):
        for file in files:
            if not file.endswith('.txt'):
                continue
            
            try:
                file_path = os.path.join(root, file)
                filename = file
                book_title_stem = os.path.splitext(filename)[0]
                
                print(f"Processing {filename}...")
                
                # Get metadata
                meta = metadata_map.get(book_title_stem, {})
                title = meta.get('书名', book_title_stem)
                book_title = meta.get('Book Title', '')
                author = meta.get('Author', '')
                pub_date = meta.get('Publication Date', '')
                copyright_year = meta.get('Copyright Open Year', '')
                last_modified = meta.get('Last Modified', '')
                
                # Insert into books table
                add_book = ("INSERT INTO books "
                            "(filename, title, book_title, author, publication_date, copyright_year, last_modified) "
                            "VALUES (%s, %s, %s, %s, %s, %s, %s)")
                data_book = (filename, title, book_title, author, pub_date, copyright_year, last_modified)
                cursor.execute(add_book, data_book)
                book_id = cursor.lastrowid
                
                # Read content
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except UnicodeDecodeError:
                    try:
                        with open(file_path, 'r', encoding='gb18030') as f:
                            content = f.read()
                    except Exception as e:
                        print(f"Failed to read {filename}: {e}")
                        cnx.rollback()
                        continue
                
                # Clean content
                content = clean_text(content, ocr_regexes)
                
                # Split chapters
                chapters = split_chapters(content)
                
                # Insert chapters
                add_chapter = ("INSERT INTO chapters "
                               "(book_id, book_name, chapter_index, title, content, content_length) "
                               "VALUES (%s, %s, %s, %s, %s, %s)")
                
                for idx, chap in enumerate(chapters):
                    # Truncate title to 255 characters
                    chap_title = chap['title'][:255]
                    chap_content = chap['content']
                    content_len = len(chap_content)
                    data_chapter = (book_id, title, idx + 1, chap_title, chap_content, content_len)
                    cursor.execute(add_chapter, data_chapter)
                
                cnx.commit()
                print(f"Imported {filename} with {len(chapters)} chapters.")
                
            except Exception as e:
                print(f"ERROR: Failed to process {filename}: {e}")
                print(f"Skipping {filename} and continuing...")
                cnx.rollback()
                continue

    cursor.close()
    cnx.close()

if __name__ == "__main__":
    process_books()
