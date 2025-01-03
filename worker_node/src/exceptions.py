class DangerException(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message

class ImportException(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message

class PrintException(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message

class CodeException(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message