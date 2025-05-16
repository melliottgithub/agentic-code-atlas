import json
import os
import sys
import traceback
from typing import Dict

from parsers.java_parser import JavaCodeParser
from metadata import Namespace

from code_parser import CodeParser
from parsers.kotlin_parser import KotlinCodeParser
from parsers.php_parser import PhpCodeParser
from parsers.python_parser import PythonCodeParser

# Utility functions
def save_metadata(metadata_dict, output_path):
    """Saves metadata to a JSON file."""
    with open(output_path, "w") as json_file:
        json.dump(metadata_dict, json_file, indent=None)

def process_files_in_folder(folder_path, extensions):
    """
    Recursively process files in a folder, filtering by the given extensions.
    """
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith(extensions):
                yield os.path.join(root, file)

def generate_metadata(language: str, folder_path: str) -> Dict[str, Namespace]:
    """
    Generates metadata for a given folder path and extensions.
    """
    code_parser: CodeParser
    if language == "kotlin":
        code_parser = KotlinCodeParser()
        extensions = (".kt",)
    elif language == "php":
        code_parser = PhpCodeParser()
        extensions = (".php",)
    elif language == "java":
        code_parser = JavaCodeParser()
        extensions = (".java",)
    elif language == "python":
        code_parser = PythonCodeParser()
        extensions = (".py",)
    else:
        raise ValueError(f"Unsupported language: {language}")
    
    namespaces = {}
    for file_path in process_files_in_folder(folder_path, extensions):
        #print(f"Processing file: {file_path}")
        try:
            with open(file_path, 'r') as file:
                source_code = file.read()

            # Parse the source code to get metadata
            relative_path = os.path.relpath(file_path, folder_path)
            metadata = code_parser.parse_source(source_code, relative_path)

            # Merge namespaces
            namespace_name = metadata.name
            if namespace_name in namespaces:
                namespaces[namespace_name].merge_namespace(metadata)
            else:
                namespaces[namespace_name] = metadata

        except Exception as file_error:
            print(f"Error processing file {file_path}: {file_error}")
            traceback.print_exc()
            sys.exit(1)

    return namespaces

def resolve_references(namespaces: Dict[str, Namespace], root_namespace: str):
    """
    Resolves references and adds dependencies between classes.
    """
    for namespace in namespaces.values():
        for class_metadata in namespace.classes.values():
            for method in class_metadata.methods:
                resolved_invocations = []
                for invocation in method['invoked_methods']:
                    # Attempt to resolve the fully qualified name
                    resolved = False
                    for import_statement in namespace.imports:
                        if invocation.startswith(import_statement.split('.')[-1]):
                            resolved_invocations.append(import_statement + '.' + invocation)
                            resolved = True
                            break
                    if not resolved:
                        # If not resolved, assume it's within the same namespace
                        resolved_invocations.append(namespace.name + '.' + invocation)
                    # Add dependency between classes
                    class_metadata.add_dependency(invocation)
                    method['invoked_methods'] = resolved_invocations

def main():
    if len(sys.argv) != 5:
        print("Usage: python code_analyzer.py <language> <folder_path> <root_namespace> <output_file>")
        sys.exit(1)

    language = sys.argv[1].lower()
    folder_path = sys.argv[2]
    root_namespace = sys.argv[3]
    output_file = sys.argv[4]

    try:
        if not os.path.exists(folder_path):
            raise FileNotFoundError(f"The folder {folder_path} does not exist.")
        if not os.path.isdir(folder_path):
            raise NotADirectoryError(f"The path {folder_path} is not a directory.")

        namespaces = generate_metadata(language, folder_path)
        resolve_references(namespaces, root_namespace)
        
        # Step 3: Convert namespaces to a dictionary format and save
        merged_metadata = {ns_name: ns_obj.to_dict() for ns_name, ns_obj in namespaces.items()}
        save_metadata(merged_metadata, output_file)
        print(f"Metadata saved to {output_file}")
        
    except Exception as e:
        traceback.print_exc()
        print(f"An error occurred: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
