import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import tempfile

def convert_transcript_to_pdf(transcript, bot_id, company_id):
    temp_dir = tempfile.gettempdir()
    pdf_path = os.path.join(temp_dir, f"{bot_id}.pdf")
    
    c = canvas.Canvas(pdf_path, pagesize=letter)
    width, height = letter

    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, height - 50, f"company_id : {company_id}")
    c.setFont("Helvetica", 12)

    line_height = 14  
    space_between_entries = 10  
    current_y = height - 80  

    def draw_entry(start_time, speaker, text, current_y):
        c.setFont("Helvetica-Bold", 12)
        c.drawString(40, current_y, f"{start_time} | {speaker}")
        current_y -= line_height

        c.setFont("Helvetica", 12)
        text_lines = split_text(text, width - 80, c)
        for line in text_lines:
            c.drawString(40, current_y, line)
            current_y -= line_height
        
        current_y -= space_between_entries

        if current_y < 50:  
            c.showPage()
            current_y = height - 40
            c.setFont("Helvetica", 12)
        
        return current_y

    def split_text(text, max_width, canvas_obj):
        words = text.split(' ')
        lines = []
        current_line = ""

        for word in words:
            test_line = f"{current_line} {word}".strip()
            if canvas_obj.stringWidth(test_line, "Helvetica", 12) > max_width:
                lines.append(current_line)
                current_line = word
            else:
                current_line = test_line
        lines.append(current_line)

        return lines

    for entry in transcript:
        start_time = format_timestamp(entry['start_timestamp'])
        speaker = entry['speaker']
        text = entry['text']
        current_y = draw_entry(start_time, speaker, text, current_y)

    c.save()
    return pdf_path

def format_timestamp(seconds):
    minutes, seconds = divmod(seconds, 60)
    return f"{int(minutes):02}:{int(seconds):02}"
