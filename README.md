# Agentic Code Atlas

This project automates the process of generating comprehensive documentation and visual diagrams for your codebase. By analyzing metadata such as namespaces and code structures, the tool leverages an agent-based system to produce detailed insights, including system overviews, architecture diagrams, and component breakdowns. Integrated with PlantUML, it effortlessly creates C4 model diagrams, making it a powerful resource for developers looking to understand and document complex systems.

## Command‑Line Usage

```bash
python gen_doc.py \
  -l <language> \
  -f <folder-path> \
  -r <root-namespace> \
  -o <output-dir> \
  [-p <plantuml-server>] \
  [-m <max-rpm>] \
  [-v]
```

Options

- `-l, --language`  
  Programming language of the codebase.  
  (supported languages: `java`, `python`, `kotlin`, `php`)

- `-f, --folder-path`  
  Path to the root of the source code folder to analyze.  
  e.g. `./src`, `/home/me/project`

- `-r, --root-namespace`  
  Top‑level namespace or package that all references should be resolved against.  
  e.g. `com.mycompany.myapp`, `my_project`

- `-o, --output-dir`  
  Directory where the generated Markdown docs and diagrams will be written.  
  e.g. `./docs`

- `-p, --plantuml-server` _(optional)_  
  URL of a PlantUML server for generating diagrams.  
  e.g. `http://localhost:8000/plantuml/png/` 

- `-m --max-rpm` _(optional)_  
  Maximum requests per minute to LLM API.
  e.g. `60` (default is `30`)

- `-v, --verbose` _(optional)_
  Enable verbose output for debugging purposes.  

Example

```bash
python gen_doc.py \
  -l java \
  -f ./my_service/src \
  -r my_service \
  -o ./generated_docs \
  -p http://localhost:8000/plantuml/png/
```

## Question Answering Utility (`qa.py`)

The `qa.py` script extends this toolkit with an interactive question-answering feature. It analyzes your code metadata and provides answers (along with PlantUML diagrams) to natural-language queries about your codebase.

### Command‑Line Usage

```bash
python qa.py \
  -l <language> \
  -f <folder-path> \
  -r <root-namespace> \
  -o <output-file> \
  -q <question> \
  [-p <plantuml-server>] \
  [-m <max-rpm>] \
  [-v]
```

**Options**

- `-l, --language`  
  Programming language (e.g., `java`, `python`, `kotlin`, `php`).

- `-f, --folder-path`  
  Path to the source code folder to scan.  
  e.g. `./src`, `/home/me/project`

- `-r, --root-namespace`  
  Root namespace or package for resolving references.  
  e.g. `com.mycompany.myapp`, `my_project`

- `-o, --output-file`  
  Base name of the output file (Markdown). The script will produce `<output-file>.md` and an accompanying `<output-file>.png` diagram.  
  e.g. `./answers/architecture_overview`

- `-q, --question`  
  Natural-language question to ask the system.  
  e.g. `"What are the main modules and their dependencies?"`

- `-p, --plantuml-server` _(optional)_  
  URL of a PlantUML server for rendering diagrams.  
  e.g. `http://localhost:8000/plantuml/png/`

- `-m, --max-rpm` _(optional)_  
  Maximum requests per minute to the LLM API (default is `20`).  
  e.g. `50`

- `-v, --verbose` _(optional)_
  Enable verbose logging for debugging purposes.

**Example**

```bash
python qa.py \
  -l python \
  -f ./project/src \
  -r project \
  -o ./answers/code_questions \
  -q "List all classes handling HTTP requests" \
  -p http://localhost:8000/plantuml/png/ \
  -m 25 \
  -v
```