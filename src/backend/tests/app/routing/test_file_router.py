import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, Mock

from app.routing.middleware import token_validator, user_id_extractor
from common.conversion.pdf_to_image import get_images_from_pdf_bytes
from app import app

client = TestClient(app)

@patch("app.routing.file_router.get_images_from_pdf_bytes", autospec=True)
@patch("app.routing.file_router.ResumeScannerPrompt", autospec=True)
@patch("app.routing.file_router.token_validator", autospec=True)
@pytest.mark.asyncio
async def test_get_resume_details(mock_token_validator, mock_resume_scanner, mock_get_images_from_pdf_bytes):
    """
    Tests the /files/resume endpoint:
    1. Status code is 200
    2. ResumeScannerPrompt.get_profile_data is called with the images returned from get_images_from_pdf_bytes
    3. get_images_from_pdf_bytes is called with the file content
    4. Response contains the expected profile data
    """
    
    # Override dependencies
    app.dependency_overrides[token_validator] = lambda: mock_token_validator
    app.dependency_overrides[user_id_extractor] = lambda: "mock_user_id"
    
    # Mock the output of get_images_from_pdf_bytes
    mock_get_images_from_pdf_bytes.return_value = ["image1", "image2"]
    
    # Mock the ResumeScannerPrompt.get_profile_data return value
    mock_resume_scanner_instance = mock_resume_scanner.return_value
    mock_resume_scanner_instance.get_profile_data.return_value = {
        "name": "John Doe",
        "email": "johndoe@example.com"
    }
    
    # Write out a fake file
    with open("test_resume.pdf", "wb") as file:
        file.write(b"PDF_CONTENT")
    
    # Upload a sample file to the endpoint
    with open("test_resume.pdf", "rb") as file:
        response = client.post("/api/files/resume", files={"file": ("test_resume.pdf", file, "application/pdf")})
    
    # Delete the test file
    os.remove("test_resume.pdf")
    
    # Assertions
    assert response.status_code == 200
    assert response.json() == {
        "name": "John Doe",
        "email": "johndoe@example.com"
    }
    
    # Assert that get_images_from_pdf_bytes was called with the correct file content
    mock_get_images_from_pdf_bytes.assert_called_once_with(b"PDF_CONTENT")
    
    # Assert that get_profile_data was called with the images
    mock_resume_scanner_instance.get_profile_data.assert_called_once_with(["image1", "image2"])


# If needed, you can also write an additional test to verify behavior with invalid file types
@patch("app.routing.file_router.get_images_from_pdf_bytes", autospec=True)
@patch("app.routing.file_router.token_validator", autospec=True)
@pytest.mark.asyncio
async def test_get_resume_details_invalid_file(mock_token_validator, mock_get_images_from_pdf_bytes):
    """
    Tests the /files/resume endpoint with an invalid file type:
    1. Status code is 422 (validation error)
    2. Error message should indicate invalid file
    """
    
    mock_get_images_from_pdf_bytes.return_value = ["image1", "image2"]
    
    # Override dependencies
    app.dependency_overrides[token_validator] = lambda: mock_token_validator
    app.dependency_overrides[user_id_extractor] = lambda: "mock_user_id"
    app.dependency_overrides[get_images_from_pdf_bytes] = lambda: mock_get_images_from_pdf_bytes
    
    # Write a bad file
    with open("test_image.txt", "wb") as file:
        file.write(b"text content")
    
    with open("test_image.txt", "rb") as file:
        response = client.post("/api/files/resume", files={"file": ("test_image.txt", file, "text/plain")})

    # Delete the test file
    os.remove("test_image.txt")

    # Assertions
    assert response.status_code == 400
    
