from baselanguage import BaseLanguage
from exceptions import DangerException, CodeException, ImportException, PrintException
from pathlib import Path
from utils import is_running_in_container
import os
import json
import subprocess
import re
#import sys

class PythonLanguage(BaseLanguage):
    def __init__(self, langExtension:str):   
        self.__offsetCodeLines = 4
        self.__baseCodeLines = -1
        super().__init__(langExtension)
    
    def base_code_with_args(self, baseCode: str, name_file_professor: str, funcName: str, funcNameProf: str, arg, returnType = ""):
        #print(f"baseCodeLines: {self.__baseCodeLines}")
        self.__baseCodeLines = len(baseCode.splitlines())
        baseCode = '\n'.join('        ' + linha for linha in baseCode.splitlines())     #Adicionando identação
        resultArgs = f"""import traceback
def execute_code():
    try:
        from {name_file_professor} import {funcName} as {funcNameProf}
{baseCode}
        print({funcName}(*{arg}) == {funcNameProf}(*{arg}), flush=True)
        print({funcName}(*{arg}), flush=True)
        print({funcNameProf}(*{arg}), flush=True)
        print("NoErrors", flush=True)
    except Exception as e:
        return e, traceback.extract_tb(e.__traceback__)
    return None, None

error, tb_list = execute_code()
if error:
    tb_last = tb_list[-1]
    line_number = tb_last.lineno - {self.__offsetCodeLines}    #Aqui é necessário diminuir por um offset
    error_type = type(error).__name__
    error_message = str(error)
    print(f"{{line_number}}\\n{{error_type}}\\n{{error_message}}", flush=True)"""
        return resultArgs
    
    def professor_code_with_args(self, professorCode: str, funcName: str, funcNameProf: str, arg, returnType = ""):
        outputProf = f"\nprint({funcName}(*{arg}))"
        outputProfCode = professorCode + outputProf
        return professorCode, outputProfCode
    
    def evaluate_file(self, absolute_path: str):
        sast_result_file_path = absolute_path.replace(".py", "") + "_result.json"
        if is_running_in_container():
            os.system(f'bandit -c bandit_config.yml "{absolute_path}"  -f json -o "{sast_result_file_path}"')    #Esta linha é para o container
            test_output = json.load(Path(sast_result_file_path).open())
        else:
            try:
                base_dir = Path(__file__).resolve().parent.parent
                config_path = base_dir / "bandit_config.yml"

                command = [
                    "bandit",
                    "-c", str(config_path),
                    "-f", "json",
                    "-o", sast_result_file_path,
                    "-r", absolute_path
                ]
                
                subprocess.run(command, check=True, capture_output=True, text=True)

            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                raise CodeException(f"Bandit security scan failed: {e}")

            try:
                sast_result_path = Path(sast_result_file_path)
                if not sast_result_path.exists() or sast_result_path.stat().st_size == 0:
                    return

                with sast_result_path.open(encoding='utf-8') as f:
                    test_output = json.load(f)

            except json.JSONDecodeError:
                raise CodeException(f"Error decoding JSON from bandit output file.")
            #os.system(f'bandit -c /home/nickashu/testeWorkerNode/remote-code-executor/worker_node/bandit_config.yml "{absolute_path}"  -f json -o "{sast_result_file_path}"')

        #test_output = json.load(Path(sast_result_file_path).open())
        metrics = test_output["metrics"]
        HIGH_SEVERITY = metrics["_totals"]["SEVERITY.HIGH"]
        MEDIUM_SEVERITY = metrics["_totals"]["SEVERITY.MEDIUM"]
        LOW_SEVERITY = metrics["_totals"]["SEVERITY.LOW"]
        UNDEFINED_SEVERITY = metrics["_totals"]["SEVERITY.UNDEFINED"]
        DANGER_SCORE = HIGH_SEVERITY * 3 + MEDIUM_SEVERITY * 2 + LOW_SEVERITY * 1 + UNDEFINED_SEVERITY * 0
        TOTAL_WARNINGS = HIGH_SEVERITY + MEDIUM_SEVERITY + LOW_SEVERITY + UNDEFINED_SEVERITY
        if TOTAL_WARNINGS == 0:
            return

        AVG_DANGER_SCORE = DANGER_SCORE / TOTAL_WARNINGS
        if AVG_DANGER_SCORE >= 1:
            raise DangerException("Danger score is too high")
        return
    
    def run_code(self, file_path: str, isProfessorCode: bool):
        result = subprocess.run(["python3", f"{file_path}"], capture_output=True, text=True, timeout=10)
        if result.stderr != "":
            error_message = process_errors(result.stderr, self.__offsetCodeLines)
            raise CodeException(error_message)
        
        outputs = result.stdout.split("\n")    #outputs terá o booleano informando se os outputs foram iguais, o output do estudante e o output do professor
        if isProfessorCode:
            return outputs[0]    #No caso de ter rodado apenas o código do professor
        
        if "NoErrors" in result.stdout:
            outputs[0] = True if outputs[0].upper() == "TRUE" else False
            return outputs
        line_number = outputs[0]
        error_type = outputs[1]
        error_message = outputs[2]
        error_message = error_message.replace("execute_code.<locals>.", "")
        error = f"{error_type}: {error_message}"
        if self.__baseCodeLines != -1 and int(line_number) <= self.__baseCodeLines:
            error += f" on line {line_number}"
            
        raise CodeException(error)
    
    
    def run_pre_process_code(self, file_path: str):   #Verificando erros de sintaxe
        result = subprocess.run(["python3", f"{file_path}"], capture_output=True, text=True, timeout=10)
        stderr = result.stderr
        if "SyntaxError" in stderr:
            error_message = "SyntaxError:"
            matches = list(re.finditer(r'line (\d+)', stderr))
            if matches:
                last_match = matches[-1]
                line_number = int(last_match.group(1))
                error_message += f"  on line {line_number}"
            raise CodeException(error_message)
    
    
    def pre_process_code(self, code: str, code_path: str):
        code_without_comments = re.sub(r'(?<!["\'])#.*$', '', code, flags=re.MULTILINE)
        code_without_comments = re.sub(r"'''[\s\S]*?'''|\"\"\"[\s\S]*?\"\"\"", '', code_without_comments, flags=re.MULTILINE)
        code_without_comments = code_without_comments.strip()
        print_regex = re.compile(r'\bprint\s*\(.*\)')
        has_print = bool(print_regex.search(code_without_comments))
        if has_print:
            raise PrintException("")
        verify_against_blacklist(code_without_comments)   #Verificando importações inválidas
        self.run_pre_process_code(code_path)   #Verificando erros de sintaxe
        return code
    

