import cv2
from ultralytics import YOLO
import time

def process_video(input_path, output_path):
    model = YOLO('yolov8n.pt')
    cap = cv2.VideoCapture(input_path)
    
    stats = {
        'processing_time': 0,
        'total_frames': 0,
        'object_counts': {},
        'detections': []
    }
    
    start_time = time.time()
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*'avc1')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
            
        results = model.predict(
            source=frame,
            classes=[15],
            conf=0.3,
            verbose=False,
            device='cpu'  
        )
        
        current_detections = []
        
        if results and results[0].boxes is not None:
            for obj in results[0].boxes.cls:
                class_id = int(obj)
                class_name = model.names[class_id]  # Получаем имя класса
                stats['object_counts'][class_name] = stats['object_counts'].get(class_name, 0) + 1
                current_detections.append(class_name)
        else:
            current_detections = []
        
        stats['detections'].append({
            'frame': stats['total_frames'],
            'time': stats['total_frames'] / fps,
            'objects': current_detections.copy()
        })
        
        annotated_frame = results[0].plot()
        out.write(annotated_frame)
        stats['total_frames'] += 1
    
    stats['processing_time'] = time.time() - start_time
    
    cap.release()
    out.release()
    return stats