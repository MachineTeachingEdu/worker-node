from baselanguage import BaseLanguage
from exceptions import CodeException, PrintException, DangerException
import os
import subprocess
import json
import re
import signal

class CLanguage(BaseLanguage):
    def __init__(self, langExtension:str):
        self.__offsetCodeLines = 4  #Offset de linhas que vêm antes do código do usuário
        self.__baseCodeLines = -1
        super().__init__(langExtension)
    
    def base_code_with_args(self, baseCode: str, name_file_professor: str, funcName: str, funcNameProf: str, arg, returnType = ""):
        if returnType == "":
            raise Exception
        argsTxt = extract_args(arg)
        self.__baseCodeLines = len(baseCode.splitlines())
        printf_returnType = formats_printf[returnType]
        line_comparison = f'printf("%d\\n", {funcName}({argsTxt}) == {funcNameProf}({argsTxt}));'
        if printf_returnType == "%s":  #Se o retorno for uma string, a comparação será feita com a função strcmp
            line_comparison = f'printf("%d\\n", strcmp({funcName}({argsTxt}), {funcNameProf}({argsTxt})) == 0);'
        
        resultArgs = f"""#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "{name_file_professor}{self.langExtension}"
{baseCode}
int main() {{
    {line_comparison}
    printf("{printf_returnType}\\n", {funcName}({argsTxt}));
    printf("{printf_returnType}", {funcNameProf}({argsTxt}));
    return 0;
}}
"""
        return resultArgs
    
    def professor_code_with_args(self, professorCode: str, funcName: str, funcNameProf: str, arg, returnType = ""):
        printf_returnType = formats_printf[returnType]
        argsTxt = extract_args(arg)
        
        baseProfCode = professorCode.replace(funcName, funcNameProf)   #Trocando o nome da função no arquivo do professor
        outputProfCode = f"""#include <stdio.h>
{baseProfCode}
int main(){{
    printf("{printf_returnType}", {funcNameProf}({argsTxt}));
    return 0;
}}"""
        return baseProfCode, outputProfCode
    
    def evaluate_file(self, absolute_path: str):        #Sem verificações para C
        return
    
    def run_code(self, file_path: str, isProfessorCode: bool):
        exec_file_path = compile_code(file_path, self.__offsetCodeLines, self.__baseCodeLines)
        run_result = subprocess.run([exec_file_path], capture_output=True, text=True, timeout=10)
        if run_result.stderr != "":
            raise CodeException(run_result.stderr)
        if run_result.returncode != 0:
            signal_number = -run_result.returncode
            signal_name = signal.Signals(signal_number).name
            msg_error = ""
            msg_error += f"RUNTIME ERROR\nSignal: {signal_name} (return code: {run_result.returncode})"
            if signal_name == "SIGFPE":
                msg_error += "\nDivision by zero or floating point error."
            elif signal_name == "SIGSEGV":
                msg_error += "\nSegmentation fault."
            elif signal_name == "SIGABRT":
                msg_error += "\nProgram aborted."
            elif signal_name == "SIGILL":
                msg_error += "\nIllegal instruction (SIGILL)."
            elif signal_name == "SIGBUS":
                msg_error += "\nBus error."
            raise CodeException(msg_error)
        outputs = run_result.stdout.split("\n")
        if isProfessorCode:
            return outputs[0]
        outputs[0] = False if outputs[0].upper() == "0" else True
        return outputs
    
    def run_pre_process_code(self, file_path: str):   #Verificando erros de sintaxe
        compile_code(file_path, 3, self.__baseCodeLines)
    
    def pre_process_code(self, code: str, code_path: str):
        code_without_comments = re.sub(r'\/\/.*$', '', code, flags=re.MULTILINE)
        code_without_comments = re.sub(r'\/\*[\s\S]*?\*\/', '', code_without_comments, flags=re.MULTILINE)
        code_without_comments = code_without_comments.strip()
        print_regex = re.compile(r'\b(printf|puts)\s*\(.*\)')
        has_print = bool(print_regex.search(code_without_comments))
        if has_print:
            raise PrintException("")
        verify_against_blacklist(code_without_comments)
        self.__baseCodeLines = len(code.splitlines())
        
        importPart = "#include <stdio.h>\n#include <string.h>\n#include <stdlib.h>\n"
        mainPart = "\nint main() {return 0;}"
        codeWithMain = importPart + code + mainPart
        with open(code_path, 'w') as file:
            file.write(codeWithMain)
        self.run_pre_process_code(code_path)   #Checando por erros na compilação do código
        return code_without_comments