def process_errors(stderr: str, offSetLines: int):
    error_message = stderr.splitlines()[-1]
    return_message = error_message
    matches = list(re.finditer(r'line (\d+)', stderr))
    if matches:
        last_match = matches[-1]
        line_number = int(last_match.group(1)) - offSetLines
        return_message = return_message.split(" on line")[0]
        return_message += f" on line {line_number}"
    return return_message

def verify_against_blacklist(code: str):
    blacklist = [
        r'\bimport\s*\bos\b',                   # import os
        r'\bimport\s*\bsubprocess\b',            # import subprocess
        r'\bimport\s*\bsys\b',                   # import sys
        r'\bimport\s*\bsocket\b',                # import socket
        r'\bimport\s*\bthreading\b',             # import threading
        r'\bimport\s*\bmultiprocessing\b',       # import multiprocessing
        r'\bfrom\s+os\s+import\b',               # from os import ...
        r'\bfrom\s+subprocess\s+import\b',       # from subprocess import ...
        r'\bfrom\s+sys\s+import\b',              # from sys import ...
        r'\bfrom\s+socket\s+import\b',           # from socket import ...
        r'\bfrom\s+threading\s+import\b',        # from threading import ...
        r'\bfrom\s+multiprocessing\s+import\b',  # from multiprocessing import ...
        r'\bopen\s*\(',                          # open(...)
    ]

    for pattern in blacklist:
        if re.search(pattern, code):
            raise ImportException("Not allowed import or method found.")