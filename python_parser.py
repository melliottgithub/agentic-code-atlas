import re
from typing import Optional
from pathlib import Path
from code_parser import CodeParser
from metadata import ClassMetadata, Namespace
from tree_sitter import Language, Parser
import tree_sitter_python

# Load the Python language for Tree-sitter
PYTHON_LANGUAGE = Language(tree_sitter_python.language())
parser = Parser(PYTHON_LANGUAGE)

def walk(node):
    """
    Recursively yields a node and all of its descendants.
    """
    yield node
    for child in node.children:
        yield from walk(child)

class PythonCodeParser(CodeParser):
    """
    Concrete implementation of CodeParser for Python source files.
    """
    def __init__(self):
        super().__init__()
        # Regex to extract decorator name (without the '@')
        self.decorator_re = r"(?<=@)([A-Za-z_][A-Za-z0-9_]*)"

    def parse_source(self, source_code: str, file_path: Optional[str]) -> Namespace:
        # Parse the source code into a syntax tree
        tree = parser.parse(bytes(source_code, "utf8"))
        root_node = tree.root_node
        # Initialize namespace metadata
        self.namespace = Namespace(name="", imports=set())

        # Derive module name from file path if available
        if file_path:
            module_name = Path(file_path).stem
            self.namespace.name = module_name

        # Walk the tree and handle relevant node types
        def traverse(node):
            if node.type == "import_statement":
                self._parse_import(node)
            elif node.type == "import_from_statement":
                self._parse_from_import(node)
            elif node.type == "class_definition":
                self._parse_class(node, file_path)
            for child in node.children:
                traverse(child)

        traverse(root_node)
        return self.namespace

    def resolve_references(self, metadata, root_namespace):
        """Stub for resolving Python import and type references."""
        raise NotImplementedError("PythonCodeParser.resolve_references not implemented.")

    def _parse_import(self, node):
        """
        Parses `import module` statements.
        """
        module_node = node.child_by_field_name("module")
        if module_node:
            self.namespace.imports.add(module_node.text.decode("utf8"))

    def _parse_from_import(self, node):
        import_from_statement = node.text.decode("utf8")
        module_name = re.search(r'from\s+(\S+)\s+import', import_from_statement).group(1)
        imported_names = [f"{module_name}.{name.strip()}" for name in import_from_statement.split("import", 1)[1].split(",")]
        for name in imported_names:
            name = name.strip()
            if name:
                self.namespace.imports.add(name)
                
    def _parse_attributes_from_assignment(self, expression_statement):
        attribute_names = []
        for child in expression_statement.named_children:
            if child.type == "assignment":
                # Get the left-hand side of the assignment
                lhs = child.child_by_field_name("left")
                if lhs and lhs.type == "attribute":
                    _, _, attribute_name = lhs.children
                    attribute_names.append(attribute_name.text.decode("utf8"))
        return attribute_names
    
    def _get_last_of_type(self, nodes, type: str):
        last_node = None
        for node in nodes.children:
            if node.type == type:
                last_node = node
        return last_node
    
    def _get_method_call(self, call_statement):
        invoked_function = call_statement.child_by_field_name("function")
        if invoked_function:
            return self._get_last_of_type(invoked_function, "identifier")
        return None

    def _parse_class(self, node, file_path: Optional[str]):
        """
        Parses class definitions, extracting class name, decorators, attributes, and methods.
        """
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        class_name = name_node.text.decode("utf8")
        # Register the class in the namespace
        _ = self.namespace.add_class(class_name, file_path)

        # Extract decorator names
        for child in node.children:
            if child.type == "decorator":
                m = re.search(self.decorator_re, child.text.decode("utf8"))
                if m:
                    self.namespace.add_class_stereotype(class_name, m.group(1))

        # Parse class body for attributes and methods
        body_node = node.child_by_field_name("body")
        if body_node:
            for stmt in body_node.named_children:
                # Class attribute: simple assignment
                if stmt.type == "assignment":
                    target = stmt.child_by_field_name("left")
                    if target and target.type == "identifier":
                        self.namespace.add_class_attribute(
                            class_name=class_name,
                            name=target.text.decode("utf8"),
                            type_=""
                        )
                # Method definition inside a class
                elif stmt.type == "function_definition":
                    self._parse_method(stmt, class_name)

    def _parse_method(self, node, class_name):
        """
        Parses method definitions inside classes.
        """
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        method_name = name_node.text.decode("utf8")
        params = []
        invocations = []

        # Extract parameters
        params_node = node.child_by_field_name("parameters")
        if params_node:
            for param in params_node.named_children:
                if param.type == "parameter":
                    p_name = param.child_by_field_name("name")
                    if p_name:
                        params.append({
                            "name": p_name.text.decode("utf8"),
                            "type": ""
                        })


        body_node = node.child_by_field_name("body")
        # Extract attributes from the method body
        if body_node:
            for stmt in body_node.named_children:
                if stmt.type == "expression_statement":
                    attribute_names = self._parse_attributes_from_assignment(stmt)
                    for attribute_name in attribute_names:
                        self.namespace.add_class_attribute(
                            class_name=class_name,
                            name=attribute_name,
                            type_="")
        
        # Extract method invocations
            calls = set()
            for n in walk(body_node):
                if n.type == "call":
                    method_call = self._get_method_call(n)
                    if method_call:
                        calls.add(method_call.text.decode("utf8"))
            invocations = list(calls)

        # Register the method in the class metadata
        self.namespace.add_class_method(
            class_name=class_name,
            method_name=method_name,
            parameters=params,
            invoked_methods=invocations
        )
