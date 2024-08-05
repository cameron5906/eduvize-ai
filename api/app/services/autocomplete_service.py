from typing import List

from ..ai.prompts.autocomplete import AutocompletePrompt
from ..common.cache import add_to_set, get_set
from ..domain.enums.autocomplete_enums import AutocompleteLibrarySubject

class AutocompleteService:
    def get_programming_languages(self, query: str) -> List[str]:
        cache_key = get_cache_key("programming-languages", query)
        existing = get_set(cache_key)
        
        if existing:
            return existing
        
        prompt_input = get_programming_languages_input(query)
        prompt = AutocompletePrompt().with_input(prompt_input)
        options = prompt.get_options()
        
        add_to_set(cache_key, options)
        
        return options
    
    def get_libraries(self, subjects: List[AutocompleteLibrarySubject], query: str) -> List[str]:        
        valid_subjects = [
            subject for subject in subjects
            if any(subject == valid_subject.value for valid_subject in AutocompleteLibrarySubject)
        ]
        
        if not valid_subjects:
            return []
        
        cache_key = get_cache_key("libraries", query)
        existing = get_set(cache_key)
        
        if existing:
            return existing
        
        prompt_input = get_library_input(subjects, query)
        prompt = AutocompletePrompt().with_input(prompt_input)
        options = prompt.get_options()
        
        add_to_set(cache_key, options)
        
        return options
    
def get_library_input(subjects: List[str], query: str) -> str:
    return f"""
libraries for {','.join(subjects)} development: {query}
"""

def get_programming_languages_input(query: str) -> str:
    return f"""
Programming languages. Correct any spelling mistakes and use the proper industry names if a synonym is used.
Do not include markdown syntaxes or other non-languages in your options.
Query: {query}
"""
    
def get_cache_key(c_type: str, query: str) -> str:
    return f"autocomplete:{c_type}:{query}"