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
  [-v]
```

Options

- `-l, --language`  
  Programming language of the codebase.  
  e.g. `python`, `java`, `csharp`

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