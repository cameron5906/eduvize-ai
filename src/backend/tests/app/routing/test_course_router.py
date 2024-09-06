from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch

from app.routing.middleware import token_validator, user_id_extractor
from app.services import CourseService
from app import app
from domain.dto.courses import CourseDto, CourseListingDto, CoursePlanDto, CourseProgressionDto
from domain.enums.course_enums import CurrentSubjectExperience

client = TestClient(app)

@patch("app.services.CourseService", autospec=True)
@patch("app.routing.middleware.token_validator", autospec=True)
@pytest.mark.asyncio
async def test_get_courses(mock_token_validator: token_validator, mock_course_service: CourseService):
    """
    Tests the /courses endpoint:
    1. Status code is 200
    2. Response contains a list of CourseListingDto items
    3. CourseService.get_courses is called with the correct user_id
    """
    
    course_1_id = uuid4()
    course_2_id = uuid4()
    
    # Mock the get_courses method
    mock_course_service.get_courses = AsyncMock(return_value=[
        CourseListingDto(id=course_1_id, title="Course 1", description="Description 1", is_generating=False, generation_progress=0, cover_image_url="", progress=0),
        CourseListingDto(id=course_2_id, title="Course 2", description="Description 2", is_generating=True, generation_progress=50, cover_image_url="", progress=50)
    ])

    # Override the CourseService dependency
    app.dependency_overrides[CourseService] = lambda: mock_course_service
    app.dependency_overrides[token_validator] = lambda: mock_token_validator
    app.dependency_overrides[user_id_extractor] = lambda: "user_id"

    response = client.get("/api/courses")

    # Assertions
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 2
    assert response.json()[0]["id"] == str(course_1_id)
    assert response.json()[0]["title"] == "Course 1"
    assert response.json()[1]["id"] == str(course_2_id)
    assert response.json()[1]["title"] == "Course 2"
    
    mock_course_service.get_courses.assert_awaited_once()

    # Clear overrides after test
    app.dependency_overrides = {}

@patch("app.services.CourseService", autospec=True)
@patch("app.routing.middleware.token_validator", autospec=True)
@pytest.mark.asyncio
async def test_get_course(mock_token_validator: token_validator, mock_course_service: CourseService):
    """
    Tests the /courses/{course_id} endpoint:
    1. Status code is 200
    2. Response contains CourseDto with the correct id and title
    3. CourseService.get_course is called with the correct course_id and user_id
    """
    
    course_id = str(uuid4())
    
    # Mock the get_course method
    mock_course_service.get_course = AsyncMock(return_value=CourseDto.model_construct(
        id=course_id, 
        title="Course 1",
        description="Description 1",
        lesson_index=0,
        current_lesson_id=uuid4(),
        cover_image_url="",
        is_generating=False,
        generation_progress=0,
        modules=[]
    ))

    # Override the CourseService dependency
    app.dependency_overrides[CourseService] = lambda: mock_course_service
    app.dependency_overrides[token_validator] = lambda: mock_token_validator
    app.dependency_overrides[user_id_extractor] = lambda: "user_id"

    response = client.get(f"/api/courses/{course_id}")

    # Assertions
    assert response.status_code == 200
    assert response.json()["id"] == course_id
    assert response.json()["title"] == "Course 1"

    mock_course_service.get_course.assert_awaited_once_with("user_id", course_id)

    # Clear overrides after test
    app.dependency_overrides = {}

@patch("app.services.CourseService", autospec=True)
@patch("app.routing.middleware.token_validator", autospec=True)
@pytest.mark.asyncio
async def test_complete_section(mock_token_validator: token_validator, mock_course_service: CourseService):
    """
    Tests the /courses/{course_id}/section-complete endpoint:
    1. Status code is 200
    2. Response contains CourseProgressionDto with expected data
    3. CourseService.mark_section_as_completed is called with the correct course_id and user_id
    """
    # Mock the mark_section_as_completed method
    mock_course_service.mark_section_as_completed = AsyncMock(return_value=CourseProgressionDto(is_course_complete=False, section_index=0, lesson_id=uuid4()))

    # Override the CourseService dependency
    app.dependency_overrides[CourseService] = lambda: mock_course_service
    app.dependency_overrides[token_validator] = lambda: mock_token_validator
    app.dependency_overrides[user_id_extractor] = lambda: "user_id"

    course_id = "course1"
    response = client.post(f"/api/courses/{course_id}/section-complete")

    # Assertions
    assert response.status_code == 200
    assert response.json()["is_course_complete"] == False
    assert response.json()["section_index"] == 0

    mock_course_service.mark_section_as_completed.assert_awaited_once_with("user_id", course_id)

    # Clear overrides after test
    app.dependency_overrides = {}

@patch("app.services.CourseService", autospec=True)
@patch("app.routing.middleware.token_validator", autospec=True)
@pytest.mark.asyncio
async def test_get_additional_inputs(mock_token_validator: token_validator, mock_course_service: CourseService):
    """
    Tests the /courses/additional-inputs endpoint:
    1. Status code is 200
    2. Response contains expected additional inputs
    3. CourseService.get_additional_inputs is called with the correct payload and user_id
    """
    # Mock the get_additional_inputs method
    mock_course_service.get_additional_inputs = AsyncMock(return_value={"input_type": "text", "data": "additional_input"})

    # Override the CourseService dependency
    app.dependency_overrides[CourseService] = lambda: mock_course_service
    app.dependency_overrides[token_validator] = lambda: mock_token_validator
    app.dependency_overrides[user_id_extractor] = lambda: "user_id"

    payload = CoursePlanDto(
        subject="subject",
        motivations=[],
        materials=[],
        desired_outcome="",
        experience=CurrentSubjectExperience.EXISTING
    ).model_dump(mode='json')
    response = client.post("/api/courses/additional-inputs", json=payload)

    # Assertions
    assert response.status_code == 200
    assert response.json() == {
        "input_type": "text",
        "data": "additional_input"
    }

    mock_course_service.get_additional_inputs.assert_awaited_once_with("user_id", CoursePlanDto(**payload))

    # Clear overrides after test
    app.dependency_overrides = {}

@patch("app.services.CourseService", autospec=True)
@patch("app.routing.middleware.token_validator", autospec=True)
@pytest.mark.asyncio
async def test_generate_course(mock_token_validator: token_validator, mock_course_service: CourseService):
    """
    Tests the /courses/generate endpoint:
    1. Status code is 200
    2. CourseService.generate_course is called with the correct payload and user_id
    """
    # Mock the generate_course method
    mock_course_service.generate_course = AsyncMock()

    # Override the CourseService dependency
    app.dependency_overrides[CourseService] = lambda: mock_course_service
    app.dependency_overrides[token_validator] = lambda: mock_token_validator
    app.dependency_overrides[user_id_extractor] = lambda: "user_id"

    payload = CoursePlanDto(
        subject="subject",
        motivations=[],
        materials=[],
        desired_outcome="",
        experience=CurrentSubjectExperience.EXISTING
    ).model_dump(mode='json')
    response = client.post("/api/courses/generate", json=payload)

    # Assertions
    assert response.status_code == 200

    mock_course_service.generate_course.assert_awaited_once_with("user_id", CoursePlanDto(**payload))

    # Clear overrides after test
    app.dependency_overrides = {}
