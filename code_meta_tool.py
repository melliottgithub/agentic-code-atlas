import json
from collections import defaultdict
import logging
import networkx as nx
import community as community_louvain
from typing import Dict, List, Optional, Type

from pydantic import BaseModel, Field, PrivateAttr
from crewai.tools import BaseTool

from metadata import Namespace

logger = logging.getLogger(__name__)

class CodeMeta:
    """
    Refactored CodeMeta to accept a dictionary of Namespace objects instead of JSON.
    """
    def __init__(self, metadata: Dict[str, Namespace]):
        """
        :param metadata: A dictionary mapping namespace names to Namespace objects.
        """
        self.metadata = metadata

    def list_namespaces(self) -> Dict:
        """
        Return a JSON-like dict with overview for each namespace.
        """
        namespaces = {}
        for namespace_name, namespace_obj in self.metadata.items():
            ns_dict = namespace_obj.to_dict()
            namespaces[namespace_name] = {
                "imports": ns_dict.get("imports", []),
                "classes": {}
            }

            for class_name, class_data in ns_dict['classes'].items():
                attributes = class_data.get('attributes', None)
                methods = class_data.get('methods', None)
                stereotypes = class_data.get('stereotypes', None)
                
                class_stats = {}

                if attributes:
                    class_stats["attribute_names"] = ", ".join([attr['name'] for attr in attributes])
                    
                if methods:
                    class_stats["method_names"] = ", ".join([m['name'] for m in methods])
                
                if stereotypes:
                    class_stats["stereotypes"] = ", ".join(stereotypes)

                namespaces[namespace_name]["classes"][class_name] = class_stats

        # DEBUG: Write to file
        #with open('list_namespaces.json', 'w') as file:
        #    file.write(json.dumps(namespaces, indent=None))
        return {
            "total_namespaces": len(namespaces),
            "namespaces": namespaces
        }

    def get_namespace_meta(self, namespace: str) -> Optional[dict]:
        """
        Return imports and classes for a given namespace in the metadata.
        """
        if namespace not in self.metadata:
            return None

        namespace_obj = self.metadata[namespace]
        ns_dict = namespace_obj.to_dict()
        response = {
            "namespace": namespace,
            "imports": ns_dict.get("imports", []),
            "classes": ns_dict.get("classes", {})
        }
        return response
    
    def get_children_namespaces(self, namespace: str) -> List:
        """
        Return a list of child namespaces for a given namespace.
        """
        children = []
        for ns in self.metadata.keys():
            if ns.startswith(namespace) and ns != namespace:
                children.append(ns)
        return children
    
    def get_namespaces_meta(self, namespaces: List[str]) -> Dict:
        """
        Return metadata for a list of namespaces.
        """
        response = {}
        for namespace_name in namespaces:
            namespace = self.get_namespace_meta(namespace_name)
            if namespace:
                response[namespace_name] = namespace
            else:
                children = self.get_children_namespaces(namespace_name)
                for child in children:
                    child_namespace = self.get_namespace_meta(child)
                    if child_namespace:
                        response[child] = child_namespace
            
        return response

    def get_classes_meta(self, fully_qualified_names: List[str]) -> Dict:
        """
        Return metadata for a given classes, each specified as a fully qualified name (including namespace).
        """
        namespaces = {}
        for fq_name in fully_qualified_names:
            namespace, class_name = fq_name.rsplit('.', 1)
            if namespace not in self.metadata:
                continue
            namespace_obj = self.metadata[namespace]
            class_data = namespace_obj.get_class(class_name)
            if class_data:
                if namespace not in namespaces:
                    namespaces[namespace] = {
                        "imports": namespace_obj.imports,
                        "classes": {}
                    }
                namespaces[namespace]["classes"][class_name] = class_data
        
        return namespaces

    def detect_modules(self):
        
        def get_namespace(import_str, namespaces_set):
            """
            Given a full import string (e.g. "com.mycompany.mypackage.MyClass"),
            try to determine which namespace (i.e. package) it belongs to by
            testing prefixes against the known namespaces.
            """
            tokens = import_str.split('.')
            # Try dropping tokens from the end until we get a match.
            for i in range(len(tokens), 0, -1):
                candidate = '.'.join(tokens[:i])
                if candidate in namespaces_set:
                    return candidate
            return None

        def build_graph(namespaces):
            """
            Build a weighted, undirected graph where nodes are namespaces and an edge
            between namespace A and B exists if A imports something from B (or vice-versa).
            """
            namespaces_set = set(namespaces.get("namespaces", {}).keys())
            G = nx.Graph()
            
            # Add all namespaces as nodes.
            for ns in namespaces_set:
                G.add_node(ns)
            
            # For each namespace, check its imports.
            for ns, info in namespaces.get("namespaces", {}).items():
                imports = info.get("imports", [])
                for imp in imports:
                    dep = get_namespace(imp, namespaces_set)
                    if dep and dep != ns:
                        # Add (or update) the edge with a weight (number of imports).
                        if G.has_edge(ns, dep):
                            G[ns][dep]["weight"] += 1
                        else:
                            G.add_edge(ns, dep, weight=1)
            
            return G
        
        # Build the dependency graph.
        G = build_graph(self.list_namespaces())
        
        # Compute the best partition (a dict: namespace -> community id)
        partition = community_louvain.best_partition(G, weight='weight')
        
        # Compute the modularity of the partitioning.
        try:
            modularity = community_louvain.modularity(partition, G, weight='weight')
            logger.info(f"Overall modularity: {modularity:.4f}")
        except Exception as e:
            logger.error(f"Error computing modularity: {e}")
            modularity = 0.0
        
        # Group namespaces by community id.
        modules = defaultdict(list)
        for ns, comm in partition.items():
            modules[comm].append(ns)
            
        return modules


