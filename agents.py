import os
from typing import Any, Dict, List
from crewai import LLM, Crew, Agent, Process, Task
import time

# Turn off CrewAI Telemetry
os.environ["OTEL_SDK_DISABLED"] = "true"

# Set LLM logging level
# os.environ["LITELLM_LOG"] = "DEBUG"

VERBOSE = False
MAX_RPM = 120

class AgentSystem:
    def __init__(self, 
                 name: str,
                 llms: Dict[str, Any],
                 agents_data: Dict[str, Any],
                 tasks_data: Dict[str, Any],
                 tools: Dict[str, Any] = {},
                 max_rpm: int = MAX_RPM,
                 verbose: bool = VERBOSE):
        """
        Initializes the AgentSystem with agents and tasks data.

        :param name: The name of the AgentSystem.
        :param llms: A dictionary containing LLMs to be used by the agents.
        :param agents_data: A dictionary containing information about agents.
        :param tasks_data: A dictionary containing information about tasks.
        :param tools: A dictionary containing tools to be used by the agents.
        """

        self.name = name
        self.tools = tools

        self.llms = self._create_llms(llms)
        self.agents = self._create_agents(agents_data)
        self.tasks = self._create_tasks(tasks_data, self.agents)

        self.crew = Crew(
            name=name,
            agents=list(self.agents.values()),
            tasks=self.tasks,
            process=Process.sequential,
            max_rpm=max_rpm,
            verbose=verbose,
            cache=False, # results of tools
            share_crew=False,
        )
        
    def _create_llms(self, llms_data) -> Dict[str, LLM]:
        llms = {}
        for llm_name, llm_info in llms_data.items():
            provider = llm_info.get('provider')
            model = llm_info.get('model')
            llm = LLM(
                model=f'{provider}/{model}',
                temperature=llm_info.get('temperature'),
                max_tokens=llm_info.get('max_tokens'),
                context_window_size=llm_info.get('context_window_size'),
            )
            llms[llm_name] = llm
        
        return llms

    def _create_agents(self, agents_data) -> Dict[str, Agent]:
        agents = {}
        for _, agent_info in agents_data.items():
            agent = Agent(
                role=agent_info.get('role'),
                goal=agent_info.get('goal'),
                max_iter=agent_info.get('max_iterations', 3),
                backstory=agent_info.get('backstory'),
                llm=self.llms[agent_info.get('llm')],
                cache=False,
                respect_context_window=False,
                use_system_prompt=True,
                memory=False,
                verbose=VERBOSE,
                allow_delegation=False
            )
            agents[agent_info.get('role')] = agent  # Store agents by their role
        
        return agents

    def _create_tasks(self, tasks_data, agents: Dict[str, Agent]) -> List[Task]:
        tasks = []
        for task_name, task_info in tasks_data.items():
            agent_role = task_info.get('agent_role')  # Get the agent role for this task
            agent = agents.get(agent_role)  # Look up the agent using the role
            
            if agent is None:
                raise ValueError(f"Agent with role '{agent_role}' not found for task '{task_name}'")

            # Lookup tasks specified in context if present
            context_task_names = task_info.get('context', [])
            context_tasks = [task for task in tasks if task.name in context_task_names]
            tools = []
            for tool_name in task_info.get('tools', []):
                tool = self.tools.get(tool_name)
                if tool is None:
                    raise ValueError(f"Tool with name '{tool_name}' not found for task '{task_name}'")
                tools.append(tool)
                #print(f"Tool {tool_name} added to task {task_name}")

            task = Task(
                name=task_name,
                description=task_info['description'],
                expected_output=task_info['expected_output'],
                agent=agent,
                context=context_tasks,
                tools=tools,
                output_file=f"debug-{task_name}.md"
            )
            # print(f"Task {task_name}") # context: {context_tasks}
            tasks.append(task)
        
        return tasks

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the crew process with the provided inputs.

        :param inputs: A dictionary of inputs to execute the workflow.
        :return: A dictionary containing raw output, usage metrics, and execution time.
        """
        start_time = time.time()
        
        output = self.crew.kickoff(inputs)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        return {
            "raw_output": output.raw,
            "usage_metrics": {
                "total_tokens": output.token_usage.total_tokens,
                "prompt_tokens": output.token_usage.prompt_tokens,
                "completion_tokens": output.token_usage.completion_tokens,
                "successful_requests": output.token_usage.successful_requests,
                "execution_time": execution_time
            }
        }