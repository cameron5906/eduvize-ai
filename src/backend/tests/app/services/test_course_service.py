import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import uuid
from app.services.course_service import CourseService
from domain.dto.courses import CoursePlanDto, CourseProgressionDto, CourseListingDto
from domain.dto.profile import UserProfileDto
from domain.enums.course_enums import CourseMotivation, CurrentSubjectExperience, CourseMaterial
from common.storage import StoragePurpose
from domain.schema.courses import Course, Lesson, Module, Section
from domain.topics import CourseGenerationTopic
from common.messaging.topics import Topic
from ai.prompts.course_generation.models import CourseOutline, ModuleOutline, LessonOutline, SectionOutline

# Sample data
user_id = "user123"
course_id = str(uuid.uuid4())
resource_id = uuid.uuid4()
plan = CoursePlanDto(
    subject="React",
    motivations=[
        CourseMotivation.CAREER.value
    ],
    experience=CurrentSubjectExperience.KNOWLEDGEABLE.value,
    materials=[CourseMaterial.READING.value],
    desired_outcome="To build a React app"
)
current_module_id = uuid.uuid4()
current_lesson_id = uuid.uuid4()
course = Course(
    id=course_id, 
    title="Sample Course", 
    description="A sample course", 
    modules=[
        Module(
            id=current_module_id,
            course_id=course_id,
            title="Module 1",
            description="Learn the basics of React",
            order=0,
            lessons=[
                Lesson(
                    id=current_lesson_id,
                    module_id=current_module_id,
                    title="Lesson 1",
                    description="Introduction to React",
                    order=0,
                    sections=[
                        Section(
                            title="Section 1",
                            description="Introduction to React",
                            content="",
                            order=0
                        )
                    ]
                )
            ]
        )    
    ], 
    current_lesson_id=current_lesson_id
)
lesson = Lesson(id=uuid.uuid4(), sections=[])
profile_dto = UserProfileDto(first_name="John", last_name="Doe")

@pytest.fixture
def course_service():
    user_service = MagicMock()
    course_repo = MagicMock()
    return CourseService(user_service=user_service, course_repo=course_repo)

@pytest.mark.asyncio
@patch("app.services.course_service.GetAdditionalInputsPrompt", autospec=True)
@patch("app.services.course_service.get_user_profile_text", autospec=True)
async def test_get_additional_inputs(mock_get_user_profile_text, mock_prompt, course_service):
    """
    Tests get_additional_inputs method:
    1. Should call user_service.get_user to validate the user.
    2. Should return the additional inputs from the prompt.
    """
    # Mock user service and profile handling
    course_service.user_service.get_user = AsyncMock(return_value=MagicMock(profile=profile_dto))
    mock_get_user_profile_text.return_value = "User Profile Text"
    
    # Mock the prompt to return additional inputs
    mock_prompt_instance = mock_prompt.return_value
    mock_prompt_instance.get_inputs.return_value = {"additional_input": "value"}
    
    result = await course_service.get_additional_inputs(user_id=user_id, plan=plan)
    
    course_service.user_service.get_user.assert_awaited_once_with("id", user_id, ["profile.*"])
    mock_prompt_instance.get_inputs.assert_called_once_with(plan=plan, profile_text="User Profile Text")
    
    assert result == {"additional_input": "value"}

