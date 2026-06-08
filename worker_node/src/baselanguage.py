class BaseLanguage():   #Aqui estarão métodos comuns para todas as linguagens suportadas
    def __init__(self, langExtension:str):
        self.langExtension = langExtension
    
    def base_code_with_args(self, baseCode: str, name_file_professor: str, funcName: str, funcNameProf: str, arg, returnType = ""):
        """
        Método para formatar o código base da solução, adicionando os argumentos dos casos de teste e o código necessário para comparar a saída da solução com a saída esperada, além de capturar erros e exceções que possam ocorrer durante a execução do código.
        Args:
            baseCode (str): O código base da solução, que é o código enviado pelo estudante na submissão.
            name_file_professor (str): O nome do arquivo que contém o código do professor (solução correta).
            funcName (str): O nome da função da solução.
            funcNameProf (str): O nome da função do professor.
            arg: Os argumentos para a função.
            returnType (str, optional): O tipo de retorno da função. Defaults to "".
        """
        pass
    
    def base_code_with_args_validate(self, baseCode: str, funcName: str, arg: str, expected_output: str, returnType: str):
        """
        Método para formatar o código enviado no momento da criação do problema, adicionando o código necessário para imprimir a saída da função do professor, para que seja possível comparar com a saída esperada.
        Args:
            baseCode (str): O código base da solução, que é o código enviado pelo professor durante a criação do problema.
            funcName (str): O nome da função da solução.
            arg: Os argumentos para a função.
            expected_output (str): A saída esperada para os argumentos fornecidos.
            returnType (str): O tipo de retorno da função.
        """
        pass
    
    def professor_code_with_args(self, professorCode: str, funcName: str, funcNameProf: str, arg, returnType = ""):
        """
        Método para formatar o código do professor durante a execução dos casos de teste na submissão de um estudante.
        Args:
            professorCode (str): O código do professor, que é o código correto da solução.
            funcName (str): O nome da função da solução.
            funcNameProf (str): O nome da função do professor.
            arg: Os argumentos para a função.
            returnType (str, optional): O tipo de retorno da função. Defaults to "".
        """
        pass
    
    def evaluate_file(self, absolute_path: str):
        """
        Método para avaliar um arquivo de código, utilizando uma ferramenta de análise estática de segurança (SAST) adequada para a linguagem em questão, e retornar os resultados da avaliação, como vulnerabilidades encontradas, riscos associados e recomendações de correção.
        Args:
            absolute_path (str): O caminho absoluto do arquivo de código a ser avaliado.
        """
        pass
    
    def run_code(self, file_path: str, isProfessorCode: bool):
        """
        Método para compilar e/ou executar um arquivo de código, dependendo da linguagem, e retornar a saída gerada pela execução do código, além de capturar erros e exceções que possam ocorrer durante a execução do código.
        Args:
            file_path (str): O caminho absoluto do arquivo de código a ser executado.
            isProfessorCode (bool): Indica se o código a ser executado é o código do professor (solução correta) ou o código do estudante (solução a ser avaliada). Isso pode ser útil para diferenciar a forma de execução ou tratamento de erros, caso seja necessário.
        """
        pass
    
    def run_pre_process_code(self, file_path: str):
        """
        Método para executar um código de pré-processamento, garantindo que o código enviado não tenha nenhum tipo de erro de sintaxe ou outro tipo de erro que possa impedir a execução do código principal com os casos de teste.
        Args:
            file_path (str): O caminho absoluto do arquivo de código a ser pré-processado.
        """
        pass
    
    def pre_process_code(self, code: str, code_path: str):
        """
        Método para pré-processar o código enviado, realizando tarefas como formatação, remoção de comentários, verificação de erros de sintaxe, entre outras tarefas que possam ser necessárias para garantir que o código esteja pronto para ser executado com os casos de teste.
        Args:
            code (str): O código a ser pré-processado.
            code_path (str): O caminho absoluto do arquivo de código a ser pré-processado.
        """
        pass
    
    def format_value(self, value: str, type: str, isReturn: bool = False):
        """
        Método para formatar um valor que virá no formato JSON padrão para o formato correspondente ao seu tipo específico. Por exemplo, para booleanos, em Python o expected output deve ser "True" ou "False", enquanto em C deve ser 1 ou 0. Para None, em Python deve ser "None", em Julia deve ser "nothing" e em C deve ser "NULL". Para strings, é necessário garantir que estejam entre aspas duplas e que caracteres especiais sejam escapados corretamente. Para outros tipos de dados, como números, listas ou dicionários, é necessário convertê-los para uma representação string adequada para cada linguagem
        Args:
            value (str): O valor a ser formatado, que é recebido no formato JSON padrão.
            type (str): O tipo do valor, como "int", "float", "string", "bool", "None", etc.
            isReturn (bool, optional): Indica se o valor a ser formatado é um valor de retorno de uma função. Isso pode ser útil para diferenciar a formatação de valores de entrada e valores de retorno, caso seja necessário. Defaults to False.
        """
        pass
