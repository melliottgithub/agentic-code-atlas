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
    
class TokenStats:
    def __init__(self, data=None):
        self.total_tokens = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.successful_requests = 0

        self.update(data)

    def update(self, data):
        if not data:
            return
        self.total_tokens += data.get("total_tokens", 0)
        self.prompt_tokens += data.get("prompt_tokens", 0)
        self.completion_tokens += data.get("completion_tokens", 0)
        self.successful_requests += data.get("successful_requests", 0)

    def __repr__(self):
        return (f"TokenStats(total_tokens={self.total_tokens}, "
                f"prompt_tokens={self.prompt_tokens}, "
                f"completion_tokens={self.completion_tokens}, "
                f"successful_requests={self.successful_requests})")