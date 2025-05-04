from flask import Flask, request, send_file, render_template, redirect, url_for, json
import os
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from video_processor import process_video
import json as pyjson
import pandas as pd
from reportlab.pdfgen import canvas
import shutil

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///history.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class ProcessingHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(120))
    stats = db.Column(db.Text)
    processed_filename = db.Column(db.String(120))
    upload_date = db.Column(db.DateTime)
    
    @property
    def parsed_stats(self):
        import json
        return json.loads(self.stats)  # Десериализуем JSON

with app.app_context():
    db.create_all()
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    history = ProcessingHistory.query.order_by(ProcessingHistory.upload_date.desc()).all()
    return render_template('upload.html', history=history)

@app.route('/upload', methods=['POST'])
def handle_upload():
    try:
        file = request.files['video']
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        
        input_filename = f"input_{timestamp}.mp4"
        output_filename = f"output_{timestamp}.mp4"
        
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], input_filename)
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
        
        file.save(input_path)
        stats = process_video(input_path, output_path)
        
        processed_dir = os.path.join(app.static_folder, 'processed')
        os.makedirs(processed_dir, exist_ok=True)
        final_path = os.path.join(processed_dir, output_filename)
        shutil.move(output_path, final_path)

        new_record = ProcessingHistory(
            filename=file.filename,
            stats=json.dumps(stats),
            processed_filename=output_filename,
            upload_date=datetime.now()
        )
        db.session.add(new_record)
        db.session.commit()
        
        return redirect(url_for('index'))
    
    except Exception as e:
        return render_template('upload.html', error=str(e))

@app.route('/report/<int:record_id>/<format>')
def generate_report(record_id, format):
    record = ProcessingHistory.query.get(record_id)
    stats = record.parsed_stats
    
    if format == 'pdf':
        pdf_path = generate_pdf_report(record, stats)
        return send_file(pdf_path, as_attachment=True)
    elif format == 'xlsx':
        df = pd.DataFrame(stats['detections'])
        excel_path = f"report_{record_id}.xlsx"
        df.to_excel(excel_path)
        return send_file(excel_path, as_attachment=True)
    
    return "Invalid format", 400

def generate_pdf_report(record, stats):
    pdf_path = f"report_{record.id}.pdf"
    c = canvas.Canvas(pdf_path)
    
    c.drawString(100, 800, f"Video Analysis Report: {record.filename}")
    c.drawString(100, 780, f"Processing Date: {record.upload_date}")
    
    y = 750
    for obj, count in stats['object_counts'].items():
        c.drawString(100, y, f"{obj}: {count}")
        y -= 20
    
    c.save()
    return pdf_path

@app.context_processor
def inject_json():
    return dict(json=pyjson)
    
@app.context_processor
def utility_processor():
    return dict(datetime=datetime)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
