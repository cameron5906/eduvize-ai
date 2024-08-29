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

# Continuously iterate over incoming course generation jobs
for data, message in consumer.messages(message_type=CourseGenerationTopic):
    logging.info(f"Received course generation job: {data.course_outline.course_title}, id: {data.course_id}")
    
    try:
        # Build a new course DTO
        course_dto = CourseDto.model_construct(
            modules=[]
        )
        
        # Generate each module as defined in the outline
        for index, module in enumerate(data.course_outline.modules):
            # Update the overall progress of the course generation
            overall_progress = int(((index + 1) / len(data.course_outline.modules)) * 100)
            repository.set_generation_progress(
                course_id=data.course_id,
                progress=overall_progress
            )
            
            # Generate the module content
            module_prompt = GenerateModuleContentPrompt()
            module_dto = module_prompt.generate_module_content(
                course=data.course_outline,
                module=module
            )
            
            logging.info(f"Generated module '{module_dto.title}'")
            
            # Append the module to the course DTO
            course_dto.modules.append(module_dto)
            
        # Create the course content in the database
        repository.create_course_content(
            course_id=data.course_id,
            course_dto=course_dto
        )
            
        # Commit the message to the Kafka topic offset
        consumer.commit(message)
    except ValueError as e: # TODO: This should specifically look for a course not existing rather than a generic ValueError
        logging.error(f"Failed to generate course content: {e}. Skipping...")
        consumer.commit(message)