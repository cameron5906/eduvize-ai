import logging
from ai.prompts import GenerateModuleContentPrompt
from app.repositories import CourseRepository
from common.messaging import Topic, KafkaConsumer
from domain.topics import CourseGenerationTopic
from domain.dto.courses import CourseDto

logging.basicConfig(level=logging.INFO)

repository = CourseRepository()

consumer = KafkaConsumer(
    topic=Topic.GENERATE_NEW_COURSE,
    group_id="course_generator"
)

def calculate_total_section_count(course_outline):
    """Calculate the total number of sections in the course outline."""
    return sum(
        len(lesson.sections)
        for module in course_outline.modules
        for lesson in module.lessons
    )

def generate_course(data):
    """Generate the entire course content."""
    total_section_count = calculate_total_section_count(data.course_outline)
    current_section = [0]  # Use a list to make it mutable

    def get_total_progress():
        current_section[0] += 1
        return int((current_section[0] / total_section_count) * 100)

    # Build a new course DTO
    course_dto = CourseDto.model_construct(modules=[])

    # Generate each module as defined in the outline
    for module in data.course_outline.modules:
        module_dto = generate_module(data, module, get_total_progress)
        course_dto.modules.append(module_dto)

    # Create the course content in the database
    repository.create_course_content(
        course_id=data.course_id,
        course_dto=course_dto
    )

def generate_module(data, module, progress_callback):
    """Generate content for a single module."""
    module_prompt = GenerateModuleContentPrompt()
    module_dto = module_prompt.generate_module_content(
        course=data.course_outline,
        module=module,
        progress_cb=lambda cur_section: repository.set_generation_progress(
            course_id=data.course_id,
            progress=progress_callback()
        )
    )
    logging.info(f"Generated module '{module_dto.title}'")
    return module_dto

# Continuously iterate over incoming course generation jobs
for data, message in consumer.messages(message_type=CourseGenerationTopic):
    logging.info(f"Received course generation job: {data.course_outline.course_title}, id: {data.course_id}")
    
    try:
        generate_course(data)
        # Commit the message to the Kafka topic offset
        consumer.commit(message)
    except ValueError as e:  # TODO: This should specifically look for a course not existing rather than a generic ValueError
        logging.error(f"Failed to generate course content: {e}. Skipping...")
        consumer.commit(message)
