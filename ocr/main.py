from fastapi import FastAPI, UploadFile, File, HTTPException
from paddleocr import PaddleOCR
import tempfile, os, numpy as np

app = FastAPI(title="Qanuni OCR Service")
ocr_engine = PaddleOCR(use_angle_cls=True, lang='ar', show_log=False)

@app.post("/extract")
async def extract_text(file: UploadFile = File(...), doc_id: str = ""):
    content = await file.read()
    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        result = ocr_engine.ocr(tmp_path, cls=True)
        texts, confidences = [], []
        for page in result:
            for line in page:
                texts.append(line[1][0])
                confidences.append(float(line[1][1]))
        avg_confidence = float(np.mean(confidences)) if confidences else 0.0
        return {
            "filename": file.filename,
            "text": "\n".join(texts),
            "lines_count": len(texts),
            "confidence": round(avg_confidence, 4),
            "doc_id": doc_id,
        }
    finally:
        os.unlink(tmp_path)

@app.post("/extract-advanced")
async def extract_text_advanced(file: UploadFile = File(...), doc_id: str = ""):
    content = await file.read()
    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        result = ocr_engine.ocr(tmp_path, cls=True, det_db_thresh=0.2, det_db_box_thresh=0.3, rec_batch_num=6)
        texts, confidences = [], []
        for page in result:
            for line in page:
                texts.append(line[1][0])
                confidences.append(float(line[1][1]))
        avg_confidence = float(np.mean(confidences)) if confidences else 0.0
        return {
            "filename": file.filename,
            "text": "\n".join(texts),
            "lines_count": len(texts),
            "confidence": round(avg_confidence, 4),
            "doc_id": doc_id,
        }
    finally:
        os.unlink(tmp_path)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "ocr"}
