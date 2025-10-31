from pathlib import Path
from flask import Flask, request, abort, jsonify
from werkzeug.utils import secure_filename
import os
import zipfile
import socket
import subprocess
from exceptions import DangerException, CodeException, PrintException, ImportException
from flask_cors import CORS
import uuid
import logging
import json
from languagefactory import LanguageFactory
from utils import is_running_in_container
import google.auth.transport.requests
import google.oauth2.id_token
import re

logging.basicConfig(level=logging.INFO)
BASE_DIR = (Path(__file__).parent / "code").absolute()

app = Flask(__name__)
CORS(app)

def _valid_file(filename):
    logging.info(filename)
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'zip'}

name_file_student = "run_me"
name_file_professor = "run_me_prof"

def _unzip_file_codes(folder: Path, file_name: str, language_extension: str, professor_code: bool):
    with zipfile.ZipFile(f"{folder}/{file_name}", mode="r") as archive:
        archive.extractall(path=folder.as_posix())

    pathBaseCode = (folder / name_file_student).as_posix()
    newPathBaseCode = pathBaseCode + language_extension
    if professor_code:
        pathProfessorCode = (folder / name_file_professor).as_posix()
        newPathProfessorCode = pathProfessorCode + language_extension
        os.rename(pathBaseCode, newPathBaseCode)
        os.rename(pathProfessorCode, newPathProfessorCode)
        return newPathBaseCode, newPathProfessorCode
    os.rename(pathBaseCode, newPathBaseCode)
    return newPathBaseCode

def delete_files_from_directory(folder: Path):
    for item in os.listdir(folder):
        item_path = os.path.join(folder, item)
        if os.path.isfile(item_path):
            os.remove(item_path)
        elif os.path.isdir(item_path):
            delete_files_from_directory(item_path)
            os.rmdir(item_path)

def _delete_temp_files(folder: Path):   #Deletando as pastas temporárias criadas
    delete_files_from_directory(folder)
    os.rmdir(folder.as_posix())
    os.rmdir(folder.parent.as_posix())

def _create_temp_dir():
    unique_id = uuid.uuid4().hex
    if is_running_in_container():
        os.makedirs(unique_id + "/code")     #Esta linha é para o container
    else:
        current_directory = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(current_directory, unique_id + "/code")
        os.makedirs(path)
    
    TEMP_DIR = (Path(__file__).parent / unique_id / "code").absolute()
    return TEMP_DIR


@app.route('/', methods=['GET'])
def health_check():
    return {'message': f'Hello World from {socket.gethostname()}!'}, 200

@app.route('/pre-process', methods=['GET'])
def health_check_pre_process():
    return {'message': f'Endpoint para pré-processamento do código. From {socket.gethostname()}!'}, 200
    

