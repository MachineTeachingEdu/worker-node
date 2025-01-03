"""
Module to evaluate the code submitted by the student looking for potential malicious code
"""
import os
from pathlib import Path
import json
from exceptions import DangerException


def verify_against_blacklist(code: str):

    if "import os" in code:
        raise DangerException("os não é úm módulo permitido")
    
    if "import subprocess" in code:
        raise DangerException("subprocess não é úm módulo permitido")
    
    if "import sys" in code:
        raise DangerException("sys não é úm módulo permitido")

    if "import socket" in code:
        raise DangerException("socket não é úm módulo permitido")
    
    if "import threading" in code:
        raise DangerException("threading não é úm módulo permitido")
    
    if "import multiprocessing" in code:
        raise DangerException("multiprocessing não é úm módulo permitido")
    
    if " open(" in code:
        raise DangerException("'open' não é um método permitido")
    

def evaluate_file(absolute_path: str):

    sast_result_file_path = absolute_path.replace(".py", "") + "_result.json"

    #os.system(f'bandit -c bandit_config.yml "{absolute_path}"  -f json -o "{sast_result_file_path}"')    #Esta linha é para o container
    os.system(f'bandit -c /home/nickashu/testeWorkerNode/remote-code-executor/worker_node/bandit_config.yml "{absolute_path}"  -f json -o "{sast_result_file_path}"')

    code = open(absolute_path, "r").read()

    verify_against_blacklist(code)

    test_output = json.load(Path(sast_result_file_path).open())

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
        #raise DangerException("Danger score is too high")
        raise DangerException("Este código pode apresentar vulnerabilidades")

    return