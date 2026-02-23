"""
Instructions to create PDF from HTML file.
"""

print("=" * 60)
print("PDF CREATION INSTRUCTIONS")
print("=" * 60)
print()
print("The HTML file has been created: MLOps_Intern_Task.html")
print()
print("To create a PDF, use ONE of these methods:")
print()
print("METHOD 1: Using Chrome/Edge Browser (RECOMMENDED)")
print("-" * 60)
print("1. Open MLOps_Intern_Task.html in Chrome or Edge")
print("2. Press Ctrl+P (or File > Print)")
print("3. Select 'Save as PDF' as the destination")
print("4. Click 'Save'")
print("5. Name it: MLOps_Intern_Task.pdf")
print()
print("METHOD 2: Using PowerShell (Windows)")
print("-" * 60)
print("Run this command:")
print()
print('Start-Process "MLOps_Intern_Task.html"')
print()
print("Then follow METHOD 1 steps")
print()
print("METHOD 3: Using Python with WeasyPrint")
print("-" * 60)
print("pip install weasyprint")
print("python -c \"from weasyprint import HTML; HTML('MLOps_Intern_Task.html').write_pdf('MLOps_Intern_Task.pdf')\"")
print()
print("=" * 60)
print()

# Try to open the HTML file in default browser
import os
import webbrowser

html_path = os.path.abspath('MLOps_Intern_Task.html')
print(f"Opening HTML file in browser...")
print(f"File location: {html_path}")
print()

try:
    webbrowser.open(f'file:///{html_path}')
    print("✅ HTML file opened in browser!")
    print()
    print("Next steps:")
    print("1. Press Ctrl+P to print")
    print("2. Select 'Save as PDF'")
    print("3. Save as: MLOps_Intern_Task.pdf")
except Exception as e:
    print(f"❌ Could not open browser: {e}")
    print(f"\nPlease manually open: {html_path}")

print()
print("=" * 60)
