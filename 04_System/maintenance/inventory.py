import os
from collections import Counter

def inventory_files():
    root_dir = r"c:\Users\Paweł\Documents\GitHub\Ariadne\00_Inbox"
    extension_counts = Counter()
    
    print(f"📂 Scanning {root_dir}...")
    
    total_files = 0
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            extension_counts[ext] += 1
            total_files += 1

    print(f"\n📊 Total Files: {total_files}")
    print("\nFile Extensions:")
    for ext, count in extension_counts.most_common():
        print(f"  {ext if ext else '[No Extension]'}: {count}")

if __name__ == "__main__":
    inventory_files()
