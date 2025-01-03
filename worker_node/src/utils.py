import os
import logging

logging.basicConfig(level=logging.INFO)

def is_running_in_container():
    if os.getenv("RUNNING_IN_DOCKER", "False") == "True":   #Verifica se a variável de ambiente RUNNING_IN_DOCKER é True. Se ela não existir, assume False
        logging.info("Estou no container!!")
        return True
    logging.info("Não estou no container!!")
    return False