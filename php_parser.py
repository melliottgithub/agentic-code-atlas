from typing import Optional
from code_parser import CodeParser

from metadata import ClassMetadata, Namespace
from tree_sitter import Language, Parser
import tree_sitter_php as tsphp

# Load the PHP language
PHP_LANGUAGE = Language(tsphp.language_php())
parser = Parser(PHP_LANGUAGE)

def parse_php_source(code):
    tree = parser.parse(bytes(code, "utf8"))
    root_node = tree.root_node

    metadata = {
        "namespace": "",
        "imports": [],
        "classes": {}
    }

    namespace = Namespace(
        namespace
    )

    def parse_namespace(node):
        namespace_node = node.child_by_field_name("name")
        if namespace_node:
            namespace_name = namespace_node.text.replace(b"\\", b".")
            metadata["namespace"] = namespace_name.decode("utf8")

    def parse_imports(node):
        for child in node.children:
            if child.type == "namespace_use_clause":
                qualified_name = child.children[0].text
                if qualified_name:
                    qualified_name = qualified_name.replace(b"\\", b".")
                    metadata["imports"].append(qualified_name.decode("utf8"))

    def parse_class(node):
        class_name_node = node.child_by_field_name("name")
        if class_name_node:
            class_name = class_name_node.text.decode("utf8")
            class_metadata = {
                "attributes": [],
                "methods": []
            }
            metadata["classes"][class_name] = class_metadata
            
            declaration_list = tranverse_until_node_type(node, "declaration_list")

            for child in declaration_list.children:
                if child.type == "property_declaration":
                    parse_attribute(child, class_metadata)
                elif child.type == "method_declaration":
                    parse_method(child, class_metadata)

    def parse_attribute(node, class_metadata):
        attribute_name = None
        for child in node.children:
            if child.type == "property_element":
                attribute_name = child.child_by_field_name("name")
        if attribute_name:
            class_metadata["attributes"].append({
                "name": attribute_name.text.decode("utf8"),
                "type": None
            })

    def parse_method(node, class_metadata):
        method_name_node = node.child_by_field_name("name")
        if method_name_node:
            method_name = method_name_node.text.decode("utf8")
            method_metadata = {
                "name": method_name,
                "parameters": [],
                "invoked_methods": []
            }
            class_metadata["methods"].append(method_metadata)
            
            formal_parameters = tranverse_until_node_type(node, "formal_parameters")
            if formal_parameters:
                for child in formal_parameters.children:
                    parse_parameter(child, method_metadata)

            for child in node.children:
                if child.type == "compound_statement":
                    parse_invoked_method(child, method_metadata)

    def parse_parameter(node, method_metadata):
        parameter_name_node = node.child_by_field_name("name")
        parameter_type_node = node.child_by_field_name("type")
        if parameter_name_node and parameter_type_node:
            parameter_name = parameter_name_node.text.decode("utf8")
            parameter_type = parameter_type_node.text.decode("utf8")
            method_metadata["parameters"].append({
                "name": parameter_name,
                "type": parameter_type
            })

    def parse_invoked_method(node, method_metadata):
        calls = set()
        call_types = {"scoped_call_expression", "member_call_expression"} # , "call_expression"
        for n in walk(node):
            if n.type in call_types:
                invoked = get_invoked_method_name(n)
                calls.add(invoked)
        for invoked in calls:
            method_metadata["invoked_methods"].append(invoked)

    def get_invoked_method_name(node):
        member_name_node = node.child_by_field_name("name")
        variable_name_node = tranverse_until_node_type(node, "name")
        if member_name_node or variable_name_node:
            variable_name = variable_name_node.text.decode("utf8")
            member_name = member_name_node.text.decode("utf8")
            return f"{variable_name}::{member_name}"
        return None
    
    def walk(node):
        yield node
        for child in node.children:
            yield from walk(child)

    def traverse(node):
        if node.type == "namespace_definition":
            parse_namespace(node)
        elif node.type == "namespace_use_declaration":
            parse_imports(node)
        elif node.type == "class_declaration":
            parse_class(node)
        for child in node.children:
            traverse(child)

    def tranverse_until_node_type(node, target_type):
        """
        Tranverse the tree until a node with the target type is found.
        """
        if node.type == target_type:
            return node
        for child in node.children:
            result = tranverse_until_node_type(child, target_type)
            if result:
                return result
        return None

    traverse(root_node)
    return metadata

