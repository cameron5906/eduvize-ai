import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
from app.routing.middleware.token_middleware import token_validator
from app.services import AutocompleteService
from app import app

client = TestClient(app)
mock_token_validator = Mock(return_value="user_id")

@patch("app.services.AutocompleteService", autospec=True)
@pytest.mark.asyncio
async def test_get_programming_languages(mock_autocomplete_service):
    """
    Test the /autocomplete/programming-languages endpoint.

    Assertions:
    1. Ensure the correct response status code (200).
    2. Ensure the correct list of programming languages is returned in the response.
    3. Ensure the AutocompleteService.get_programming_languages method is called with the correct arguments.
    """
    # Mock the service call
    mock_autocomplete_service.get_programming_languages = Mock(return_value=["Python", "JavaScript"])

    # Override dependencies
    app.dependency_overrides[AutocompleteService] = lambda: mock_autocomplete_service
    app.dependency_overrides[token_validator] = lambda: mock_token_validator

    # Define the request parameters
    disciplines = "software,web"
    query = "py"

    response = client.get(f"/api/autocomplete/programming-languages?disciplines={disciplines}&query={query}")

    # 1. Assert the status code
    assert response.status_code == 200

    # 2. Assert the correct response data
    assert response.json() == ["Python", "JavaScript"]

    # 3. Assert that the service method was called with the correct arguments
    mock_autocomplete_service.get_programming_languages.assert_called_once_with(["software", "web"], "py")

@patch("app.services.AutocompleteService", autospec=True)
@pytest.mark.asyncio
async def test_get_library_options(mock_autocomplete_service):
    """
    Test the /autocomplete/libraries endpoint.

    Assertions:
    1. Ensure the correct response status code (200).
    2. Ensure the correct list of libraries is returned in the response.
    3. Ensure the AutocompleteService.get_libraries method is called with the correct arguments.
    """
    # Mock the service call
    mock_autocomplete_service.get_libraries = Mock(return_value=["React", "Django"])
    
    # Override dependencies
    app.dependency_overrides[AutocompleteService] = lambda: mock_autocomplete_service
    app.dependency_overrides[token_validator] = lambda: mock_token_validator

    # Define the request parameters
    subjects = "frontend,backend"
    languages = "JavaScript,Python"
    query = "dj"

    response = client.get(f"/api/autocomplete/libraries?subjects={subjects}&languages={languages}&query={query}")

    # 1. Assert the status code
    assert response.status_code == 200

    # 2. Assert the correct response data
    assert response.json() == ["React", "Django"]

    # 3. Assert that the service method was called with the correct arguments
    mock_autocomplete_service.get_libraries.assert_called_once_with(
        subjects=["frontend", "backend"], 
        languages=["JavaScript", "Python"], 
        query="dj"
    )

@patch("app.services.AutocompleteService", autospec=True)
@pytest.mark.asyncio
async def test_get_educational_institutions(mock_autocomplete_service):
    """
    Test the /autocomplete/educational-institutions endpoint.

    Assertions:
    1. Ensure the correct response status code (200).
    2. Ensure the correct list of institutions is returned in the response.
    3. Ensure the AutocompleteService.get_educational_institutions method is called with the correct query argument.
    """
    # Mock the service call
    mock_autocomplete_service.get_educational_institutions = Mock(return_value=["MIT", "Stanford"])

    # Override dependencies
    app.dependency_overrides[AutocompleteService] = lambda: mock_autocomplete_service
    app.dependency_overrides[token_validator] = lambda: mock_token_validator

    # Define the request parameters
    query = "stan"

    response = client.get(f"/api/autocomplete/educational-institutions?query={query}")

    # 1. Assert the status code
    assert response.status_code == 200

    # 2. Assert the correct response data
    assert response.json() == ["MIT", "Stanford"]

    # 3. Assert that the service method was called with the correct argument
    mock_autocomplete_service.get_educational_institutions.assert_called_once_with(query="stan")

@patch("app.services.AutocompleteService", autospec=True)
@pytest.mark.asyncio
async def test_get_educational_focus_options(mock_autocomplete_service):
    """
    Test the /autocomplete/educational-focuses endpoint.

    Assertions:
    1. Ensure the correct response status code (200).
    2. Ensure the correct list of focuses is returned in the response.
    3. Ensure the AutocompleteService.get_educational_focuses method is called with the correct school_name and query.
    """
    # Mock the service call
    mock_autocomplete_service.get_educational_focuses = Mock(return_value=["Computer Science", "Data Science"])

    # Override dependencies
    app.dependency_overrides[AutocompleteService] = lambda: mock_autocomplete_service
    app.dependency_overrides[token_validator] = lambda: mock_token_validator

    # Define the request parameters
    school_name = "MIT"
    query = "data"

    response = client.get(f"/api/autocomplete/educational-focuses?school_name={school_name}&query={query}")

    # 1. Assert the status code
    assert response.status_code == 200

    # 2. Assert the correct response data
    assert response.json() == ["Computer Science", "Data Science"]

    # 3. Assert that the service method was called with the correct arguments
    mock_autocomplete_service.get_educational_focuses.assert_called_once_with(
        school_name="MIT", 
        query="data"
    )
