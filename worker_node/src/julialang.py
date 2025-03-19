from baselanguage import BaseLanguage
from exceptions import CodeException, PrintException, ImportException
import subprocess
import os
import re

class JuliaLanguage(BaseLanguage):
    def __init__(self, langExtension:str): 
        self.__offsetCodeLines = 1
        self.__baseCodeLines = -1
        super().__init__(langExtension)
    
    def base_code_with_args(self, baseCode: str, name_file_professor: str, funcName: str, funcNameProf: str, arg, returnType = ""):
        #print(f"baseCodeLines: {self.__baseCodeLines}")
        self.__baseCodeLines = len(baseCode.splitlines())
        importProfLine = f'include("{name_file_professor}.jl")\n'
        argFix = convert_single_to_double_quotes(arg)
        codesComparisonOutput = f"\n\nprintln({funcName}({argFix}...) == {funcNameProf}({argFix}...))\nprintln({funcName}({argFix}...))\nprintln({funcNameProf}({argFix}...))"
        resultArgs = importProfLine + baseCode + codesComparisonOutput
        return resultArgs
    
    def professor_code_with_args(self, professorCode: str, funcName: str, funcNameProf: str, arg, returnType = ""):
        baseProfCode = professorCode.replace(funcName, funcNameProf)  #Trocando o nome da função no arquivo do professor
        argFix = convert_single_to_double_quotes(arg)
        outputProf = f"\nprintln({funcNameProf}({argFix}...))"   #Servirá para printar o output da solução correta
        outputProfCode = baseProfCode + outputProf
        return baseProfCode, outputProfCode
    
    def evaluate_file(self, absolute_path: str):    #Por enquanto, não há verificações para Julia
        return
    

    def run_code(self, file_path: str, isProfessorCode: bool):
        result = subprocess.run(["julia", file_path], capture_output=True, text=True, timeout=20)
        #result = subprocess.run(["julia", "-e", "using DaemonMode; runargs()", os.path.abspath(file_path)], capture_output=True, text=True, check=True, cwd=os.path.dirname(file_path), timeout=20)
        if result.stderr != "":
            error_message = process_errors(result.stderr, self.__offsetCodeLines, self.__baseCodeLines, file_path)
            raise CodeException(error_message)
        outputs = result.stdout.split("\n")
        if isProfessorCode:
            return outputs[0]
        outputs[0] = True if outputs[0].upper() == "TRUE" else False
        return outputs

        
        #Usando o Daemon Mode:
        #result = subprocess.run(["julia", "-e", "using DaemonMode; runargs()", file_path], capture_output=True, text=True, cwd=os.path.dirname(file_path), timeout=20)
        #if "error" in result.stdout.lower():
        #    error_message = process_errors(result.stdout, self.__offsetCodeLines, self.__baseCodeLines, file_path)
        #    raise CodeException(error_message)
        #outputs = result.stdout.split("\n")
        #if isProfessorCode:
        #    return outputs[0]
        #outputs[0] = True if outputs[0].upper() == "TRUE" else False
        #return outputs

    """
    def run_code(self, file_path: str, isProfessorCode: bool, juliaREPLSession, isFirst: bool, isLast: bool):   #Testando o REPL   
        juliaREPLSession.stdin.write(f'include("{file_path}")' + "\n")  # Envia o comando
        juliaREPLSession.stdin.flush()
        
        # Captura a saída normal (stdout) e erros (stderr)
        output = ""
        errors = ""
        while True:
            # Leia stdout
            line = juliaREPLSession.stdout.readline()
            if line.strip() == "":  # Fim da saída padrão
                break
            output += line.strip()

        while True:
            # Leia stderr
            error_line = juliaREPLSession.stderr.readline()
            if error_line.strip() == "":  # Fim dos erros
                break
            errors += error_line.strip()
    
        if errors != "":
            error_message = process_errors(errors, self.__offsetCodeLines, self.__baseCodeLines, file_path)
            raise CodeException(error_message)
        outputs = output.split("\n")
        if isProfessorCode:
            return outputs[0]
        outputs[0] = True if outputs[0].upper() == "TRUE" else False
        return outputs
    """

    def run_pre_process_code(self, file_path: str):
        result = subprocess.run(["julia", file_path], capture_output=True, text=True, timeout=20)
        stderr = result.stderr
        if stderr != "":
            error_message = process_errors(stderr, 0, self.__baseCodeLines, file_path)
            raise CodeException(error_message)
    
    def pre_process_code(self, code: str, code_path: str):
        code_without_comments = re.sub(r'#=(.*?)=#', '', code, flags=re.DOTALL)
        code_without_comments = re.sub(r'(?<!["\'])#.*$', '', code_without_comments, flags=re.MULTILINE)
        code_without_comments = code_without_comments.strip()
        print_regex = re.compile(r'\b(print|println)\s*\(.*\)|@\b(printf|show)\b')
        has_print = bool(print_regex.search(code_without_comments))
        if has_print:
            raise PrintException("")
        verify_against_blacklist(code_without_comments)   #Verificando importações inválidas
        self.__baseCodeLines = len(code.splitlines())
        self.run_pre_process_code(code_path)
        return code
    
    
