import pymupdf

doc = pymupdf.open("PDF/1-page-text-img.pdf")
text = "\n".join(page.get_text() for page in doc)
open("output.txt", "w").write(text)