@pytest.mark.asyncio
@patch("app.services.course_service.import_from_url", autospec=True)
@patch("app.services.course_service.get_public_object_url", autospec=True)
@patch("app.services.course_service.GenerateCourseOutlinePrompt", autospec=True)
@patch("app.services.course_service.get_user_profile_text", autospec=True)
@patch("app.services.course_service.kafka_producer", autospec=True)
async def test_generate_course(mock_kafka_producer, mock_get_user_profile_text, mock_generate_course_outline_prompt, mock_get_public_object_url, mock_import_from_url, course_service):
    """
    Tests generate_course method:
    1. Should call user_service.get_user to validate the user.
    2. Should generate the course outline.
    3. Should create the course in the repository and send a message to Kafka.
    """
    # Mock user service and profile handling
    course_service.user_service.get_user = AsyncMock(return_value=MagicMock(profile=profile_dto))
    
    # Mock the outline
    mock_outline = CourseOutline(
        course_subject=plan.subject, 
        course_title="A React Course", 
        description="Learn React from scratch",
        modules=[
            ModuleOutline(
                internal_name="module1",
                title="Module 1",
                focus_area="React Basics",
                description="Learn the basics of React",
                lessons=[
                    LessonOutline(
                        internal_name="lesson1",
                        focus_area="React Basics",
                        title="Lesson 1",
                        description="Introduction to React",
                        sections=[
                            SectionOutline(
                                title="Section 1",
                                description="Introduction to React"
                            )
                        ]
                    )
                ]
            )
        ],
        key_outcomes=[]
    )
    
    # Mock the outline generation and cover image
    mock_prompt_instance = mock_generate_course_outline_prompt.return_value
    mock_prompt_instance.get_outline.return_value = mock_outline
    
    mock_import_from_url.return_value = "cover_image_object_id"
    mock_get_public_object_url.return_value = "public_cover_image_url"
    
    mock_get_user_profile_text.return_value = "User Profile Text"
    
    mock_kafka_producer.produce_message = AsyncMock()
    
    course_service.generate_cover_image = MagicMock(return_value="cover_image_url")
    
    # Mock course repository
    course_service.course_repo.create_course = MagicMock(return_value=course_id)
    
    # Call the method under test
    await course_service.generate_course(user_id=user_id, plan=plan)
    
    # Assertions
    course_service.user_service.get_user.assert_awaited_once_with("id", user_id, ["profile.*"])
    mock_prompt_instance.get_outline.assert_called_once_with(plan=plan, profile_text="User Profile Text")
    mock_import_from_url.assert_called_once()
    mock_get_public_object_url.assert_called_once_with(StoragePurpose.COURSE_ASSET, "cover_image_object_id")
    
    course_service.course_repo.create_course.assert_called_once()
    
    mock_kafka_producer.produce_message.assert_called_once_with(
        topic=Topic.GENERATE_NEW_COURSE,
        message=CourseGenerationTopic(
            course_id=uuid.UUID(course_id), 
            course_outline=mock_outline
        )
    )

@pytest.mark.asyncio
async def test_mark_section_as_completed(course_service):
    """
    Tests mark_section_as_completed method:
    1. Should return CourseProgressionDto with correct data when section is completed.
    """
    # Mock user and course
    course_service.user_service.get_user = AsyncMock(return_value=MagicMock(id=user_id))
    course_service.course_repo.get_course = MagicMock(return_value=course)
    
    # Mock repository calls to set lesson progression
    course_service.course_repo.set_current_lesson = MagicMock()
    course_service.course_repo.set_course_completion = MagicMock()
    
    result = await course_service.mark_section_as_completed(user_id=user_id, course_id=course_id)
    
    course_service.user_service.get_user.assert_awaited_once_with("id", user_id)
    course_service.course_repo.get_course.assert_called_once_with(user_id, uuid.UUID(course_id))
    
    assert isinstance(result, CourseProgressionDto)

@pytest.mark.asyncio
async def test_get_courses(course_service):
    """
    Tests get_courses method:
    1. Should return a list of CourseListingDto for the user.
    """
    # Mock user and courses
    course_service.user_service.get_user = AsyncMock(return_value=MagicMock(id=user_id))
    course_service.course_repo.get_courses = MagicMock(return_value=[course])
    
    # Mock lesson count retrieval
    course_service.course_repo.get_lesson_count = MagicMock(return_value=10)
    
    result = await course_service.get_courses(user_id=user_id)
    
    course_service.user_service.get_user.assert_awaited_once_with("id", user_id)
    course_service.course_repo.get_courses.assert_called_once_with(user_id)
    
    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], CourseListingDto)

@pytest.mark.asyncio
async def test_get_course(course_service):
    """
    Tests get_course method:
    1. Should return a specific course for the user.
    """
    # Mock user and course
    course_service.user_service.get_user = AsyncMock(return_value=MagicMock(id=user_id))
    course_service.course_repo.get_course = MagicMock(return_value=course)
    
    result = await course_service.get_course(user_id=user_id, course_id=course_id)
    
    course_service.user_service.get_user.assert_awaited_once_with("id", user_id)
    course_service.course_repo.get_course.assert_called_once_with(user_id, course_id)
    
    assert result == course

@patch("app.services.course_service.OpenAI", autospec=True)
def test_generate_cover_image(mock_openai, course_service):
    """
    Tests generate_cover_image method:
    1. Should generate an image using OpenAI and return the URL.
    """
    # Mock OpenAI response
    course_service.openai = mock_openai_instance = MagicMock()
    mock_openai_instance.images = MagicMock()
    mock_openai_instance.images.generate = MagicMock()
    mock_openai_instance.images.generate.return_value = MagicMock(data=[MagicMock(url="generated_image_url")])
    
    result = course_service.generate_cover_image(subject="Python")
    
    mock_openai_instance.images.generate.assert_called_once_with(
        model="dall-e-3",
        prompt="Icon of Python, dark background, cinema 4d, isomorphic",
        size="1024x1024",
        quality="standard",
        n=1
    )
    
    assert result == "generated_image_url"