@app.route('/multi_process', methods=['POST'])    #Endpoint usado para o processamento dos códigos submetidos com multiprocessamento de todos os casos de teste
def multi_process():
    #logging.info("Iniciando processamento...")
    if os.getenv('GCR_INSTANCE'):
        #logging.info("Running on GCR. Checking authorization.")
        #Verificação do GCR:
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            abort(400, 'Missing authorization header')
        else:
            auth_type, creds = auth_header.split(" ", 1)
            if auth_type.lower() == "bearer":
                google.oauth2.id_token.verify_token(creds, google.auth.transport.requests.Request())
                #logging.info("Authorization check passed.")
    #else:
        #logging.info("Not running on GCR. No authorization check needed.")


    if 'file' not in request.files:
        abort(400, 'Missing submission file')
        
    file = request.files['file']
    try:
        lang = request.form.get("prog_lang")
        problem_id = request.form.get("problem_id")
        if not lang or not problem_id:
            raise Exception()
        objLang = LanguageFactory.create_object_language(lang)
        langExtension = objLang.langExtension
    except Exception:
        return {'errorMsg': "Error: AJAX call with invalid arguments."}, 400
    
    try:
        professorCode = request.form.get("professor_code")
        funcName = request.form.get("func")
        returnType = request.form.get("return_type")
        if not returnType:
            returnType = ""
            
            
        testCases = []
        if request.form.get("custom_test_cases"):   #No caso de haver casos de teste personalizados
            formattedTestCases = request.form.getlist('test_cases')
            for testCase in formattedTestCases:
                #Converte unicode \uXXXX para caractere real
                testCase = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), testCase)
                #Troca aspas duplas por simples
                testCase = re.sub(r'"([^"]*?)"', r"'\1'", testCase)
                testCases.append(testCase)
        else:
            testCasesRaw = json.loads(request.form['test_cases'])  #Desserializa a string JSON
            formattedTestCases = [f'"{str(element)}"' for element in testCasesRaw]
            for teste in formattedTestCases:
                testCases.append(json.loads(teste))
                
        
    except Exception as e:
        return {'errorMsg': "Invalid data."}, 500
    
    #Pré-processamento
    if file and _valid_file(file.filename):
        try:
            TEMP_DIR = _create_temp_dir()
            compressed_file_name = secure_filename(file.filename)
            file.save(os.path.join(TEMP_DIR, compressed_file_name))
        except Exception:
            return {'errorMsg': "Error: Couldn't create temporary files."}, 500

        try:
            submitted_code_path = _unzip_file_codes(TEMP_DIR, compressed_file_name, langExtension, professor_code=False)
            professor_code_path = os.path.join(os.path.dirname(submitted_code_path), name_file_professor) + langExtension
            with open(professor_code_path, 'w') as new_file:
                new_file.write(professorCode)
            
            objLang.evaluate_file(submitted_code_path)   #Checagem de vulnerabilidades
            baseCode = open(submitted_code_path, "r").read()
            
            finalCode = objLang.pre_process_code(baseCode, submitted_code_path)   #Removendo comentários do código e checando funções inválidas
        except PrintException as e:
            result = {
                'pre_process_error': True,
                'code_status': 1,    #Código com comandos de print
                'message': e.message,
                'final_code': '',
            }
            _delete_temp_files(TEMP_DIR)
            return result
        except ImportException as e:
            result = {
                'pre_process_error': True,
                'code_status': 2,    #Importações inválidas
                'message': e.message,
                'final_code': '',
            }
            _delete_temp_files(TEMP_DIR)
            return result
        except DangerException as e:
            result = {
                'pre_process_error': True,
                'code_status': 3,    #Vulnerabilidades detectadas no código
                'message': e.message,
                'final_code': '',
            }
            _delete_temp_files(TEMP_DIR)
            return result
        except CodeException as e:
            result = {
                'pre_process_error': True,
                'code_status': 4,    #Erros no código
                'message': e.message,
                'final_code': '',
            }
            _delete_temp_files(TEMP_DIR)
            return result
        except subprocess.TimeoutExpired:
            result = {
                'pre_process_error': True,
                'code_status': 5,    #TLE
                'message': "Time limit exceeded: O código excedeu o tempo limite de execução.",
                'final_code': '',
            }
            _delete_temp_files(TEMP_DIR)
            return result
        except Exception as e:
            _delete_temp_files(TEMP_DIR)
            return {'errorMsg': "Error: Couldn't extract .zip file and read the code."}, 500
        
        #Processamento (se o pré-processamento foi bem-sucedido)
        funcNameProf = funcName + "_prof"
        results = []

        """
        if(lang == "Julia"):
            print("Iniciando o servidor DaemonMode...")
            daemon_process = subprocess.Popen(
                ["julia", "-e", "using DaemonMode; serve(print_stack=true)"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            time.sleep(2)
        """

        tle = False
        for index, testCase in enumerate(testCases):
            #print(testCase)
            try:
                codeArgs = objLang.base_code_with_args(finalCode, name_file_professor, funcName, funcNameProf, testCase, returnType)
                professorCodeArgs, outputProfessorCodeArgs = objLang.professor_code_with_args(professorCode, funcName, funcNameProf, testCase, returnType)   # outputProfessorCodeArgs possui o código base do professor mais a parte do output da função
                
                with open(submitted_code_path, 'w') as file:
                    file.write(codeArgs)   #Escrevendo o código com os argumentos para ser testado
                with open(professor_code_path, 'w') as file:
                    file.write(professorCodeArgs)
                code_output = objLang.run_code(submitted_code_path, isProfessorCode=False)
                
                result = {
                    'isCorrect': code_output[0],
                    'code_output': code_output[1],
                    'prof_output': code_output[2],
                    'test_case': testCase,
                    'func_name': funcName,
                    'hostname': socket.gethostname(),
                }
                status_code = 200

            except CodeException as e:
                result = {
                    'isCorrect': False,
                    'code_output': e.message,
                    'prof_output': '',
                    'test_case': testCase,
                    'func_name': funcName,
                    'hostname': socket.gethostname(),
                }
                status_code = 400
            except subprocess.TimeoutExpired:
                tle = True
                result = {
                    'isCorrect': False,
                    'code_output': "Time limit exceeded: O código excedeu o tempo limite de execução.",
                    'prof_output': '',
                    'test_case': testCase,
                    'func_name': funcName,
                    'hostname': socket.gethostname(),
                }
                status_code = 400
            except Exception as e:
                result = {
                    'isCorrect': False,
                    f'code_output': "Exception error: {e}",
                    'prof_output': '',
                    'test_case': testCase,
                    'func_name': funcName,
                    'hostname': socket.gethostname(),
                }
                status_code = 500
            
            try:
                if status_code != 200:
                    with open(professor_code_path, 'w') as file:
                        file.write(outputProfessorCodeArgs)
                    professor_code_output = objLang.run_code(professor_code_path, True)
                    result['prof_output'] = professor_code_output
            except Exception as e:
                result['prof_output'] = 'Solution code error! (durante caso de teste)'
            
            #print(result['prof_output'])
            resultItem = {}
            resultItem['result'] = result
            resultItem['status_code'] = status_code
            resultItem['num_test_cases'] = len(testCases)   #Adicionado para fazer os testes automatizados
            if tle:
                results.clear()
                results.append(resultItem)
                break
            results.append(resultItem)
        """
        if(lang == "Julia"):
            print("Encerrando o servidor DaemonMode...")
            daemon_process.terminate()
            daemon_process.wait()
        """

        _delete_temp_files(TEMP_DIR)
        return jsonify(results)
    else:
        abort(400, 'Invalid file')
    
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.getenv('PORT', 5000)))