# Tools interface

class DetectModulesTool(BaseTool):
    name: str = "detect_modules"
    description: str = "Detect modules in the source code base."
    result_as_answer: bool = True

    _code_meta: CodeMeta = PrivateAttr()

    def __init__(self, code_meta: CodeMeta, **kwargs):
        super().__init__(**kwargs)
        self._code_meta = code_meta

    def _run(self) -> str:
        return json.dumps(self._code_meta.detect_modules(), indent=None)

class ListNamespacesTool(BaseTool):
    name: str = "list_namespaces"
    description: str = "List all namespaces in the source code base."
    result_as_answer: bool = True

    _code_meta: CodeMeta = PrivateAttr()

    def __init__(self, code_meta: CodeMeta, **kwargs):
        super().__init__(**kwargs)
        self._code_meta = code_meta

    def _run(self) -> str:
        return json.dumps(self._code_meta.list_namespaces(), indent=None)

class GetNamespacesMetaTool(BaseTool):
    class ToolInputSchema(BaseModel):
        namespace_list: List[str] = Field(..., description="A list of fully qualified namespaces like 'com.mycompany.app'")

    name: str = "get_namespaces_meta"
    description: str = "Get detailed metadata of one ore more namespaces."
    args_schema: Type[BaseModel] = ToolInputSchema
    result_as_answer: bool = True

    _code_meta: CodeMeta = PrivateAttr()

    def __init__(self, code_meta: CodeMeta, **kwargs):
        super().__init__(**kwargs)
        self._code_meta = code_meta

    def _run(self, namespace_list: list[str]) -> str:
        return json.dumps(self._code_meta.get_namespaces_meta(namespace_list), indent=None)

class GetClassesMetaTool(BaseTool):
    class ToolInputSchema(BaseModel):
        fully_qualified_names: List[str] = Field(..., description="A list of fully qualified class names like 'com.mycompany.app.MyClass'")

    name: str = "get_class_meta"
    description: str = "Get metadata for a class in a namespace."
    args_schema: Type[BaseModel] = ToolInputSchema
    result_as_answer: bool = True

    _code_meta: CodeMeta = PrivateAttr()

    def __init__(self, code_meta: CodeMeta, **kwargs):
        super().__init__(**kwargs)
        self._code_meta = code_meta

    def _run(self, fully_qualified_names: list[str]) -> str:
        return json.dumps(self._code_meta.get_classes_meta(fully_qualified_names), indent=None)

class GetFileSourcesTool(BaseTool):
    class ToolInputSchema(BaseModel):
        file_paths: List[str] = Field(..., description="A list of relative paths to the source code files.")

    name: str = "get_file_sources"
    description: str = "Get the source code for a given relative file paths (not the class names)."
    args_schema: Type[BaseModel] = ToolInputSchema
    result_as_answer: bool = False
    
    _code_meta: CodeMeta = PrivateAttr()
    _root_path: str = PrivateAttr()

    def __init__(self, code_meta: CodeMeta, root_path: str, **kwargs):
        super().__init__(**kwargs)
        self._code_meta = code_meta
        self._root_path = root_path

    def _run(self, file_paths: str) -> str:
        logger.info(f"GetFileSourcesTool -> file_paths: {self._root_path}, file_paths: {len(file_paths)}")
        sources_text = ""
        for path in file_paths:
            full_path = f"{self._root_path}/{path}".replace('//', '/')
            try:
                with open(full_path, 'r') as file:
                    sources_text += f"// File: {path}\n"
                    sources_text += file.read() + "\n\n"
            except Exception as e:
                print(f"Error reading file {full_path}: {e}")
        # DEBUG: Write to file
        # with open('debug-get-file-sources.txt', 'w') as file:
        #    file.write(sources_text)
        return sources_text