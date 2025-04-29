from typing import Optional
from kopyt import Parser as KotlinParser
from kopyt.node import ClassDeclaration, FunctionDeclaration, PostfixUnaryExpression, NavigationSuffix
from kopyt.node import Statement, SimpleIdentifier, CallSuffix, SingleAnnotation
from code_parser import CodeParser
from metadata import Namespace

def extract_post_fix_expressions_old(block):
    if getattr(block, 'sequence', None) is None:
        return []
    postFixExpressions = []
    try:
        for cs in block.sequence:
            if isinstance(cs, Statement):
                expression = getattr(cs.statement, 'expression', None)
                if isinstance(cs.statement, PostfixUnaryExpression):
                    postFixExpressions.append(cs.expression)
                elif expression is not None:
                    while expression is not None:
                        if isinstance(expression, PostfixUnaryExpression):
                            postFixExpressions.append(expression)
                            break
                        else:
                            expression = getattr(expression, 'expression', None)
    except Exception as e:
        print(f"Error extracting postfix expressions: {str(e)}")
        print(f"Block position: {block.position}")
    return postFixExpressions

def extract_post_fix_expressions(block):
    if getattr(block, 'sequence', None) is None:
        return []
    postfix_expressions = []
    
    # recursive function to extract all postfix on __slots__ of the object
    def recurse(obj):
        if isinstance(obj, PostfixUnaryExpression):
            postfix_expressions.append(obj)
        elif hasattr(obj, '__slots__'):
            for key in obj.__slots__:
                recurse(getattr(obj, key))

    for statement in block.sequence:
        recurse(statement)
    
    return postfix_expressions

def get_modifier_name(modifier):
    if isinstance(modifier, SingleAnnotation):
        return modifier.name
    elif isinstance(modifier, str):
        return modifier
    else:
        return None

class KotlinCodeParser(CodeParser):
    def parse_source(self, source_code: str, file_path: Optional[str]):
        """Parses a Kotlin source file and returns metadata."""

        parser = KotlinParser(source_code)
        ast = parser.parse()

        # Create a Namespace instance
        namespace_name = ast.package.name if ast.package else None
        namespace = Namespace(name=namespace_name, imports=[imp.name for imp in ast.imports])

        for decl in ast.declarations:
            if isinstance(decl, ClassDeclaration):
                # Add class to the namespace
                namespace.add_class(decl.name, file_path)

                functions = [f for f in decl.body.members if isinstance(f, FunctionDeclaration)] if decl.body else []
                
                modifier_names = [get_modifier_name(modifier) for modifier in decl.modifiers]
                
                # Add stereotypes to the class
                for modifier_name in modifier_names:
                    namespace.add_class_stereotype(decl.name, modifier_name)

                # Add attributes from the constructor parameters
                if decl.constructor and decl.constructor.parameters:
                    for attr in decl.constructor.parameters:
                        namespace.add_class_attribute(
                            class_name=decl.name,
                            name=attr.name,
                            type_=str(attr.type) if attr.type else None
                        )

                # Add methods to the class
                for method in functions:
                    parameters = [
                        {
                            "name": param.name,
                            "type": str(param.type) if param.type else None
                        }
                        for param in method.parameters
                    ]
                    invoked_methods = self.parse_invoked_methods(method.body) if method.body else []

                    namespace.add_class_method(
                        class_name=decl.name,
                        method_name=method.name,
                        parameters=parameters,
                        invoked_methods=invoked_methods
                    )

        return namespace

    def resolve_references(self, metadata, root_namespace):
        """Resolves user-defined and external references."""
        for class_name, class_data in metadata["classes"].items():
            for attr in class_data["attributes"]:
                attr["is_user_defined"] = (
                    attr["type"] and attr["type"].startswith(root_namespace)
                )

            for method in class_data["methods"]:
                for param in method["parameters"]:
                    param["is_user_defined"] = (
                        param["type"] and param["type"].startswith(root_namespace)
                    )
                for invoked in method["invoked_methods"]:
                    invoked["is_user_defined"] = (
                        invoked["receiver"] and invoked["receiver"].startswith(root_namespace)
                    )

        return metadata

    def parse_invoked_methods(self, method_body):
        import sys
        """Parses the body of a method to extract invoked methods by recursively traversing the AST."""
        invoked_methods = []
        
        for pfe in extract_post_fix_expressions(method_body):
            if isinstance(pfe, PostfixUnaryExpression):
                if isinstance(pfe.expression, SimpleIdentifier):
                    if isinstance(pfe.suffixes[0], CallSuffix):
                        invoked_methods.append(f"{pfe.expression.value}.constructor")
                    if isinstance(pfe.suffixes[0], NavigationSuffix):
                        invoked_methods.append(f"{pfe.expression.value}.{pfe.suffixes[0].suffix}")

        return invoked_methods