formats_printf = {
    "int": "%d",
    "char": "%c",
    "float": "%f",
    "double": "%lf",
    "long": "%ld",
    "long long": "%lld",
    "short": "%hd",
    "unsigned int": "%u",
    "unsigned long": "%lu",
    "const char*": "%s",
}

def extract_args(args):
    list_args = json.loads(args)
    argsTxt = ""
    for i, arg in enumerate(list_args):
        if i == len(list_args) - 1:
            argsTxt += f"{arg}"
        else:
            argsTxt += f"{arg}, "
    return argsTxt

def compile_code(file_path: str, offSetLines: int, baseCodeLines: int):
    file_name_with_extension = os.path.basename(file_path)  #Nome do arquivo (com extensão)
    file_name = os.path.splitext(file_name_with_extension)[0]
    exec_file_path = file_path.replace(file_name_with_extension, file_name)
    compile_result = subprocess.run(['gcc', '-o', exec_file_path, file_path, '-lm'], capture_output=True, text=True, timeout=10)  #Importando a biblioteca math.h
    if compile_result.stderr != "":
        error_message = process_compile_errors(compile_result.stderr, offSetLines, baseCodeLines)
        raise CodeException(error_message)
    
    return exec_file_path

def process_compile_errors(compile_error: str, offSetLines: int, baseCodeLines: int):
    compile_error_pattern = re.compile(r'([^:]+):(\d+):(\d+): (\w+): (.+)')   #Uso de expressões regulares
    function_error = ""
    error_message = ""

    for line in compile_error.splitlines():  #Percorrendo cada linha das mensagens de erro
        if " in function " in line.lower():
            if " in function " in line:
                function_error = line.split("in function")[1]
            elif " In function " in line:
                function_error = line.split("In function")[1]
            function_error = "In function" + function_error + "\n"

        match1 = compile_error_pattern.match(line)
        if match1:
            filename, line, column, message_type, message = match1.groups()
            lineNumber = int(line) - offSetLines
            if baseCodeLines != -1 and lineNumber <= baseCodeLines:
                error_message += f"COMPILE ERROR\n{function_error}Line {lineNumber}: Char {column}: {message_type}: {message}"
            else:
                error_message += f"COMPILE ERROR\n{function_error}{message_type}: {message}"
            if "redefinition of ‘main’" in error_message:
                error_message += ". You don't need to define the main function in your code."
            return error_message
        
        if "undefined reference to" in line.lower():
            function_name = line.split("undefined reference to")[1]
            error_message += f"{function_error}\nUndefined reference to `{function_name}`"
            return error_message
    
    error_message = f"{function_error[:-1]}"
    return error_message

def verify_against_blacklist(code):
    memory_leak_patterns = [  #Verificando uso de funções de alocação de memória
        r'\bmalloc\b', r'\bcalloc\b', r'\brealloc\b', r'\bfree\b'
    ]
    file_operations_patterns = [  #Verificando uso de funções de manipulação de arquivos
        r'\bfopen\b', r'\bfclose\b', r'\bfread\b', r'\bfwrite\b',
        r'\bfprintf\b', r'\bfscanf\b', r'\bfgets\b', r'\bfputs\b'
    ]
    
    memory_leak_found = any(re.search(pattern, code) for pattern in memory_leak_patterns)
    if memory_leak_found:
        raise DangerException("Dynamic memory allocation functions are not allowed.")
    file_operations_found = any(re.search(pattern, code) for pattern in file_operations_patterns)
    if file_operations_found:
        raise DangerException("File operations functions are not allowed.")
    
    return