import logging
from typing import Optional
import uuid
from fastapi import Depends
from openai import OpenAI
from app.services import UserService
from app.repositories import CourseRepository
from app.utilities.profile import get_user_profile_text
from common.messaging.topics import Topic
from config import get_openai_key
from common.storage import StoragePurpose, import_from_url, get_public_object_url
from common.messaging import KafkaProducer
from domain.schema.courses import Course, Lesson
from domain.dto.courses import CourseDto, CourseListingDto, CoursePlanDto, CourseProgressionDto
from domain.dto.profile import UserProfileDto
from domain.topics import CourseGenerationTopic
from ai.prompts import GetAdditionalInputsPrompt, GenerateCourseOutlinePrompt

kafka_producer = KafkaProducer()

class CourseService:
    user_service: UserService
    course_repo: CourseRepository
    openai: OpenAI
    
    def __init__(
        self,
        user_service: UserService = Depends(UserService),
        course_repo: CourseRepository = Depends(CourseRepository)
    ) -> None:
        self.user_service = user_service
        self.course_repo = course_repo
        self.openai = OpenAI(api_key=get_openai_key())
    
    async def get_additional_inputs(
        self, 
        user_id: str,
        plan: CoursePlanDto
    ):
        """
        Comes up with additional questions to ask the user based on basic information provided

        Args:
            user_id (str): The ID of the user
            plan (CoursePlanDto): The course plan object

        Returns:
            AdditionalInputs: An object containing additional inputs to provide to the user through the frontend
        """
        
        user = await self.user_service.get_user("id", user_id, ["profile.*"])
        
        if user is None:
            raise ValueError("User not found")
        
        profile_dto = UserProfileDto.model_validate(user.profile)
        user_profile_text = get_user_profile_text(profile_dto)
        
        prompt = GetAdditionalInputsPrompt()
        
        return prompt.get_inputs(
            plan=plan,
            profile_text=user_profile_text
        )
        
    async def generate_course(
        self,
        user_id: str,
        plan: CoursePlanDto
    ) -> None:
        """
        Generates a course outline and cover image based on requirements. Submits a message
        to a Kafka topic to generate the course content in the background.

        Args:
            user_id (str): The ID of the user
            plan (CoursePlanDto): The course plan object
        """
        
        user = await self.user_service.get_user("id", user_id, ["profile.*"])
        
        if user is None:
            raise ValueError("User not found")
        
        profile_dto = UserProfileDto.model_validate(user.profile)
        user_profile_text = get_user_profile_text(profile_dto)
        
        # Generate a course outline based on user requirements and profile
        prompt = GenerateCourseOutlinePrompt()
        outline = prompt.get_outline(
            plan=plan,
            profile_text=user_profile_text
        )

        # Construct the course DTO        
        course_dto = CourseDto.model_construct(
            title=outline.course_title,
            description=outline.description,
            cover_image_url="",
            modules=[]
        )
        
        # Generate a cover image for the course
        cover_image_url = self.generate_cover_image(outline.course_subject)
        cover_image_obj_id = await import_from_url(cover_image_url, StoragePurpose.COURSE_ASSET)
        
        # Set the cover image URL to the public URL
        course_dto.cover_image_url = get_public_object_url(StoragePurpose.COURSE_ASSET, cover_image_obj_id)
        
        course_id = self.course_repo.create_course(
            user_id=user.id, 
            course_dto=course_dto
        )
        
        kafka_producer.produce_message(
            topic=Topic.GENERATE_NEW_COURSE,
            message=CourseGenerationTopic(
                course_id=course_id,
                course_outline=outline   
            ) 
        )
        
    async def mark_section_as_completed(
        self,
        user_id: str,
        course_id: str
    ) -> CourseProgressionDto:
        user = await self.user_service.get_user("id", user_id)
        
        if user is None:
            raise ValueError("User not found")
        
        course = self.course_repo.get_course(user.id, uuid.UUID(course_id))
        
        if course is None:
            raise ValueError("Course not found")
        
        current_lesson: Optional[Lesson] = next((
            lesson
            for module in course.modules
            for lesson in module.lessons
            if lesson.id == course.current_lesson_id
        ), None)
        
        if current_lesson is None:
            raise ValueError("Current lesson not found")
        
        if course.lesson_index == len(current_lesson.sections) - 1:
            # They're finished with this lesson
            next_lesson = self.course_repo.get_next_lesson(
                course_id=course.id,
                current_lesson_id=course.current_lesson_id
            )
            
            if next_lesson is None:
                # They're finished with the course
                next_lesson_id = None
                next_section_index = 0
            else:
                # Move to section #1 of the next lesson
                next_lesson_id = next_lesson.id
                next_section_index = 0
        else:
            # There's another section to go
            next_lesson_id = course.current_lesson_id
            next_section_index = course.lesson_index + 1
        
        if next_lesson_id:
            self.course_repo.set_current_lesson(
                course_id=course.id,
                lesson_id=next_lesson_id,
                section_index=next_section_index
            )
        else:
            self.course_repo.set_course_completion(course.id)
            
        return CourseProgressionDto.model_construct(
            is_course_complete=next_lesson_id is None,
            lesson_id=next_lesson_id,
            section_index=next_section_index
        )
        
    async def get_courses(
        self,
        user_id: str
    ) -> list[CourseListingDto]:
        user = await self.user_service.get_user("id", user_id)
        
        if user is None:
            raise ValueError("User not found")
        
        courses = self.course_repo.get_courses(user.id)
        
        def calculate_progress(course: Course) -> int:
            total_lessons = self.course_repo.get_lesson_count(course.id)
            current_lesson = next((
                lesson
                for module in course.modules
                for lesson in module.lessons
                if lesson.id == course.current_lesson_id
            ), None)
            
            if current_lesson is None:
                return 0
            
            return int((current_lesson.order / total_lessons) * 100)
        
        return [
            CourseListingDto.model_construct(
                id=course.id,
                title=course.title,
                description=course.description,
                cover_image_url=course.cover_image_url,
                progress=calculate_progress(course),
                is_generating=course.is_generating,
                generation_progress=course.generation_progress
            )
            for course in courses
        ]
        
    async def get_course(
        self,
        user_id: str,
        course_id: str
    ) -> Course:
        user = await self.user_service.get_user("id", user_id)
        
        if user is None:
            raise ValueError("User not found")
        
        course = self.course_repo.get_course(user.id, course_id)
        
        if course is None:
            raise ValueError("Course not found")
        
        return course

    def generate_cover_image(self, subject: str) -> str:
        response = self.openai.images.generate(
            model="dall-e-3",
            prompt=f"Icon of {subject}, dark background, cinema 4d, isomorphic",
            size="1024x1024",
            quality="standard",
            n=1
        )
        
        return response.data[0].url