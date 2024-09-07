from typing import List

from ai.prompts.autocomplete import AutocompletePrompt
from common.cache import add_to_set, get_set
from domain.enums.autocomplete_enums import AutocompleteLibrarySubject

class AutocompleteService:
    def get_programming_languages(
        self, 
        disciplines: List[str], 
        query: str
    ) -> List[str]:
        cache_key = get_cache_key("programming-languages", f"{','.join(disciplines)}:{query}")
        existing = get_set(cache_key)
        
        if existing:
            return existing
        
        prompt_input = get_programming_languages_input(disciplines, query)
        prompt = AutocompletePrompt().with_input(prompt_input)
        options = prompt.get_options()
        
        add_to_set(cache_key, options)
        
        return options
    
    def get_libraries(
        self, 
        subjects: List[str], 
        languages: List[str], 
        query: str
    ) -> List[str]:        
        valid_subjects = [
            subject for subject in subjects
            if any(subject.lower() == valid_subject.value.lower() for valid_subject in AutocompleteLibrarySubject)
        ]
        
        if not valid_subjects:
            return []
        
        cache_key = get_cache_key("libraries", f"{','.join(valid_subjects)}:{','.join(languages)}:{query}")
        existing = get_set(cache_key)
        
        if existing:
            return existing
        
        prompt_input = get_library_input(valid_subjects, languages, query)
        prompt = AutocompletePrompt().with_input(prompt_input)
        options = prompt.get_options()
        
        add_to_set(cache_key, options)
        
        return options
    
    def get_educational_institutions(
        self, 
        query: str
    ) -> List[str]:
        cache_key = get_cache_key("educational-institutions", query)
        existing = get_set(cache_key)
        
        if existing:
            return existing
        
        prompt_input = get_educational_institutions_input(query)
        prompt = AutocompletePrompt().with_input(prompt_input)
        options = prompt.get_options()
        
        add_to_set(cache_key, options)
        
        return options
    
    def get_educational_focuses(
        self, 
        school_name: str, 
        query: str
    ) -> List[str]:
        cache_key = get_cache_key("educational-focuses", f"{school_name}:{query}")
        existing = get_set(cache_key)
        
        if existing:
            return existing
        
        prompt_input = get_educational_focuses_input(school_name, query)
        prompt = AutocompletePrompt().with_input(prompt_input)
        options = prompt.get_options()
        
        add_to_set(cache_key, options)
        
        return options
    
def get_library_input(
    subjects: List[str], 
    languages: List[str], 
    query: str
) -> str:
    return f"""
Development libraries and frameworks that apply to {', or '.join(subjects)} development using {','.join(languages)}.
Query: {query}
"""

def get_programming_languages_input(
    disciplines: List[str], 
    query: str
) -> str:
    return f"""
Programming languages used for {', or '.join(disciplines)} development.
Query: {query}
"""

def get_educational_institutions_input(query: str) -> str:
    return f"""
Valid universities, colleges, bootcamps, and other educational institutions. If multiple branches exist, specify the main campus.
Query: {query}
"""

def get_educational_focuses_input(
    school_name: str, 
    query: str
) -> str:
    return f"""
Focuses of study at {school_name}. Majors, minors, concentrations, and specializations.
Query: {query}
"""
    
def get_cache_key(
    c_type: str, 
    query: str
) -> str:
    return f"autocomplete:{c_type}:{query}"