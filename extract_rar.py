"""
Simple script to extract RAR file using Python
"""
import os
import subprocess

rar_file = r"C:\Users\yashw\MetaStackerBandit\BotV2-LSTM.rar"
extract_to = r"C:\Users\yashw\MetaStackerBandit"

print(f"Attempting to extract: {rar_file}")
print(f"Extract to: {extract_to}")

# Try using PowerShell's Expand-Archive (works for ZIP, not RAR)
# We'll need to check if 7-Zip or WinRAR is installed

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
    print(f"Found 7-Zip at: {seven_zip}")
    print("Extracting...")
    cmd = [seven_zip, "x", rar_file, f"-o{extract_to}", "-y"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ Extraction successful!")
        print("\nExtracted files:")
        # List .ipynb files
        for file in os.listdir(extract_to):
            if file.endswith('.ipynb'):
                print(f"  - {file}")
    else:
        print("❌ Extraction failed")
        print(result.stderr)
else:
    print("❌ 7-Zip not found!")
    print("\nPlease install 7-Zip:")
    print("1. Go to: https://www.7-zip.org/")
    print("2. Download and install")
    print("3. Run this script again")
    print("\nOR manually extract:")
    print("1. Right-click on BotV2-LSTM.rar")
    print("2. Select 'Extract Here' or 'Extract All'")
