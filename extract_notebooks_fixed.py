"""
Extract only .ipynb files from the BotV2-LSTM.rar archive
Fixed version - targets the .rar file correctly
"""
import os
import subprocess

rar_file = r"C:\Users\yashw\MetaStackerBandit\BotV2-LSTM.rar"  # Fixed: added .rar extension
extract_to = r"C:\Users\yashw\MetaStackerBandit\notebooks"

# Create notebooks directory if it doesn't exist
os.makedirs(extract_to, exist_ok=True)

print(f"Extracting .ipynb files from: {rar_file}")
print(f"Destination: {extract_to}")
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
    print(f"✅ Using 7-Zip: {seven_zip}")
    print("Extracting only .ipynb files...")
    print("(This extracts just the notebooks, not the entire 3.75 GB)")
    print()
    
    # Extract only .ipynb files recursively
    cmd = [seven_zip, "e", rar_file, "*.ipynb", f"-o{extract_to}", "-y", "-r"]
    
    print(f"Running command: {' '.join(cmd)}")
    print()
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Extraction complete!")
        print()
        
        # List extracted files
        notebooks = [f for f in os.listdir(extract_to) if f.endswith('.ipynb')]
        if notebooks:
            print(f"📓 Found {len(notebooks)} Jupyter notebook(s):")
            print()
            for nb in sorted(notebooks):
                file_path = os.path.join(extract_to, nb)
                size_kb = os.path.getsize(file_path) / 1024
                print(f"  ✓ {nb} ({size_kb:.1f} KB)")
            print()
            print(f"📁 Notebooks saved to: {extract_to}")
            print()
            print("Next steps:")
            print("1. Install Jupyter: pip install jupyter")
            print("2. Navigate to notebooks folder: cd notebooks")
            print("3. Start Jupyter: jupyter notebook")
        else:
            print("⚠️ No .ipynb files found in the archive")
            print("The archive might not contain Jupyter notebooks")
    else:
        print("❌ Extraction failed")
        print("Error output:")
        print(result.stderr)
else:
    print("❌ 7-Zip not found!")
    print("Please install 7-Zip from: https://www.7-zip.org/")
