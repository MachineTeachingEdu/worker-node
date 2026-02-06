# Worker Node - Documentação

## Índice

1. [Visão Geral](#visão-geral)
2. [Arquitetura](#arquitetura)
3. [Fluxo de Processamento](#fluxo-de-processamento)
4. [Especificidades de cada linguagem](#especificidades-de-cada-linguagem)
5. [Estratégias de Design](#estratégias-de-design)
6. [Como Rodar Localmente](#como-rodar-localmente)
7. [Como Adicionar uma Nova Linguagem](#como-adicionar-uma-nova-linguagem)

---

## Visão Geral

O **Worker Node** é um servidor dedicado responsável pelo processamento dos códigos submetidos pelos estudantes que utilizam o sistema **Machine Teaching**. Trata-se de um microsserviço desenvolvido com o framework Flask que:

- Recebe códigos de usuários via HTTP
- Valida segurança e corretude
- Retorna os resultados ao sistema Web

Atualmente, o servidor processa códigos escritos em **Python**, **C** e **Julia**, utilizando o módulo **subprocess** do Python para executar os códigos.

### Tecnologias Utilizadas

- **Framework Web:** Flask
- **WSGI Server:** Gunicorn
- **Linguagens:** Python, C, Julia
- **Deployment:** Docker + GCR

### Endpoints

- `GET /` - Health check do servidor
- `GET /pre-process` - Health check de pré-processamento
- `POST /multi_process` - **Endpoint principal** para avaliação de código

Os endpoints podem ser vistos [aqui](./worker_node/src/server.py#L74).

---

## Arquitetura

O sistema é composto pelos seguintes arquivos em `worker_node/src/`:

- **server.py** - Orquestrador principal que recebe requisições HTTP, extrai arquivos, cria ambiente temporário e coordena a execução.
- **languagefactory.py** - Implementa o Factory Pattern para instanciar a classe correta de linguagem.
- **baselanguage.py** - Classe base abstrata que define a interface comum para todas as linguagens.
- **pythonlang.py** - Classe que contém os métodos específicos de processamento dos códigos em Python.
- **clang.py** - Classe que contém os métodos específicos de processamento dos códigos em C.
- **julialang.py** - Classe que contém os métodos específicos de processamento dos códigos em Julia.
- **exceptions.py** - Define as exceções customizadas do sistema.
- **utils.py** - Funções utilitárias.

---

## Fluxo de Processamento

### 1. Recepção (server.py)

O endpoint `POST /multi_process` recebe uma requisição `multipart/form-data` vinda do sistema Web do Machine Teaching com os seguintes parâmetros:

- **file** - ZIP contendo o código do aluno (arquivo chamado `run_me`)
- **prog_lang** - Linguagem: "Python", "C" ou "Julia"
- **problem_id** - Identificador do problema
- **professor_code** - Código da solução correta escrita pelo professor para este problema
- **func** - Nome da função a ser testada
- **return_type** - Tipo de retorno (obrigatório apenas para C). Identifica qual tipo primitivo a função do problema retorna. Isto é usado posteriormente nas execuções dos casos de teste
- **test_cases** - JSON array com os casos de teste que serão usados para testar a solução enviada. Os casos de teste são parâmetros que serão passados para a função do problema
- **custom_test_cases** - (opcional) Flag para casos de teste personalizados. Por padrão, o formato dos casos de teste que chegam ao Worker Node é uma lista Python. Esta flag é usada pois alguns problemas precisam de casos de testes em um formato não convencional. Por exemplo, para a linguagem C, problemas envolvendo a escrita de uma função que recebe um vetor terá casos de teste do tipo "(int[]){1, 2, 3}"

### 2. Setup do Ambiente

O servidor então cria um diretório temporário único usando UUID, extrai o ZIP do aluno para o arquivo `run_me.{extensão}` e salva o código do professor em `run_me_prof.{extensão}`. Para saber qual extensão usar, o campo da linguagem é usado para identificar em qual linguagem a solução foi escrita.

### 3. Pré-processamento

Antes de executar todos os casos de teste, o código enviado passa por um pré-processamento para identificar erros iniciais. Cada classe de linguagem possui suas próprias validações através dos métodos:

- `evaluate_file()` → Análise estática do código para identificar vulnerabilidades (Por enquanto, funciona apenas para Python utilizando a ferramenta **Bandit**). Pode gerar a exception `DangerException`
- `pre_process_code()` → Faz uso de expressões regulares para remover comentários do código, detectar prints (não é permitido o uso de nenhuma forma de print nos códigos enviados) e verificar o uso de métodos ou importações inválidas por meio de uma blacklist específica de cada linguagem ([este](./worker_node/src/clang.py#L222) é um exemplo para a classe da linguagem C). Pode gerar as exceptions `PrintException` ou `ImportException`
- `run_pre_process_code()` → Executa o código para identificar possíveis erros de sintaxe/compilação. Nesta etapa é utilizado o módulo `subprocess` do Python para simular um processo e executar um comando de compilação específico da linguagem. Pode gerar a exception `CodeException`

Todas estas exceptions personalizadas estão definidas em `exceptions.py`. Caso o código enviado gere alguma exception nesta etapa, o código é interrompido e a mensagem de erro, juntamente com um código identificando o tipo do erro são retornados para o sistema Web. Também pode acontecer uma exception relacionada ao estouro do limite de tempo para a compilação do código nesta etapa, que seria tratada da mesma forma. Se um código enviado não passa na etapa de pré-processamento, o sistema Web apenas exibe a mensagem de erro, poupando o tempo de execução dos casos de teste.

Esta é a lista de exceções personalizadas e seus respectivos códigos de identificação:

- **PrintException** (code_status: 1) - Print/printf/println detectado no código
- **ImportException** (code_status: 2) - Import de módulo proibido
- **DangerException** (code_status: 3) - Danger score alto detectado pelo Bandit
- **CodeException** (code_status: 4) - Erro de sintaxe, runtime ou compilação
- **TimeoutExpired** (code_status: 5) - Timeout excedido (TLE)

### 4. Execução dos Casos de Teste

Caso o código enviado passe no pré-processamento, inicia-se a execução dos casos de teste. Para cada caso de teste do problema, as seguintes tarefas são realizadas:

- **1. Preparação dos Códigos:**
    - A classe da linguagem específica gera código nos arquivos `run_me` e `run_me_prof` com argumentos por meio dos métodos `base_code_with_args()` e `professor_code_with_args()`.
    - Isto é feito de forma estratégica, gerando chamadas da função do problema passando como argumentos o caso de teste atual e comparando com o retorno da chamada da função do arquivo do professor.
    - Apenas a estrutura final do código é montada aqui, e a estratégia varia conforme a linguagem com a qual se está trabalhando.
    - No momento da execução, será possível tirar proveito desta estrutura ao verificar a saída gerada.
    - Depois de preparar os códigos, eles são escritos nos arquivos temporários `run_me` e `run_me_prof`.

- **2. Execução e Análise:**
    - O código que está no arquivo temporário `run_me` é executado por meio do método `run_code()` específico de cada classe de linguagem.
    - Nesta etapa é utilizado o módulo `subprocess` do Python para simular um processo e executar um comando de compilação específico da linguagem.
    - Caso algum erro aconteça, a mensagem de erro é extraída da saída gerada pelo `subprocess` para ser retornada. A extração de erros será explicada melhor mais a frente.
    - Caso não seja gerado nada na saída de erros do `subprocess`, a saída do código é analisada para conferir se o código está correto ou não.
    - Se o retorno da função do código do estudante for igual ao retorno da função do código do professor, aquele caso de teste é considerado bem sucedido.
    - Se houve algum erro ou os retornos não forem iguais, o caso de teste falha. Isto é definido pelo parâmetro `isCorrect` que também é retornado ao sistema Web para cada caso de teste.

- **3. Finalização:**
    - Depois que todos os casos de teste são processados, os resultados de todos são retornados ao sistema Web e o Worker Node faz a limpeza do diretório temporário criado para armazenar os arquivos processados.

### 5. Detecção e extração de mensagens de erro

Durante as etapas de pré-processamento e execução dos casos de teste, com os métodos `run_pre_process_code` e `run_code`, que utilizam o `subprocess`, erros podem ser capturados se acontecerem: um erro de sintaxe durante o pré-processamento ou um erro de tipagem durante a execução de um caso de teste, por exemplo. Quando algo desse tipo acontece, é necessário recuperar a mensagem principal do erro juntamente do local no código (linha) onde ele ocorreu, para que isso seja retornado ao sistema Web e exibido ao usuário. Esta tarefa será específica de cada linguagem já que cada uma delas exibe erros em um formato.

Para isso, o método `process_errors` (para Python e Julia) e os métodos `process_compile_errors` e `process_runtime_errors` (para C) são utilizados. Estes métodos utilizam expressões regulares para tratar a saída de erro e recuperar as informações importantes. As expressões regulares utilizadas foram baseadas em formatos mais comuns de erros para cada linguagem, mas esta estratégia está sujeita a falhas por não ser possível prever o tipo de erro exato que ocorrerá. Dessa forma, há uma atualização e adaptação constante nesta frente com o objetivo principal de aprimorar esta extração e gerar um feedback útil para o usuário.

### 6. Exemplos de Respostas

A seguir, um exemplo de resposta gerada para um problema com 2 casos de teste e solução enviada em Python, onde um dos casos de teste foi bem sucedido e o outro não:

```json
[
  {
    "result": {
      "isCorrect": true,
      "code_output": "30",
      "prof_output": "30",
      "test_case": "[10, 20]",
      "func_name": "soma",
      "hostname": "worker-abc123"
    },
    "status_code": 200,
    "num_test_cases": 2
  },
  {
    "result": {
      "isCorrect": false,
      "code_output": "20",
      "prof_output": "30",
      "test_case": "[15, 20]",
      "func_name": "soma",
      "hostname": "worker-abc123"
    },
    "status_code": 200,
    "num_test_cases": 2
  }
]
```

Um exemplo de resposta contendo um erro de pré-processamento de uma solução escrita em C pode ser vista a seguir:

Código submetido no sistema Web:
```
#include <sys/file.h>

int teste(int n){
	return 1;
}
```
Resposta gerada pelo Worker Node:
```json
{
  "pre_process_error": true,
  "code_status": 2,
  "message": "Potentially dangerous code found.",
  "final_code": ""
}
```

> **Nota:** O `code_status: 2` indica importações inválidas (ver tabela de exceções).

---

## Especificidades de cada linguagem

### Python (pythonlang.py)

Como dito anteriormente, para soluções enviadas em Python, é feita uma análise estática do código durante a etapa de pré-processamento para identificar possíveis vulnerabilidades. Isto é feito com o `Bandit`, que classifica as vulnerabilidades encontradas em scores:
- Danger Score: `(HIGH×3 + MEDIUM×2 + LOW×1) / total ≥ 1` → rejeita o código

---

### C (clang.py)

Para a linguagem C, além do método `run_code` presente em todas as classes de linguagens, foi necessário criar um método específico `compile_code` pela necessidade de compilação da linguagem C. A estratégia na compilação é utilizar flags estratégicas para identificar possíveis erros nos códigos e obter mais informações sobre eles, como a flag -Werror e -Wall. A seguir, o comando exato da compilação utilizando o `subprocess` pode ser visto:

```bash
list_compile = ['gcc', '-O1', '-Wuninitialized', '-Werror', '-Wall', '-g', '-fsanitize=address', '-o', exec_file_path, file_path, '-lm']
compile_result = subprocess.run(list_compile, capture_output=True, text=True, timeout=10)
```
Isto simulará o comando:
```bash
gcc -g -fsanitize=address -O1 -Wuninitialized -Werror -Wall -o run_me run_me.c -lm
```

A flag -fsanitize é utilizada para identificar possíveis erros de index inválido no acesso de vetores, por exemplo. Além disso, pode-se notar que o tempo limite configurado para a compilação é de 10 segundos.

Outra estratégia utilizada especificamente para a linguagem C ocorre no momento da escrita do código personalizado que será executado, mais especificamente na função `base_code_with_args`. Caso o problema tenha uma string como tipo de retorno, a comparação é feita utilizando o método strcmp. Caso seja um problema com retorno do tipo float, é utilizado o método fabs() para que uma margem de erro pequena seja aceita no momento da comparação entre os retornos.

**Comparação de floats:** `fabs(a - b) < 0.0001`  
**Comparação de strings:** `strcmp(a, b) == 0`

---

### Julia (julialang.py)

Atualmente, o processamento dos códigos em Julia não está bem otimizado, fazendo com que o tempo de feedback para um problema com muitos casos de teste seja muito alto. Isso ocorre pela forma atual de como o Worker Node processa os casos de teste. Como visto, a cada execução de caso de teste, é feita uma chamada ao método subprocess, que simula a criação de um novo processo. Este é um exemplo de chamada para um código em Julia:

```bash
result = subprocess.run(["julia", file_path], capture_output=True, text=True, timeout=20)
```

O problema aqui é que cada execução precisará enfrentar o tempo de inicialização do ambiente (Runtime) do Julia. Em um cenário normal, esse "Cold Start" ocorreria apenas na primeira execução, com as posteriores tirando vantagem dessa inicialização e sendo muito mais rápidas. Porém, aqui, essa inicialização não é aproveitada já que um novo subprocess é chamado para cada caso de teste, executando independentemente uns dos outros, e o Julia precisa fazer tudo do zero.

Uma possível estratégia é utilizar sempre a mesma sessão do Julia (com o REPL, por exemplo) para todos os casos de teste. Dessa forma, a primeira execução será lenta, mas a partir da segunda será quase instantânea. Atualmente, esse tipo de estratégia está sendo estudada, mas ainda não foi implementada. Dessa forma, enquanto a otimização para a linguagem Julia não ocorre, os problemas do Machine Teaching focam principalmente em Python e C.

---

## Estratégias de Design

### Factory Pattern (languagefactory.py)

O padrão Factory foi adotado aqui para gerar objetos específicos de cada classe de linguagem.

**Benefícios:**
- Desacopla `server.py` das implementações concretas
- Facilita adicionar o suporte a novas linguagens, com o trabalho maior sendo a escrita da classe específica da nova linguagem

### Template Method (baselanguage.py)

Métodos que cada linguagem deve implementar:
- `base_code_with_args()`: Monta o código que será executado com o caso de teste |
- `professor_code_with_args()`: Prepara o código do professor para comparação |
- `run_pre_process_code()`: Valida sintaxe/compilação antes dos testes |
- `run_code()`: Executa o código e retorna a saída |
- `pre_process_code()`: Aplica validações de segurança (blacklist, prints, imports) |


### Variáveis de Ambiente

- **PORT** - Porta do servidor (default: 5000)
- **RUNNING_IN_DOCKER** - Detecta ambiente container
- **GCR_INSTANCE** - Ativa autenticação OAuth2. Essa variável de ambiente só estará presente no ambiente de produção

### Camadas de Proteção

1. **Autenticação** - OAuth2 (apenas GCR)
2. **SAST (Static Application Security Testing)** - Bandit para Python
3. **Blacklists** - Imports/funções proibidas por linguagem
4. **Detecção de prints** - Evita contaminação do output
5. **Timeouts** - 10-20s por execução

### Isolamento

- Diretório temporário único criado por requisição (UUID)
- Cleanup automático após execução
- Processo filho com timeout via `subprocess.run()`

---

## Como Rodar Localmente

### Pré-requisitos

- Python 3.10+
- GCC (para processar códigos em C)
- Julia 1.9+ (para processar códigos em Julia)

### Opção 1: Executar diretamente com Python

```bash
# 1. Navegue até o diretório do worker_node
cd worker_node

# 2. Crie e ative um ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou: venv\Scripts\activate  # Windows

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Execute o servidor Flask
cd src
python3 server.py
```

### Opção 2: Executar com Docker

```bash
cd worker_node

# Construir e executar a imagem:
docker build -t worker-node .
docker run -it --env PORT=5000 -p 5000:5000 worker-node
```

### Verificando o funcionamento

Após iniciar o servidor, acesse `http://localhost:5000/` para verificar o health check.

---

## Como Adicionar uma Nova Linguagem

Para adicionar suporte a uma nova linguagem de programação, é possível seguir alguns passos:

### 1. Criar a classe da linguagem

Crie um novo arquivo em `worker_node/src/` (ex: `<linguagem>lang.py`) implementando a classe que herda de `BaseLanguage`:

```python
from baselanguage import BaseLanguage

class NovaLanguage(BaseLanguage):
    def __init__(self, langExtension: str):
        super().__init__(langExtension)
    
    def base_code_with_args(self, baseCode, name_file_professor, funcName, funcNameProf, arg, returnType=""):
        # Gera o código personalizado para execução do caso de teste
        pass
    
    def professor_code_with_args(self, professorCode, funcName, funcNameProf, arg, returnType=""):
        # Prepara o código do professor
        pass
    
    def evaluate_file(self, absolute_path: str):
        # Análise estática do código (opcional)
        pass
    
    def run_pre_process_code(self, file_path: str):
        # Executa o código para verificar erros de sintaxe/compilação
        pass
    
    def run_code(self, file_path: str, isProfessorCode: bool):
        # Executa o código para um caso de teste
        pass
    
    def pre_process_code(self, code: str, code_path: str):
        # Remove comentários, valida imports/prints, aplica blacklist
        pass
```

### 2. Registrar no LanguageFactory

Edite `worker_node/src/languagefactory.py` para incluir a nova linguagem:

```python
from novalang import NovaLanguage  # Adicione o import

class LanguageFactory():
    @staticmethod
    def create_object_language(language: str) -> BaseLanguage:
        if language == "Python":
            return PythonLanguage(".py")
        elif language == "Julia":
            return JuliaLanguage(".jl")
        elif language == "C":
            return CLanguage(".c")
        elif language == "NovaLinguagem": 
            return NovaLanguage(".ext")
        else:
            raise ValueError(f"Unknown language: {language}")
```

### 3. Considerações

- Defina uma **blacklist** de funções/imports perigosos para a linguagem
- Implemente a **extração de erros** com regex específico para o formato de erro da linguagem
- Se a linguagem necessitar de compilação, crie um método `compile_code()` separado (similar ao C)
- Atualize o Docker para incluir o runtime da nova linguagem, se necessário