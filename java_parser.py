import re
from typing import Optional
from code_parser import CodeParser
from metadata import ClassMetadata, Namespace
from tree_sitter import Language, Parser
import tree_sitter_java

JAVA_LANGUAGE = Language(tree_sitter_java.language())
parser = Parser(JAVA_LANGUAGE)

def walk(node):
    yield node
    for child in node.children:
        yield from walk(child)
        
def get_child_by_type(node, type):
    for child in node.children:
        if child.type == type:
            return child
    return None

class JavaCodeParser(CodeParser):
    """
    Concrete implementation of CodeParser for Java source files.
    """
    def __init__(self):
        self.annotation_re = r"(?<=@)([A-Za-z]+)"
    
    def parse_source(self, source_code: str, file_path: Optional[str]) -> Namespace:
        tree = parser.parse(bytes(source_code, "utf8"))
        root_node = tree.root_node
        self.namespace = Namespace(name="", imports=set())

        def traverse(node):
            if node.type == "package_declaration":
                self._parse_package(node)
            elif node.type == "import_declaration":
                self._parse_import(node)
            elif node.type in {"class_declaration", "interface_declaration"}:
                self._parse_class(node, file_path)
            for child in node.children:
                traverse(child)

        traverse(root_node)
        return self.namespace

    def resolve_references(self, metadata, root_namespace):
        """Stub for resolving Java import and type references."""
        raise NotImplementedError("JavaCodeParser.resolve_references not implemented.")

    def _parse_package(self, node):
        name_node = node.named_child(0)
        if name_node:
            self.namespace.name = name_node.text.decode("utf8")

    def _parse_import(self, node):
        path_node = node.named_child(0)
        if path_node:
            self.namespace.imports.add(path_node.text.decode("utf8"))
            
    def _parse_class_modifiers(self, node):
        modifiers = []
        modifiers_node = get_child_by_type(node, "modifiers")
        if not modifiers_node:
            return modifiers
        for child in modifiers_node.children:
            if child.type == "annotation" or child.type == "marker_annotation":
                name = re.search(self.annotation_re, child.text.decode("utf8")).group(1)
                modifiers.append(name)
        return modifiers

    def _parse_class(self, node, file_path: Optional[str]):
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        class_name = name_node.text.decode("utf8")
        _ = self.namespace.add_class(class_name, file_path)
        
        for stereotype in self._parse_class_modifiers(node):
            self.namespace.add_class_stereotype(class_name, stereotype)

        body_node = node.child_by_field_name("body")
        if body_node:
            for child in body_node.named_children:
                if child.type == "field_declaration":
                    # Add class attribute
                    type_node = child.child_by_field_name("type")
                    for decl in child.named_children:
                        if decl.type == "variable_declarator":
                            name_var = decl.child_by_field_name("name")
                            if name_var:
                                self.namespace.add_class_attribute(
                                    class_name=class_name,
                                    name=name_var.text.decode("utf8"),
                                    type_=type_node.text.decode("utf8") if type_node else ""
                                )
                elif child.type in {"method_declaration", "constructor_declaration"}:
                    self._parse_method(child, class_name)

    def _parse_method(self, node, class_name):
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        method_name = name_node.text.decode("utf8")
        params = []
        invocations = []

        params_node = node.child_by_field_name("parameters")
        if params_node:
            for param in params_node.named_children:
                if param.type == "formal_parameter":
                    p_type = param.child_by_field_name("type")
                    p_name = param.child_by_field_name("name")
                    if p_type and p_name:
                        params.append({
                            "name": p_name.text.decode("utf8"),
                            "type": p_type.text.decode("utf8")
                        })

        body_node = node.child_by_field_name("body")
        if body_node:
            calls = set()
            for n in walk(body_node):
                if n.type == "method_invocation":
                    name_child = n.child_by_field_name("name")
                    if name_child:
                        calls.add(name_child.text.decode("utf8"))
            invocations = list(calls)

        self.namespace.add_class_method(
            class_name=class_name,
            method_name=method_name,
            parameters=params,
            invoked_methods=invocations
        )
