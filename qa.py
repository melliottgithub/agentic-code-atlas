import json
import os
import sys
import traceback
import argparse
import logging
from typing import Dict, Optional
from dataclasses import dataclass

from code_analyzer import generate_metadata, resolve_references
from metadata import Namespace
from code_meta_tool import CodeMeta, DetectModulesTool, GetClassesMetaTool, GetNamespacesMetaTool, GetFileSourcesTool
from agents import AgentSystem
from plantuml_tool import PlantUMLExportTool, createPlantUMLProcessor
from utils import read_yaml_file, write_file

logger = logging.getLogger(__name__)

@dataclass
class GenerationOptions:
    language: str
    root_namespace: str
    output_file: str
    folder_path: str
    plantuml_server: Optional[str] = None,
    question: Optional[str] = None,
    verbose: Optional[bool] = False

def question_answering(metadata: Dict[str, Namespace], options: GenerationOptions):
    llms_data = read_yaml_file('conf/llms.yaml')
    agents_data = read_yaml_file('conf/agents.yaml')
    tasks_data = read_yaml_file('conf/task_question_answering.yaml')

    code_meta = CodeMeta(metadata)
    
    plantuml_processor = createPlantUMLProcessor(options.plantuml_server)
    logger.info(f"PlantUML server: {plantuml_processor.url}")

    tools = {
        "get_namespaces": GetNamespacesMetaTool(code_meta),
        "get_classes": GetClassesMetaTool(code_meta),
        "get_file_sources": GetFileSourcesTool(code_meta, options.folder_path),
        "detect_modules": DetectModulesTool(code_meta),
        "plantuml_export": PlantUMLExportTool(plantuml_processor, f'{options.output_file}.png')
    }

    namespaces_metadata_json = json.dumps(code_meta.list_namespaces(), indent=None)

    inputs = {
        "language": options.language,
        "user_query": options.question,
        "root_namespace": options.root_namespace,
        "namespaces_metadata_json": namespaces_metadata_json,
    }    
    
    agents = AgentSystem("Question Answering",
                         llms_data, agents_data, tasks_data, tools=tools,
                         verbose=options.verbose)
    result = agents.execute(inputs)
    logger.info(result.get('usage_metrics'))
    return result

def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate system documentation from code metadata."
    )
    parser.add_argument(
        "--language",
        "-l",
        required=True,
        help="Programming language (e.g., 'java', 'python').",
    )
    parser.add_argument(
        "--folder-path",
        "-f",
        required=True,
        help="Path to the source code folder to scan.",
    )
    parser.add_argument(
        "--root-namespace",
        "-r",
        required=True,
        help="Root namespace or package for resolving references.",
    )
    parser.add_argument(
        "--output-file",
        "-o",
        required=True,
        help="Output file for the generated documentation (defaults to .md extension).",
    )
    parser.add_argument(
        "--plantuml-server",
        "-p",
        required=False,
        help="PlantUML server URL for generating diagrams.",
    )
    parser.add_argument(
        "--question",
        "-q",
        required=True,
        help="Question to ask the system.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging.",
    )
    return parser.parse_args()

def main():
    args = parse_args()
    
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING)
    
    file_path, file_ext = os.path.splitext(args.output_file)
    
    options = GenerationOptions(
        language=args.language.lower(),
        root_namespace=args.root_namespace,
        output_file=file_path,
        folder_path=args.folder_path,
        plantuml_server=args.plantuml_server,
        question=args.question,
        verbose=args.verbose if args.verbose else False
    )

    try:
        if not os.path.exists(options.folder_path):
            raise FileNotFoundError(f"The folder {options.folder_path} does not exist.")
        if not os.path.isdir(options.folder_path):
            raise NotADirectoryError(f"The path {options.folder_path} is not a directory.")

        namespaces = generate_metadata(args.language, args.folder_path)
        resolve_references(namespaces, args.root_namespace)
        
        results = question_answering(namespaces, options)
        
        raw_output = f"**Question:** {args.question}\n\n"
        raw_output += results.get('raw_output', '')
        
        if file_ext != '.md':
            file_ext += '.md'
        write_file(f"{file_path}{file_ext}", raw_output)
                
    except Exception as e:
        traceback.print_exc()
        logger.error(f"An error occurred: {str(e)}")
        sys.exit(1)
        
if __name__ == "__main__":
    main()