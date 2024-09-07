from fastapi import APIRouter, Depends, File, UploadFile, Response, status
from ai.prompts import ResumeScannerPrompt
from app.routing.middleware import token_validator, user_id_extractor

from common.conversion.pdf_to_image import get_images_from_pdf_bytes

router = APIRouter(
    prefix="/files",
    dependencies=[
        Depends(token_validator),
        Depends(user_id_extractor)
    ]
)

@router.post("/resume")
async def get_resume_details(file: UploadFile = File(...)):
    if not file.content_type == "application/pdf":
        return Response(status_code=status.HTTP_400_BAD_REQUEST, content="Only PDF files are supported")
    
    images = get_images_from_pdf_bytes(await file.read())
    
    return ResumeScannerPrompt().get_profile_data(images)