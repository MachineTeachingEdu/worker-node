from baselanguage import BaseLanguage
from pythonlang import PythonLanguage
from julialang import JuliaLanguage
from clang import CLanguage

class LanguageFactory():    #Aqui os objetos de linguagem serão criados
    
    @staticmethod
    def create_object_language(language: str) -> BaseLanguage:
        if language == "Python":
            return PythonLanguage(".py")
        elif language == "Julia":
            return JuliaLanguage(".jl")
        elif language == "C":
            return CLanguage(".c")
        else:
            raise ValueError(f"Unknown language: {language}")