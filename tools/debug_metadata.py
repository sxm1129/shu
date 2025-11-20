import csv
import os

INDEX_FILE = '/Users/hs/workspace/github/shu/index.csv'

def debug_metadata():
    if os.path.exists(INDEX_FILE):
        with open(INDEX_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            print(f"Field names: {reader.fieldnames}")
            for i, row in enumerate(reader):
                if i < 5:
                    print(f"Row {i}: {row}")
                if row.get('书名') == '琴笺':
                    print(f"Found 琴笺: {row}")
                    break

if __name__ == "__main__":
    debug_metadata()
