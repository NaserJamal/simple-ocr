import pymupdf

doc = pymupdf.open("../../PDF/110-pages-text.pdf")
text = "\n".join(page.get_text() for page in doc)
open("output/output.txt", "w").write(text)
