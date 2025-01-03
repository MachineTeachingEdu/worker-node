from pathlib import Path
from flask import Flask, request,  abort
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
import requests
from flask import jsonify
from dotenv import load_dotenv
import time

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
    


@app.route('/pre-process', methods=['POST'])    #Endpoint usado para o pré-processamento dos códigos submetidos
def pre_process():
    logging.info(request.files)
    if 'file' not in request.files:
        abort(400, 'Missing submission file')
        
    file = request.files['file']
    try:
        lang = request.form.get("prog_lang")
        if not lang:
            raise Exception()
        objLang = LanguageFactory.create_object_language(lang)
        langExtension = objLang.langExtension
    except Exception:
        return {'errorMsg': "Error: AJAX call with invalid arguments."}, 400
    if file and _valid_file(file.filename):
        try:
            TEMP_DIR = _create_temp_dir()
            compressed_file_name = secure_filename(file.filename)
            file.save(os.path.join(TEMP_DIR, compressed_file_name))
        except Exception:
            return {'errorMsg': "Error: Couldn't create temporary files."}, 500

        try:
            submitted_code_path = _unzip_file_codes(TEMP_DIR, compressed_file_name, langExtension, professor_code=False)
            objLang.evaluate_file(submitted_code_path)   #Checagem de vulnerabilidades
            code = open(submitted_code_path, "r").read()
            final_code = objLang.pre_process_code(code, submitted_code_path)   #Removendo comentários do código e checando funções inválidas
            result = {
                'code_status': 0,    #Código válido
                'message': '',
                'final_code': final_code,
            }
            _delete_temp_files(TEMP_DIR)
            return result
        except PrintException as e:
            result = {
                'code_status': 1,    #Código com comandos de print
                'message': e.message,
                'final_code': '',
            }
            _delete_temp_files(TEMP_DIR)
            return result
        except ImportException as e:
            result = {
                'code_status': 2,    #Importações inválidas
                'message': e.message,
                'final_code': '',
            }
            _delete_temp_files(TEMP_DIR)
            return result
        except DangerException as e:
            result = {
                'code_status': 3,    #Vulnerabilidades detectadas no código
                'message': e.message,
                'final_code': '',
            }
            _delete_temp_files(TEMP_DIR)
            return result
        except CodeException as e:
            result = {
                'code_status': 4,    #Erros de sintaxe ou de compilação
                'message': e.message,
                'final_code': '',
            }
            _delete_temp_files(TEMP_DIR)
            return result
        except subprocess.TimeoutExpired:
            result = {
                'code_status': 5,    #TLE
                'message': "Time limit exceeded: O código excedeu o tempo limite de execução.",
                'final_code': '',
            }
            _delete_temp_files(TEMP_DIR)
            return result
        except Exception as e:
            _delete_temp_files(TEMP_DIR)
            return {'errorMsg': "Error: Couldn't extract .zip file and read the code."}, 500
    else:
        abort(400, 'Invalid file')


