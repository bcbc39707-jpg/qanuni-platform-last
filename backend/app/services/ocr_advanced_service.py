import logging, base64, httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

class AdvancedOCRService:
    def __init__(self):
        self.api_key = settings.GOOGLE_VISION_API_KEY
        self.endpoint = f"https://vision.googleapis.com/v1/images:annotate?key={self.api_key}"

    async def process_document(self, file_path: str) -> dict:
        if not self.api_key:
            logger.warning("Google Vision API key not configured")
            return {"text": "", "confidence": 0.0, "method": "google_vision"}

        try:
            with open(file_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")

            payload = {
                "requests": [{
                    "image": {"content": image_data},
                    "features": [{"type": "DOCUMENT_TEXT_DETECTION", "model": "builtin/latest"}],
                    "imageContext": {"languageHints": ["ar"]},
                }]
            }

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(self.endpoint, json=payload)
                response.raise_for_status()
                result = response.json()

            text_annotations = result.get("responses", [{}])[0].get("textAnnotations", [])
            if not text_annotations:
                return {"text": "", "confidence": 0.0, "method": "google_vision"}

            full_text = text_annotations[0].get("description", "")
            confidence = text_annotations[0].get("confidence", 0.95) if len(text_annotations) > 0 else 0.95

            return {
                "text": full_text.strip(),
                "confidence": round(confidence, 4),
                "method": "google_vision",
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"Google Vision API error: {e.response.status_code} - {e.response.text}")
            return {"text": "", "confidence": 0.0, "method": "google_vision"}
        except Exception as e:
            logger.error(f"Google Vision processing error: {e}")
            return {"text": "", "confidence": 0.0, "method": "google_vision"}

advanced_ocr_service = AdvancedOCRService()
