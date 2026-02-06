from reportlab.pdfgen import canvas

def create_sample_pdf(filename):
    c = canvas.Canvas(filename)
    c.drawString(100, 750, "GOVERNMENT OF INDIA")
    c.drawString(100, 730, "GST NOTICE OF DEMAND")
    c.drawString(100, 700, "Date: 06-02-2026")
    c.drawString(100, 680, "FY: 2024-25")
    c.drawString(100, 650, "This is a notice under Section 73 for unpaid taxes.")
    c.drawString(100, 630, "We observed an ITC mismatch of Rs 50,000 between GSTR-3B and GSTR-2A.")
    c.drawString(100, 610, "Please verify and pay immediately.")
    c.save()
    print(f"Created {filename}")

if __name__ == "__main__":
    create_sample_pdf("sample_notice.pdf")