def tranverse_until_node_type(node, target_type):
    """
    Tranverse the tree until a node with the target type is found.
    """
    if node.type == target_type:
        return node
    for child in node.children:
        result = tranverse_until_node_type(child, target_type)
        if result:
            return result
    return None

def walk(node):
    yield node
    for child in node.children:
        yield from walk(child)

class PhpCodeParser(CodeParser):
    def parse_source(self, source_code, file_path: Optional[str]):
        tree = parser.parse(bytes(source_code, "utf8"))
        root_node = tree.root_node
        
        self.namespace = Namespace(name="", imports=[])
        
        def traverse(node):
            if node.type == "namespace_definition":
                self._parse_namespace(node)
            elif node.type == "namespace_use_declaration":
                self._parse_imports(node)
            elif node.type == "class_declaration":
                self._parse_class(node, file_path)
            for child in node.children:
                traverse(child)
            
        traverse(root_node)
        
        return self.namespace

    def resolve_references(self, metadata, root_namespace):
        """Stub for resolving references in PHP files."""
        raise NotImplementedError("PhpCodeParser is not yet implemented.")

    def _parse_namespace(self, node):
        namespace_node = node.child_by_field_name("name")
        if namespace_node:
            self.namespace.name = namespace_node.text.replace(b"\\", b".").decode("utf8")

    def _parse_imports(self, node):
        for child in node.children:
            if child.type == "namespace_use_clause":
                qualified_name = child.children[0].text
                if qualified_name:
                    qualified_name = qualified_name.replace(b"\\", b".")
                    self.namespace.imports.add(qualified_name.decode("utf8"))
                    
    def _parse_class(self, node, file_path: Optional[str]):
        class_name_node = node.child_by_field_name("name")
        if class_name_node:
            class_name = class_name_node.text.decode("utf8")

            class_metadata = self.namespace.add_class(class_name, file_path)
            
            declaration_list = tranverse_until_node_type(node, "declaration_list")

            for child in declaration_list.children:
                if child.type == "property_declaration":
                    self._parse_attribute(child, class_name)
                elif child.type == "method_declaration":
                    self._parse_method(child, class_name)
                
            self.namespace.add_class(class_metadata)
                    
    def _parse_attribute(self, node, class_name):
        attribute_name = None
        for child in node.children:
            if child.type == "property_element":
                attribute_name = child.child_by_field_name("name")
        if attribute_name:
            self.namespace.add_class_attribute(
                class_name = class_name,
                name = attribute_name.text.decode("utf8"),
                type_ = ""
            )
            
    def _parse_method(self, node, class_name):
        method_name_node = node.child_by_field_name("name")
        if method_name_node:
            method_name = method_name_node.text.decode("utf8")
            method_metadata = {
                "name": method_name,
                "parameters": [],
                "invoked_methods": []
            }
            
            formal_parameters = tranverse_until_node_type(node, "formal_parameters")
            if formal_parameters:
                for child in formal_parameters.children:
                    self._parse_parameter(child, method_metadata)

            for child in node.children:
                if child.type == "compound_statement":
                    self._parse_invoked_method(child, method_metadata)
                    
            self.namespace.add_class_method(
                class_name = class_name,
                method_name = method_name,
                parameters = method_metadata["parameters"],
                invoked_methods = method_metadata["invoked_methods"]
            )
            
    def _parse_parameter(self, node, method_metadata):
        parameter_name_node = node.child_by_field_name("name")
        parameter_type_node = node.child_by_field_name("type")
        if parameter_name_node and parameter_type_node:
            parameter_name = parameter_name_node.text.decode("utf8")
            parameter_type = parameter_type_node.text.decode("utf8")
            method_metadata["parameters"].append({
                "name": parameter_name,
                "type": parameter_type
            })
            
    def _parse_invoked_method(self, node, method_metadata):
        calls = set()
        call_types = {"scoped_call_expression", "member_call_expression"} # , "call_expression"
        for n in walk(node):
            if n.type in call_types:
                invoked = self._get_invoked_method_name(n)
                calls.add(invoked)
        for invoked in calls:
            method_metadata["invoked_methods"].append(invoked)
            
    def _get_invoked_method_name(self, node):
        member_name_node = node.child_by_field_name("name")
        variable_name_node = tranverse_until_node_type(node, "name")
        if member_name_node or variable_name_node:
            variable_name = variable_name_node.text.decode("utf8")
            member_name = member_name_node.text.decode("utf8")
            return f"{variable_name}::{member_name}"
        return None