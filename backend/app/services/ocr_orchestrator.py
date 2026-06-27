import logging, os, httpx
from typing import Optional
from app.core.config import settings
from app.services.ocr_advanced_service import advanced_ocr_service

logger = logging.getLogger(__name__)

PADDLEOCR_URL = os.getenv("PADDLEOCR_URL", "http://ocr:8001")
CONFIDENCE_THRESHOLD = 0.80

class OCROrchestrator:
    async def process_document(self, file_path: str, doc_id: str, use_advanced: bool = False) -> dict:
        result = {"text": "", "confidence": 0.0, "method": "none", "ocr_processed": False}

        paddle_result = await self._run_paddleocr(file_path, doc_id, advanced_mode=use_advanced)

        if paddle_result and paddle_result.get("text"):
            result["text"] = paddle_result["text"]
            result["confidence"] = paddle_result.get("confidence", 0.0)
            result["method"] = "paddleocr"
            result["ocr_processed"] = True

            if paddle_result["confidence"] < CONFIDENCE_THRESHOLD and not use_advanced:
                logger.info(f"PaddleOCR confidence low ({paddle_result['confidence']}), trying Google Vision for {doc_id}")
                gv_result = await advanced_ocr_service.process_document(file_path)
                if gv_result and gv_result.get("text") and gv_result["confidence"] > paddle_result["confidence"]:
                    result["text"] = gv_result["text"]
                    result["confidence"] = gv_result["confidence"]
                    result["method"] = "google_vision"
                    logger.info(f"Google Vision produced better result for {doc_id}")
        else:
            gv_result = await advanced_ocr_service.process_document(file_path)
            if gv_result and gv_result.get("text"):
                result["text"] = gv_result["text"]
                result["confidence"] = gv_result["confidence"]
                result["method"] = "google_vision"
                result["ocr_processed"] = True

        return result

    async def process_advanced(self, file_path: str, doc_id: str) -> dict:
        return await self.process_document(file_path, doc_id, use_advanced=True)

    async def _run_paddleocr(self, file_path: str, doc_id: str, advanced_mode: bool = False) -> Optional[dict]:
        try:
            endpoint = f"{PADDLEOCR_URL}/extract-advanced" if advanced_mode else f"{PADDLEOCR_URL}/extract"
            async with httpx.AsyncClient(timeout=120) as client:
                with open(file_path, "rb") as f:
                    files = {"file": (os.path.basename(file_path), f, "application/octet-stream")}
                    response = await client.post(endpoint, files=files, params={"doc_id": doc_id})
                    response.raise_for_status()
                    return response.json()
        except httpx.ConnectError:
            logger.warning(f"PaddleOCR service not available at {PADDLEOCR_URL}")
            return None
        except Exception as e:
            logger.error(f"PaddleOCR error for {doc_id}: {e}")
            return None

ocr_orchestrator = OCROrchestrator()
