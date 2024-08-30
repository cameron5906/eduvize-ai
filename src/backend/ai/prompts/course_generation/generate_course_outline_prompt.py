import logging
from ai.prompts.base_prompt import BasePrompt
from domain.dto.courses.course_plan import CoursePlanDto
from .provide_course_outline_tool import ProvideCourseOutlineTool
from ai.prompts.course_planning.get_additional_inputs_prompt import get_course_plan_description
from .models import CourseOutline

class GenerateCourseOutlinePrompt(BasePrompt):
    def setup(self) -> None:        
        self.set_system_prompt(f"""
You are an AI designed to create structured course syllabi based on user information and learning requests. Your task is to generate a syllabus outline that includes sections such as Introduction, Learning Objectives, Modules, Hands-On Practice/Assignments, Assessments, Resources, and Conclusion. Each module can optionally include a quiz at the end, if it makes sense, and each lesson can optionally include a hands-on exercise, such as coding or using a system shell in a sandbox environment, if it aligns with the learning objectives. These sections should contain placeholders or brief descriptions, as the detailed content will be generated by another system.
""")
    
    def get_outline(self, plan: CoursePlanDto, profile_text: str) -> CourseOutline:
        from ai.models.gpt_4o import GPT4o
        model = GPT4o()
        
        plan_text = get_course_plan_description(plan)
        
        if plan.followup_answers:
            plan_text += "\n\nFollow-up Answers:\n"
            for key, value in plan.followup_answers.items():
                if isinstance(value, list):
                    value = ", ".join(value)
                    
                plan_text += f"{key}: {value}\n"
        
        logging.info(f"Profile Text: {profile_text}")
        logging.info(f"Plan Text: {plan_text}")
        
        self.add_user_message(f"""## User Information:
{profile_text}

## Syllabus Request:
{plan_text}

Please brainstorm a high-level plan for the course syllabus. Let's start with developing the modules - the primary sections of the course.
Each module should have a clear objective and be separated by a logical progression of topics.
""".strip())
        
        # Allow the model to brainstorm modules
        model.get_responses(self)
        
        self.add_user_message(f"""
Great! Now that we have the modules, let's focus on each module's content.
Next, I would like you to generate the overall objectives for each module and create lessons that facilitate the learning process in order
to achieve those objectives. Include lesson titles and a brief overview of the content covered in each lesson.                   
""".strip())
        
        # Allow the model to come up with lessons
        model.get_responses(self)
        
        self.add_user_message(f"""
Now that we have lessons figured out, let's move on to the sections of each lesson. These can be thought of as groupings of content
that will help the student parse the information in a structured way. Each section should have a clear purpose and contribute to the overall
lesson objective. Include the title of each section and what content it will cover.                   
""".strip())
        
        # Allow the model to come up with sections
        model.get_responses(self)
        
        self.add_user_message(f"""
Finally, I would like you to generate a full course outline using the information we've collected here. Use your tool to provide a structured representation that will be given to the instructor.
Take careful consideration of the tool schema in order to provide the data in the correct format.                   
""".strip())

        # Now we force it to use the tool to produce the course outline
        self.use_tool(ProvideCourseOutlineTool, force=True)
        model.get_responses(self)
        outline_call = self.get_tool_call(ProvideCourseOutlineTool)
        
        if not outline_call.result:
            raise ValueError("No course outline was generated")
        
        return outline_call.result