class BaseLanguage():   #Aqui estarão métodos comuns para todas as linguagens suportadas
    def __init__(self, langExtension:str):
        self.langExtension = langExtension
    
    def base_code_with_args(self, baseCode: str, name_file_professor: str, funcName: str, funcNameProf: str, arg, returnType = ""):
        pass
    
    def professor_code_with_args(self, professorCode: str, funcName: str, funcNameProf: str, arg, returnType = ""):
        pass
    
    def evaluate_file(self, absolute_path: str):
        pass
    
    def run_code(self, file_path: str, isProfessorCode: bool):
        pass
    
    def run_pre_process_code(self, file_path: str):
        pass
    
    def pre_process_code(self, code: str, code_path: str):
        pass
