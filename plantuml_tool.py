import json
from typing import Optional, Type
from pydantic import BaseModel, Field, PrivateAttr
from crewai.tools import BaseTool

from plantuml import PlantUML

_DEFAULT_PLANTUML_SERVER = "http://www.plantuml.com/plantuml/img/"

def createPlantUMLProcessor(url: Optional[str]):
    return PlantUML(url=url) if url else PlantUML(url=_DEFAULT_PLANTUML_SERVER)

class PlantUMLExportTool(BaseTool):
    class ToolInputSchema(BaseModel):
        plantuml_text: str = Field(..., description="The PlantUML text to be exported to PNG")

    name: str = "plantuml_export"
    description: str = "Export PlantUML diagram to PNG"
    args_schema: Type[BaseModel] = ToolInputSchema
    result_as_answer: bool = False

    _plant_uml: PlantUML = PrivateAttr()
    _output_file: str = PrivateAttr()

    def __init__(self, plant_uml: PlantUML, output_file: str, **kwargs):
        super().__init__(**kwargs)
        self._plant_uml = plant_uml
        self._output_file = output_file

    def _run(self, plantuml_text: str) -> str:
        # print(f"PlantUMLExportTool -> Exporting PlantUML diagram to PNG")
        try:
            image = self._plant_uml.processes(plantuml_text)
            with open(self._output_file, "wb") as file:
                file.write(image)
            return json.dumps({"success": True, "output_file": self._output_file}, indent=None)
        except Exception as e:
            error_message = e.message if hasattr(e, 'message') else 'Unknown error (probably a syntax error in the PlantUML text)'
            print(f"Error exporting PlantUML diagram to PNG: {error_message}")
            return json.dumps({"success": False, "message": error_message}, indent=None)
