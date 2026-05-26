class BaseLanguage():   #Aqui estarão métodos comuns para todas as linguagens suportadas
    def __init__(self, langExtension:str):
        self.langExtension = langExtension
    
    #Método específico de cada linguagem para formatar o código base da solução, adicionando os argumentos dos casos de teste e o código necessário para comparar a saída da solução com a saída esperada, além de capturar erros e exceções que possam ocorrer durante a execução do código.
    def base_code_with_args(self, baseCode: str, name_file_professor: str, funcName: str, funcNameProf: str, arg, returnType = ""):
        pass
    
    #Método específico de cada linguagem para formatar o código enviado no momento da criação do problema, adicionando o código necessário para imprimir a saída da função do professor, para que seja possível comparar com a saída esperada.
    def base_code_with_args_validate(self, baseCode: str, funcName: str, arg: str, expected_output: str, returnType):
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
    
    #Método específico de cada linguagem para formatar um valor que virá no formato JSON padrão para o formato correspondente ao seu tipo específico. Por exemplo, para booleanos, em Python o expected output deve ser "True" ou "False", enquanto em C deve ser 1 ou 0. Para None, em Python deve ser "None", em Julia deve ser "nothing" e em C deve ser "NULL". Para strings, é necessário garantir que estejam entre aspas duplas e que caracteres especiais sejam escapados corretamente. Para outros tipos de dados, como números, listas ou dicionários, é necessário convertê-los para uma representação string adequada para cada linguagem.
    def format_value(self, value: str, type: str, isReturn: bool = False):
        pass
