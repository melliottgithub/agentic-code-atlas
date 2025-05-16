import os
import json
import sys
import traceback
import argparse
import logging
from typing import Any, Dict, Optional
from dataclasses import dataclass

from code_analyzer import generate_metadata, resolve_references

from code_meta_tool import CodeMeta, ListNamespacesTool
from agents import AgentSystem
from metadata import Namespace
from plantuml_tool import PlantUMLExportTool, createPlantUMLProcessor
from utils import TokenStats, read_yaml_file, write_file

MAX_RPM = 30

logger = logging.getLogger(__name__)

@dataclass
class GenerationOptions:
    language: str
    root_namespace: str
    output_dir: str
    folder_path: str
    plantuml_server: Optional[str] = None,
    max_rpm: Optional[int] = None,
    verbose: Optional[bool] = False

class DocumentationWorkflow:
    def __init__(self, metadata: Dict[str, Namespace], options: GenerationOptions):
        self.metadata = metadata
        self.options = options
        self.plantuml_processor = createPlantUMLProcessor(options.plantuml_server)
        self.verbose = self.options.verbose if self.options.verbose else False
        self.token_stats = TokenStats()
        logger.info(f"PlantUML server: {self.plantuml_processor.url}")
        
    def generate(self):
        inputs = {
            "language": self.options.language,
            "root_namespace": self.options.root_namespace,
        }
        
        print(f"Generating system overview documentation...")
        results = self._generate_system_overview(inputs)
        write_file(f'{self.options.output_dir}/system_overview.md', results.get('raw_output', ''))
        
        print(f"Generating system architecture documentation...")
        results = self._generate_system_architecture(inputs)
        write_file(f'{self.options.output_dir}/system_architecture.md', results.get('raw_output', ''))
        
        print(f"Generating system components documentation...")
        results = self._generate_system_components(inputs)
        write_file(f'{self.options.output_dir}/system_components.md', results.get('raw_output', ''))
        
        print(f"Generating entry points documentation...")
        results = self._identify_entry_points(inputs)
        write_file(f'{self.options.output_dir}/entry_points.md', results.get('raw_output', ''))

    def _generate_system_overview(self, inputs: Dict[str, Any]):
        llms_data = read_yaml_file('conf/llms.yaml')
        agents_data = read_yaml_file('conf/agents.yaml')
        tasks_data = read_yaml_file('conf/task_system_overview.yaml')

        code_meta = CodeMeta(self.metadata)

        tools = {
            "list_namespaces": ListNamespacesTool(code_meta),
            "plantuml_export": PlantUMLExportTool(self.plantuml_processor, f'{self.options.output_dir}/c4_system_context.png')
        }

        agents = AgentSystem("System Overview", 
                             llms_data, agents_data, tasks_data, tools=tools,
                             max_rpm=self.options.max_rpm, verbose=self.verbose)
        result = agents.execute(inputs)
        self.token_stats.update(result.get('usage_metrics'))
        return result

    def _generate_system_architecture(self, inputs: Dict[str, Any]):
        llms_data = read_yaml_file('conf/llms.yaml')
        agents_data = read_yaml_file('conf/agents.yaml')
        tasks_data = read_yaml_file('conf/task_system_architecture.yaml')

        code_meta = CodeMeta(self.metadata)
        
        tools = {
            "list_namespaces": ListNamespacesTool(code_meta),
            "plantuml_export": PlantUMLExportTool(self.plantuml_processor, f'{self.options.output_dir}/c4_container_diagram.png')
        }

        agents = AgentSystem("System Architecture", llms_data, agents_data, tasks_data, tools=tools)
        result = agents.execute(inputs)
        self.token_stats.update(result.get('usage_metrics'))
        return result

    def _generate_system_components(self, inputs: Dict[str, Any]):
        llms_data = read_yaml_file('conf/llms.yaml')
        agents_data = read_yaml_file('conf/agents.yaml')
        tasks_data = read_yaml_file('conf/task_system_components.yaml')

        code_meta = CodeMeta(self.metadata)
        raw_output = ""
        components = code_meta.detect_modules()
        if self.verbose:
            write_file('debug-detect_modules.json', json.dumps(components, indent=2))
        for component_id, namespaces in components.items():

            tools = {
                "plantuml_export": PlantUMLExportTool(self.plantuml_processor, f'{self.options.output_dir}/c4_component_{component_id}.png')
            }
            
            logger.debug(f"Analyzing component: {component_id}, namespaces: {namespaces}")
            
            meta_data_json = json.dumps(code_meta.get_namespaces_meta(namespaces), indent=None)
            
            inputs['component_id'] = component_id
            inputs['meta_data_json'] = meta_data_json
                
            agents = AgentSystem("System Components", llms_data, agents_data, tasks_data, tools=tools)
            try:
                result = agents.execute(inputs)
                self.token_stats.update(result.get('usage_metrics'))
            
                raw_output += '\n\n' + result.get('raw_output', '')
            except Exception as e:
                traceback.print_exc()
                logger.debug(f"Error analyzing component {component_id}: {str(e)}")

        return { "raw_output": raw_output }

    def _identify_entry_points(self, inputs: Dict[str, Any]):
        llms_data = read_yaml_file('conf/llms.yaml')
        agents_data = read_yaml_file('conf/agents.yaml')
        tasks_data = read_yaml_file('conf/task_entry_points.yaml')

        code_meta = CodeMeta(self.metadata)
        tools = {
            "list_namespaces": ListNamespacesTool(code_meta)
        }

        agents = AgentSystem("Identify Entry Points", llms_data, agents_data, tasks_data, tools=tools)
        result = agents.execute(inputs)
        self.token_stats.update(result.get('usage_metrics'))
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
        "--output-dir",
        "-o",
        required=True,
        help="Directory where markdown files will be written.",
    )
    parser.add_argument(
        "--plantuml-server",
        "-p",
        required=False,
        help="PlantUML server URL for generating diagrams.",
    )
    parser.add_argument(
        "--max-rpm",
        "-m",
        required=False,
        help="Maximum requests per minute for the LLM API (defaults is 30).",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        required=False,
        help="Enable verbose logging.",
    )
    return parser.parse_args()

def main():
    args = parse_args()
    
    max_rpm = args.max_rpm if args.max_rpm else MAX_RPM
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING)
    
    options = GenerationOptions(
        language=args.language.lower(),
        root_namespace=args.root_namespace,
        output_dir=args.output_dir,
        folder_path=args.folder_path,
        plantuml_server=args.plantuml_server,
        max_rpm=max_rpm,
        verbose=args.verbose
    )

    try:
        if not os.path.exists(options.folder_path):
            raise FileNotFoundError(f"The folder {options.folder_path} does not exist.")
        if not os.path.isdir(options.folder_path):
            raise NotADirectoryError(f"The path {options.folder_path} is not a directory.")

        # create output directory if it doesn't exist
        os.makedirs(options.output_dir, exist_ok=True)

        namespaces = generate_metadata(options.language, options.folder_path)
        resolve_references(namespaces, options.root_namespace)
        
        workflow = DocumentationWorkflow(namespaces, options)
        workflow.generate()
        
        print(workflow.token_stats)

    except Exception as e:
        traceback.print_exc()
        logger.debug(f"An error occurred: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()