def process_errors(stderr: str, offSetLines: int, baseCodeLines: int, file_path: str):
    path = os.path.normpath(file_path)
    result_path = os.sep.join(path.split(os.sep)[-3:])  #Pegando os 3 últimos diretórios do caminho relativo do arquivo
    result_path_without_file_name = os.sep.join(path.split(os.sep)[-3:-1])
    
    match_undef_var = re.search(r"ERROR: LoadError: UndefVarError: `(.+?)` not defined.*?:(\d+)", stderr, re.DOTALL) #Regex para capturar erro de variável indefinida
    other_errors = re.compile(r'ERROR:\s+([\w]+):\s+([\w\s.-]+):\s+(.*)')
    other_errors_match = other_errors.search(stderr)
    
    error_type = ""
    error_message = ""
    line_number = -1
    
    if match_undef_var:
        var_name = match_undef_var.group(1)
        error_message = f"LoadError: UndefVarError: `{var_name}` not defined"
    elif other_errors_match:
        error_type1 = other_errors_match.group(1).strip()
        error_type2 = other_errors_match.group(2).strip()
        error_type = error_type1 + ": " + error_type2
        error_message = other_errors_match.group(3).strip()
        if result_path_without_file_name in error_message:
            error_parts = error_message.split('"')
            file_name = ""
            full_path = ""
            for error_part in error_parts:
                if result_path_without_file_name in error_part:
                    full_path = error_part
                    last_slash_index = max(error_part.rfind('/'), error_part.rfind('\\'))
                    file_name = error_part[last_slash_index + 1:]
                    file_name = file_name.split(":")[0]
                    break
            if file_name != "":
                error_message = error_message.replace(full_path, f" in {file_name}")
            else:
                error_message = ""
        error_message = f"{error_type}: {error_message}"
        
        if "└ ──" in stderr or "┘ ──" in stderr or "╙ ──" in stderr:  #Verifica se há uma seta no erro
            arrow_index = stderr.find("└ ──")
            if arrow_index == -1:
                arrow_index = stderr.find("┘ ──")
            if arrow_index == -1:
                arrow_index = stderr.find("╙ ──")
            start_index = arrow_index
            for i in range(arrow_index + 1, len(stderr)):
                if stderr[i].isalpha():
                    start_index = i
                    break
            end_index = stderr.find('\n', start_index)
            if end_index == -1:
                end_index = len(stderr)
            extracted = stderr[start_index:end_index].strip()
            error_message += f" - {extracted}"
    
    #Procurando a linha:
    stacktrace_pattern = re.compile(r'run_me.jl:(\d+)')
    stacktrace_matches = stacktrace_pattern.findall(stderr)
    if stacktrace_matches:
        for line in stacktrace_matches:
            #if result_path in file_name:
            line_number = int(line.strip()) - offSetLines
            break
    if baseCodeLines != -1 and line_number != -1:
        if int(line_number) <= baseCodeLines:
            error_message += f" on line {line_number}"
    return error_message

def convert_single_to_double_quotes(arg_string):
    arg_string = re.sub(r"''", r'""', arg_string)   #Substitui strings vazias '' por ""
    arg_string = re.sub(r"'([^']+)'", r'"\1"', arg_string)   #Substitui aspas simples internas por aspas duplas para palavras com mais de um caractere
    arg_string = re.sub(r'"(.)"', r"'\1'", arg_string)   #Mantém aspas simples para strings de 1 caractere
    arg_string = re.sub(r'^"|"$', "'", arg_string)    #Substitui as aspas duplas externas por aspas simples
    return arg_string

def verify_against_blacklist(code: str):
    blacklist = [
        r'\busing\s+FileIO\b',               # using FileIO
        r'\busing\s+Sockets\b',              # using Sockets
        r'\busing\s+Distributed\b',          # using Distributed
        r'\busing\s+Libc\b',                 # using Libc
        r'\busing\s+Libdl\b',                # using Libdl (usado para manipulação de bibliotecas externas)
        r'\busing\s+DelimitedFiles\b',       # using DelimitedFiles (permite leitura e escrita de arquivos)
        r'\busing\s+Base\b',                 # using Base (excesso de permissões)
        r'\bimport\s+FileIO\b',              # import FileIO
        r'\bimport\s+Sockets\b',             # import Sockets
        r'\bimport\s+Distributed\b',         # import Distributed
        r'\bimport\s+Libc\b',                # import Libc
        r'\bimport\s+Libdl\b',               # import Libdl
        r'\bimport\s+Base\b',                # import Base (excesso de permissões)
        r'\bopen\s*\(',                      # open(...)
        r'\brun\s*\(',                       # run(...)
        r'\beval\s*\(',                      # eval(...)
        r'\bsystem\s*\(',                    # system(...) - execução de comandos do sistema
        r'\bread\s*\(',                      # read(...) - leitura de arquivos
        r'\bwrite\s*\(',                     # write(...) - escrita de arquivos
    ]

    for pattern in blacklist:
        if re.search(pattern, code):
            raise ImportException("Not allowed import or method found.")