"""
Extract only .ipynb files from the BotV2-LSTM archive
This avoids extracting 100,000+ files and saves time/space
"""
import os
import subprocess

rar_file = r"C:\Users\yashw\MetaStackerBandit\BotV2-LSTM"
extract_to = r"C:\Users\yashw\MetaStackerBandit\notebooks"

# Create notebooks directory if it doesn't exist
os.makedirs(extract_to, exist_ok=True)

print(f"Looking for .ipynb files in: {rar_file}")
print(f"Will extract to: {extract_to}")
print()

# Check for 7-Zip
seven_zip_paths = [
    r"C:\Program Files\7-Zip\7z.exe",
    r"C:\Program Files (x86)\7-Zip\7z.exe"
]

seven_zip = None
for path in seven_zip_paths:
    if os.path.exists(path):
        seven_zip = path
        break

if seven_zip:
    print(f"✅ Found 7-Zip at: {seven_zip}")
    print("Extracting only .ipynb files (this will be fast!)...")
    print()
    
    # Extract only .ipynb files
    cmd = [seven_zip, "e", rar_file, "*.ipynb", f"-o{extract_to}", "-y", "-r"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Extraction successful!")
        print("\nExtracted Jupyter notebooks:")
        
        # List extracted files
        notebooks = [f for f in os.listdir(extract_to) if f.endswith('.ipynb')]
        if notebooks:
            for nb in sorted(notebooks):
                file_path = os.path.join(extract_to, nb)
                size_kb = os.path.getsize(file_path) / 1024
                print(f"  ✓ {nb} ({size_kb:.1f} KB)")
            print(f"\n📁 Files saved to: {extract_to}")
        else:
            print("  ⚠️ No .ipynb files found in archive")
    else:
        print("❌ Extraction failed")
        print(result.stderr)
else:
    print("❌ 7-Zip not found!")
    print("\nPlease install 7-Zip first:")
    print("1. Go to: https://www.7-zip.org/")
    print("2. Download 64-bit version")
    print("3. Install it")
    print("4. Run this script again")
