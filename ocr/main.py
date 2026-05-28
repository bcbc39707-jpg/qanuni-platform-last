from fastapi import FastAPI, UploadFile, File, HTTPException
from paddleocr import PaddleOCR
import tempfile, os

app = FastAPI(title="Qanuni OCR Service")
ocr_engine = PaddleOCR(use_angle_cls=True, lang='ar')

@app.post("/extract")
async def extract_text(file: UploadFile = File(...)):
    content = await file.read()
    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        result = ocr_engine.ocr(tmp_path, cls=True)
        texts = []
        for page in result:
            for line in page:
                texts.append(line[1][0])
        return {"filename": file.filename, "text": "\n".join(texts), "lines_count": len(texts)}
    finally:
        os.unlink(tmp_path)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "ocr"}
