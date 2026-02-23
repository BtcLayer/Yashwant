"""
Convert HTML to PDF for MLOps intern task document.
"""

try:
    # Try using weasyprint (best quality)
    from weasyprint import HTML
    
    html_file = 'MLOps_Intern_Task.html'
    pdf_file = 'MLOps_Intern_Task.pdf'
    
    print(f"Converting {html_file} to PDF using WeasyPrint...")
    HTML(html_file).write_pdf(pdf_file)
    print(f"✅ PDF created successfully: {pdf_file}")
    
except ImportError:
    print("WeasyPrint not installed. Trying alternative method...")
    
    try:
        # Try pdfkit (requires wkhtmltopdf)
        import pdfkit
        
        html_file = 'MLOps_Intern_Task.html'
        pdf_file = 'MLOps_Intern_Task.pdf'
        
        print(f"Converting {html_file} to PDF using pdfkit...")
        pdfkit.from_file(html_file, pdf_file)
        print(f"✅ PDF created successfully: {pdf_file}")
        
    except ImportError:
        print("pdfkit not installed. Trying xhtml2pdf...")
        
        try:
            # Try xhtml2pdf
            from xhtml2pdf import pisa
            
            html_file = 'MLOps_Intern_Task.html'
            pdf_file = 'MLOps_Intern_Task.pdf'
            
            print(f"Converting {html_file} to PDF using xhtml2pdf...")
            
            with open(html_file, 'r', encoding='utf-8') as html:
                with open(pdf_file, 'wb') as pdf:
                    pisa_status = pisa.CreatePDF(html.read(), dest=pdf)
            
            if pisa_status.err:
                print(f"❌ Error creating PDF")
            else:
                print(f"✅ PDF created successfully: {pdf_file}")
                
        except ImportError:
            print("\n❌ No PDF library found!")
            print("\nPlease install one of the following:")
            print("  pip install weasyprint")
            print("  pip install pdfkit")
            print("  pip install xhtml2pdf")
            print("\nAlternatively, open MLOps_Intern_Task.html in a browser and print to PDF.")
