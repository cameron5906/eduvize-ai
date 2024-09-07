import pytest
from unittest.mock import patch, Mock
from app.services.autocomplete_service import AutocompleteService
from domain.enums.autocomplete_enums import AutocompleteLibrarySubject

# Sample data for testing
disciplines = ["web", "mobile"]
languages = ["python", "javascript"]
valid_subjects = [AutocompleteLibrarySubject.BACKEND.value, AutocompleteLibrarySubject.DEVOPS.value]
invalid_subjects = ["data", "security"]
query = "data"
school_name = "MIT"

@pytest.mark.asyncio
@patch("app.services.autocomplete_service.get_set", autospec=True)
@patch("app.services.autocomplete_service.add_to_set", autospec=True)
@patch("app.services.autocomplete_service.AutocompletePrompt", autospec=True)
def test_get_programming_languages(mock_prompt, mock_add_to_set, mock_get_set):
    """
    Tests get_programming_languages:
    1. Should return cached data if exists in cache.
    2. Should call prompt and return options if not cached.
    """
    mock_get_set.return_value = []  # Simulate cache miss
    
    # Mock AutocompletePrompt
    mock_prompt_instance = mock_prompt.return_value
    mock_prompt_instance.with_input.return_value = mock_prompt_instance
    mock_prompt_instance.get_options.return_value = ["Python", "JavaScript"]

    service = AutocompleteService()
    
    result = service.get_programming_languages(disciplines, query)

    # Assertions
    mock_get_set.assert_called_once()
    mock_prompt_instance.with_input.assert_called_once()
    mock_prompt_instance.get_options.assert_called_once()
    mock_add_to_set.assert_called_once()
    assert result == ["Python", "JavaScript"]


@pytest.mark.asyncio
@patch("app.services.autocomplete_service.get_set", autospec=True)
@patch("app.services.autocomplete_service.add_to_set", autospec=True)
@patch("app.services.autocomplete_service.AutocompletePrompt", autospec=True)
def test_get_libraries(mock_prompt, mock_add_to_set, mock_get_set):
    """
    Tests get_libraries:
    1. Should return cached data if exists.
    2. Should validate subjects, call prompt, and return options.
    """
    mock_get_set.return_value = []  # Simulate cache miss
    
    # Mock AutocompletePrompt
    mock_prompt_instance = mock_prompt.return_value
    mock_prompt_instance.with_input.return_value = mock_prompt_instance
    mock_prompt_instance.get_options.return_value = ["NumPy", "Pandas"]

    service = AutocompleteService()
    
    result = service.get_libraries(valid_subjects, languages, query)

    # Assertions
    mock_get_set.assert_called_once()
    mock_prompt_instance.with_input.assert_called_once()
    mock_prompt_instance.get_options.assert_called_once()
    mock_add_to_set.assert_called_once()
    assert result == ["NumPy", "Pandas"]

@pytest.mark.asyncio
@patch("app.services.autocomplete_service.get_set", autospec=True)
@patch("app.services.autocomplete_service.add_to_set", autospec=True)
@patch("app.services.autocomplete_service.AutocompletePrompt", autospec=True)
@patch("app.services.autocomplete_service.get_library_input", autospec=True)
def test_get_libraries_mixed_subjects(mock_get_library_input, mock_prompt, mock_add_to_set, mock_get_set):
    """
    Tests get_libraries with mixed valid and invalid subjects:
    1. Should filter out invalid subjects.
    2. Should pass only valid subjects to get_library_input.
    """
    mock_get_set.return_value = []  # Simulate cache miss
    
    # Mock AutocompletePrompt
    mock_prompt_instance = mock_prompt.return_value
    mock_prompt_instance.with_input.return_value = mock_prompt_instance
    mock_prompt_instance.get_options.return_value = ["NumPy", "Pandas"]

    service = AutocompleteService()
    
    result = service.get_libraries([*valid_subjects, *invalid_subjects], languages, query)

    # Assertions
    mock_get_set.assert_called_once()
    mock_prompt_instance.with_input.assert_called_once()
    mock_prompt_instance.get_options.assert_called_once()
    mock_add_to_set.assert_called_once()
    
    # Ensure only valid subjects are passed to get_library_input
    mock_get_library_input.assert_called_once_with(valid_subjects, languages, query)
    
    assert result == ["NumPy", "Pandas"]

@pytest.mark.asyncio
@patch("app.services.autocomplete_service.get_set", autospec=True)
@patch("app.services.autocomplete_service.add_to_set", autospec=True)
@patch("app.services.autocomplete_service.AutocompletePrompt", autospec=True)
def test_get_educational_institutions(mock_prompt, mock_add_to_set, mock_get_set):
    """
    Tests get_educational_institutions:
    1. Should return cached data if exists.
    2. Should call prompt and return options if not cached.
    """
    mock_get_set.return_value = []  # Simulate cache miss
    
    # Mock AutocompletePrompt
    mock_prompt_instance = mock_prompt.return_value
    mock_prompt_instance.with_input.return_value = mock_prompt_instance
    mock_prompt_instance.get_options.return_value = ["MIT", "Harvard"]

    service = AutocompleteService()
    
    result = service.get_educational_institutions(query)

    # Assertions
    mock_get_set.assert_called_once()
    mock_prompt_instance.with_input.assert_called_once()
    mock_prompt_instance.get_options.assert_called_once()
    mock_add_to_set.assert_called_once()
    assert result == ["MIT", "Harvard"]


@pytest.mark.asyncio
@patch("app.services.autocomplete_service.get_set", autospec=True)
@patch("app.services.autocomplete_service.add_to_set", autospec=True)
@patch("app.services.autocomplete_service.AutocompletePrompt", autospec=True)
def test_get_educational_focuses(mock_prompt, mock_add_to_set, mock_get_set):
    """
    Tests get_educational_focuses:
    1. Should return cached data if exists.
    2. Should call prompt and return options if not cached.
    """
    mock_get_set.return_value = None  # Simulate cache miss
    
    # Mock AutocompletePrompt
    mock_prompt_instance = mock_prompt.return_value
    mock_prompt_instance.with_input.return_value = mock_prompt_instance
    mock_prompt_instance.get_options.return_value = ["Computer Science", "Physics"]

    service = AutocompleteService()
    
    result = service.get_educational_focuses(school_name, query)

    # Assertions
    mock_get_set.assert_called_once()
    mock_prompt_instance.with_input.assert_called_once()
    mock_prompt_instance.get_options.assert_called_once()
    mock_add_to_set.assert_called_once()
    assert result == ["Computer Science", "Physics"]