@app.route('/', methods=['POST'])    #Endpoint usado para o processamento dos códigos submetidos
def upload_file():
    logging.info(request.files)
    if 'file' not in request.files:
        abort(400, 'Missing submission file')
        
    file = request.files['file']
    try:
        args = request.form.get("args")
        funcName = request.form.get("funcName")
        returnType = request.form.get("returnType")
        lang = request.form.get("prog_lang")
        if not args or not funcName or not lang:
            raise Exception()
        funcNameProf = funcName + "_prof"
        objLang = LanguageFactory.create_object_language(lang)
        langExtension = objLang.langExtension
        
        args = json.loads(args)
    except Exception:
        return {'errorMsg': "Error: AJAX call with invalid arguments."}, 400

    if file and _valid_file(file.filename):
        try:
            TEMP_DIR = _create_temp_dir()
            compressed_file_name = secure_filename(file.filename)
            file.save(os.path.join(TEMP_DIR, compressed_file_name))
        except Exception:
            return {'errorMsg': "Error: Couldn't create temporary files."}, 500
        
        try:
            submitted_code_path, professor_code_path = _unzip_file_codes(TEMP_DIR, compressed_file_name, langExtension, professor_code=True)
            baseCode = open(submitted_code_path, "r").read()
            professorCode = open(professor_code_path, "r").read()
        except Exception:
            _delete_temp_files(TEMP_DIR)
            return {'errorMsg': "Error: Couldn't extract .zip file and read the code."}, 500
        
        results = []
        for index, arg in enumerate(args):
            try:
                codeArgs = objLang.base_code_with_args(baseCode, name_file_professor, funcName, funcNameProf, arg, returnType)
                professorCodeArgs, outputProfessorCodeArgs = objLang.professor_code_with_args(professorCode, funcName, funcNameProf, arg, returnType)   # outputProfessorCodeArgs possui o código base do professor mais a parte do output da função
                
                with open(submitted_code_path, 'w') as file:
                    file.write(codeArgs)   #Escrevendo o código com os argumentos para ser testado
                with open(professor_code_path, 'w') as file:
                    file.write(professorCodeArgs)
                
                code_output = objLang.run_code(submitted_code_path, False)
                
                result = {
                    'isCorrect': code_output[0],
                    'code_output': code_output[1],
                    'prof_output': code_output[2],
                    'hostname': socket.gethostname(),
                }
                status_code = 200

            except CodeException as e:
                result = {
                    'isCorrect': False,
                    'code_output': e.message,
                    'prof_output': '',
                    'hostname': socket.gethostname(),
                }
                status_code = 400
            except subprocess.TimeoutExpired:
                result = {
                    'isCorrect': False,
                    'code_output': "Time limit exceeded: O código excedeu o tempo limite de execução.",
                    'prof_output': '',
                    'hostname': socket.gethostname(),
                }
                status_code = 400
            except Exception as e:
                _delete_temp_files(TEMP_DIR)
                return {'errorMsg': "Erro na execução dos códigos!"}, 500
            
            try:
                if status_code != 200:
                    with open(professor_code_path, 'w') as file:
                        file.write(outputProfessorCodeArgs)
                    professor_code_output = objLang.run_code(professor_code_path, True)
                    result['prof_output'] = professor_code_output
            except Exception as e:
                _delete_temp_files(TEMP_DIR)
                return {'errorMsg': "Solution code error!"}, 500
            
            resultItem = []
            resultItem.append(result)
            resultItem.append(status_code)
            results.append(resultItem)
                
        _delete_temp_files(TEMP_DIR)
        return results
    else:
        abort(400, 'Invalid files')





@app.route('/multi_process', methods=['POST'])    #Endpoint usado para o processamento dos códigos submetidos com multiprocessamento de todos os casos de teste
def multi_process():
    #logging.info(request.files)
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
    
    
    
    #Primeiramente, recuperando os dados com a API Django enviando o id do problema (usar try/except)
    try:
        problem_data, status_code = get_problem(problem_id)
        for solution in problem_data.json['solutions']:
            if solution['language'] == lang and solution['ignore'] == False:
                professorCode = solution['content']
                funcName = solution['header']
                returnType = solution['return_type']
                if not returnType:
                    returnType = ""
                break
        #Recuperando os casos de teste e formatando eles para o formato JSON esperado:
        testCasesRaw = []
        for test_case in problem_data.json['test_cases']:
            if lang in test_case['languages']:
                testCasesRaw.append(test_case['content'])
        formattedTestCases = [f'"{str(element)}"' for element in testCasesRaw]
        testCases = []
        for teste in formattedTestCases:
            testCases.append(json.loads(teste))
    except Exception as e:
        return {'errorMsg': "Error: Couldn't get problem data from Django API."}, 500
    
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
            results.append(resultItem)
        """
        if(lang == "Julia"):
            print("Encerrando o servidor DaemonMode...")
            daemon_process.terminate()
            daemon_process.wait()
        """

        _delete_temp_files(TEMP_DIR)
        return results
    else:
        abort(400, 'Invalid file')
    

#Teste de comunicação com a API Django:
def get_problem(problem_id):
    #django_api_url = f'{os.getenv("DJANGO_API_URL")}/{problem_id}/'  # URL da API Django    #Aparentemente, variáveis de ambiente não funcionam no modo debug
    django_api_url = f'http://localhost:8000/pt-br/problem_details/{problem_id}/'  # URL da API Django (modo debug)
    try:
        response = requests.get(django_api_url, timeout=5)  # Timeout para evitar travamento
        response.raise_for_status()  # Levanta exceções para erros HTTP
        data = response.json()
        return jsonify(data), response.status_code  #Retorna o mesmo código da API Django
    except requests.exceptions.Timeout:
        app.logger.error("Timeout ao tentar se conectar à API Django.")
        return jsonify({'error': 'Timeout while connecting to Django API'}), 504  #Gateway Timeout
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Erro ao se comunicar com a API Django: {e}")
        return jsonify({'error': 'Failed to fetch data from Django API'}), 500
    
    
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.getenv('PORT', 5000)))
