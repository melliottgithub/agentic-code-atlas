from typing import List, Dict, Optional, Union

class ClassMetadata:
    """
    Represents metadata for a class, including its attributes and methods.
    """
    def __init__(self, name: str, file_path: Optional[str]):
        self.name = name
        self.file_path = file_path
        self.stereotypes = []
        self.attributes = []
        self.methods = []
        self.dependencies = []

    def add_stereotype(self, stereotype: str):
        self.stereotypes.append(stereotype)

    def add_attribute(self, name: str, type_: str):
        self.attributes.append({
            "name": name,
            "type": type_
        })

    def add_method(self, name: str, parameters: List[Dict[str, Union[str, bool]]], invoked_methods: List[Dict[str, Union[str, bool]]]):
        self.methods.append({
            "name": name,
            "parameters": parameters,
            "invoked_methods": invoked_methods
        })
        
    def add_dependency(self, dependency: 'ClassMetadata'):
        self.dependencies.append(dependency)

class Namespace:
    """
    Represents a namespace, including imports and classes.
    """
    def __init__(self, name: str, imports: List[str]):
        self.name = name
        self.imports = set(imports)
        self.classes: Dict[ClassMetadata] = {}
        
    def add_imports(self, imports: List[str]):
        self.imports.update(imports)

    def add_class(self, class_name: str, file_path: str = None):
        if class_name not in self.classes:
            self.classes[class_name] = ClassMetadata(class_name, file_path)

    def add_class_attribute(self, class_name: str, name: str, type_: str):
        if class_name in self.classes:
            self.classes[class_name].add_attribute(name, type_)
        else:
            raise ValueError(f"Class '{class_name}' does not exist.")

    def add_class_method(self, class_name: str, method_name: str, \
        parameters: List[Dict[str, Union[str, bool]]], \
        invoked_methods: List[Dict[str, Union[str, bool]]]):

        if class_name in self.classes:
            self.classes[class_name].add_method(method_name, parameters, invoked_methods)
        else:
            raise ValueError(f"Class '{class_name}' does not exist.")
        
    def add_class_stereotype(self, class_name: str, stereotype: str):
        if class_name in self.classes:
            self.classes[class_name].add_stereotype(stereotype)
        else:
            raise ValueError(f"Class '{class_name}' does not exist.")

    def merge_namespace(self, other_namespace):
        """
        Merges another namespace into the current namespace.
        """
        if self.name != other_namespace.name:
            raise ValueError("Cannot merge namespaces with different names.")
        
        self.add_imports(other_namespace.imports)

        for class_name, class_metadata in other_namespace.classes.items():
            if class_name in self.classes:
                self.classes[class_name].attributes.extend(class_metadata.attributes)
                self.classes[class_name].methods.extend(class_metadata.methods)
            else:
                self.classes[class_name] = class_metadata

    def to_dict(self):
        """
        Converts the namespace to a dictionary format.
        """
        return {
            "name": self.name,
            "imports": list(self.imports),
            "classes": {
                class_name: {
                    "file_path": class_metadata.file_path,
                    "stereotypes": class_metadata.stereotypes,
                    "attributes": class_metadata.attributes,
                    "methods": class_metadata.methods
                }
                for class_name, class_metadata in self.classes.items()
            }
        }