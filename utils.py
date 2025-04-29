import json
import yaml

def write_file(file_path, content):
    with open(file_path, 'w') as file:
        file.write(content)

def read_file(file_path):
    with open(file_path, 'r') as file:
        return file.read()
    
def read_json_file(json_file):
    with open(json_file, 'r') as file:
        print(file)
        return json.load(file)

def read_yaml_file(yaml_file):
    with open(yaml_file, 'r') as file:
        return yaml.safe_load(file)