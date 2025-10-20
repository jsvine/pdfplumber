import pdfplumber

with pdfplumber.open("./pdfs/issue-1325.pdf") as pdf:
    pdf.pages[1].to_image(150).debug_tablefinder(table_settings={}).show()