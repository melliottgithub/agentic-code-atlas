from abc import ABC, abstractmethod
from typing import Optional

from metadata import Namespace

class CodeParser(ABC):
    @abstractmethod
    def parse_source(self, source_code: str, relative_file_path: Optional[str]) -> 'Namespace':
        """Parse the source code and return metadata."""
        pass

    @abstractmethod
    def resolve_references(self, metadata, root_namespace):
        """Resolve references within the parsed metadata."""
        pass