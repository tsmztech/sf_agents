"""
True CrewAI implementation for Salesforce requirement analysis.
Replaces the manual orchestration with authentic agentic collaboration.
"""

from crewai import Agent, Task, Crew, Process
from tools.salesforce_tool import SalesforceAnalysisTool
from typing import List, Dict, Any
import os
import json
import logging
import yaml

logger = logging.getLogger(__name__)

class SalesforceImplementationCrew:
    """
    Salesforce Implementation Planning Crew using true CrewAI patterns.
    
    This crew uses autonomous agent collaboration to analyze requirements,
    design schema, create technical architecture, and generate implementation plans.
    """
    
    def __init__(self):
        """Initialize the crew with logging and error handling."""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("Initializing Salesforce Implementation Crew")
        
        # Load configurations
        self.agents_config = self._load_config('config/agents.yaml')
        self.tasks_config = self._load_config('config/tasks.yaml')
        
        # Initialize agents and tasks
        self._agents = self._create_agents()
        self._tasks = self._create_tasks()

    def _load_config(self, config_path: str) -> dict:
        """Load YAML configuration file."""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"Failed to load config {config_path}: {e}")
            return {}

    def _create_agents(self) -> List[Agent]:
        """Create all agents with their configurations."""
        agents = []
        
        # Schema Expert Agent
        schema_expert = Agent(
            role=self.agents_config.get('schema_expert', {}).get('role', 'Salesforce Schema Expert'),
            goal=self.agents_config.get('schema_expert', {}).get('goal', 'Analyze requirements and design schema'),
            backstory=self.agents_config.get('schema_expert', {}).get('backstory', 'Expert in Salesforce schema design'),
            tools=[SalesforceAnalysisTool()],
            verbose=True,
            allow_delegation=False,  # Disabled to prevent delegation tool errors
            max_iter=3,
            memory=True
        )
        agents.append(schema_expert)
        
        # Technical Architect Agent
        technical_architect = Agent(
            role=self.agents_config.get('technical_architect', {}).get('role', 'Salesforce Technical Architect'),
            goal=self.agents_config.get('technical_architect', {}).get('goal', 'Create technical architecture'),
            backstory=self.agents_config.get('technical_architect', {}).get('backstory', 'Expert in technical design'),
            verbose=True,
            allow_delegation=False,  # Disabled to prevent delegation tool errors
            max_iter=3,
            memory=True
        )
        agents.append(technical_architect)
        
        # Dependency Resolver Agent
        dependency_resolver = Agent(
            role=self.agents_config.get('dependency_resolver', {}).get('role', 'Implementation Task Creator'),
            goal=self.agents_config.get('dependency_resolver', {}).get('goal', 'Create implementation plans'),
            backstory=self.agents_config.get('dependency_resolver', {}).get('backstory', 'Expert in project management'),
            verbose=True,
            allow_delegation=False,
            max_iter=2,
            memory=True
        )
        agents.append(dependency_resolver)
        
        return agents

    def _create_tasks(self) -> List[Task]:
        """Create all tasks with their configurations."""
        tasks = []
        
        # Schema Analysis Task
        schema_task = Task(
            description=self.tasks_config.get('schema_analysis_task', {}).get('description', 'Analyze business requirements'),
            expected_output=self.tasks_config.get('schema_analysis_task', {}).get('expected_output', 'Schema analysis JSON'),
            agent=self._agents[0],  # Schema Expert
            output_file='output/schema_analysis.json'
        )
        tasks.append(schema_task)
        
        # Technical Design Task
        technical_task = Task(
            description=self.tasks_config.get('technical_design_task', {}).get('description', 'Create technical design'),
            expected_output=self.tasks_config.get('technical_design_task', {}).get('expected_output', 'Technical design JSON'),
            agent=self._agents[1],  # Technical Architect
            context=[schema_task],
            output_file='output/technical_design.json'
        )
        tasks.append(technical_task)
        
        # Implementation Planning Task
        implementation_task = Task(
            description=self.tasks_config.get('task_creation_task', {}).get('description', 'Create implementation plan'),
            expected_output=self.tasks_config.get('task_creation_task', {}).get('expected_output', 'Implementation plan JSON'),
            agent=self._agents[2],  # Dependency Resolver
            context=[technical_task],
            output_file='output/implementation_plan.json'
        )
        tasks.append(implementation_task)
        
        return tasks

    @property
    def agents(self) -> List[Agent]:
        """Get the list of agents."""
        return self._agents

    @property
    def tasks(self) -> List[Task]:
        """Get the list of tasks."""
        return self._tasks

    def _update_agent_status(self, agent_name: str, status: str = "active", activity: str = ""):
        """Update agent status in Streamlit session state."""
        try:
            import streamlit as st
            import time
            
            if status == "active":
                st.session_state.current_active_agent = agent_name.lower().replace(" ", "_")
                st.session_state.agent_start_time = time.time()
                
                # Add to activities
                if 'agent_activities' not in st.session_state:
                    st.session_state.agent_activities = []
                
                st.session_state.agent_activities.append({
                    'agent': agent_name,
                    'activity': activity,
                    'start_time': time.time(),
                    'status': 'active'
                })
                
            elif status == "completed":
                # Mark current agent as completed
                for activity in st.session_state.agent_activities:
                    if activity.get('agent') == agent_name and activity.get('status') == 'active':
                        activity['status'] = 'completed'
                        activity['duration'] = time.time() - activity['start_time']
                        break
                
                st.session_state.current_active_agent = None
                st.session_state.agent_start_time = None
                
        except Exception as e:
            self.logger.warning(f"Failed to update agent status: {e}")

    def create_crew(self) -> Crew:
        """
        Create the Salesforce Implementation Crew.
        
        Uses sequential process for logical workflow:
        1. Schema Expert analyzes requirements and designs data model
        2. Technical Architect creates comprehensive technical design
        3. Dependency Resolver creates implementation plan
        """
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            memory=True,
            verbose=True,
            max_rpm=10
        )


class SalesforceInteractiveCrew(SalesforceImplementationCrew):
    """
    Enhanced crew with human input for complex scenarios.
    Allows user to review and modify schema recommendations.
    """
    
    def _create_tasks(self) -> List[Task]:
        """Create tasks with human review step."""
        tasks = super()._create_tasks()
        
        # Add human review task after schema analysis
        schema_review_task = Task(
            description="Review the schema analysis with the user for approval and modifications",
            expected_output="User-approved and potentially modified schema design in JSON format",
            agent=self._agents[0],  # Schema Expert
            context=[tasks[0]],  # Schema analysis task
            human_input=True,
            output_file='output/schema_analysis_reviewed.json'
        )
        
        # Update the technical task to depend on the reviewed schema
        tasks[1].context = [schema_review_task]
        
        # Insert the review task
        tasks.insert(1, schema_review_task)
        
        return tasks


class CrewExecutor:
    """
    Utility class for executing crews and handling results.
    Provides a clean interface for Streamlit integration.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def execute_requirement_analysis(
        self, 
        requirement: str, 
        interactive: bool = False,
        additional_context: Dict[str, Any] = None,
        timeout: int = 300  # 5 minute timeout for simplified tasks
    ) -> Dict[str, Any]:
        """
        Execute Salesforce requirement analysis using CrewAI.
        
        Args:
            requirement: Business requirement to analyze
            interactive: Whether to use interactive crew with human review
            additional_context: Additional context for the analysis
            timeout: Maximum execution time in seconds
            
        Returns:
            Dictionary with execution results and outputs
        """
        
        try:
            # Choose crew type based on mode
            if interactive:
                crew_instance = SalesforceInteractiveCrew()
                self.logger.info("Using interactive crew with human review")
            else:
                crew_instance = SalesforceImplementationCrew()
                self.logger.info("Using standard crew")
            
            # Prepare inputs for the crew
            inputs = {
                'requirement': requirement,
                'user_context': additional_context or {},
                'timestamp': self._get_timestamp()
            }
            
            self.logger.info(f"Starting crew execution for requirement: {requirement[:100]}...")
            
            # Create crew with error handling
            try:
                crew = crew_instance.create_crew()
            except Exception as e:
                self.logger.error(f"Failed to create crew: {e}")
                return {
                    'success': False,
                    'error': f"Failed to create crew: {str(e)}",
                    'crew_type': 'interactive' if interactive else 'standard',
                    'requirement': requirement
                }
            
            # Execute with timeout handling
            import signal
            import threading
            
            result = None
            error = None
            
            def execute_crew():
                nonlocal result, error
                try:
                    result = crew.kickoff(inputs=inputs)
                except Exception as e:
                    error = e
            
            # Update status tracking if we have Streamlit context
            def execute_crew_with_status():
                nonlocal result, error
                try:
                    # Update status: Schema Expert starting
                    if hasattr(__builtins__, 'st') or 'streamlit' in globals():
                        try:
                            import streamlit as st
                            import time
                            
                            # Initialize agent tracking
                            if 'agent_activities' not in st.session_state:
                                st.session_state.agent_activities = []
                            
                            # Start with Schema Expert
                            st.session_state.current_active_agent = 'schema'
                            st.session_state.agent_start_time = time.time()
                            
                            # Add initial activity
                            st.session_state.agent_activities.append({
                                'agent': 'Schema Expert',
                                'activity': 'Analyzing Salesforce schema and requirements',
                                'start_time': time.time(),
                                'status': 'active'
                            })
                            
                            # Simulate agent progression based on task completion
                            # This will be updated as tasks complete
                            
                        except Exception as e:
                            self.logger.warning(f"Failed to update Streamlit status: {e}")
                    
                    # Execute the crew
                    result = crew.kickoff(inputs=inputs)
                    
                    # Mark completion
                    if hasattr(__builtins__, 'st') or 'streamlit' in globals():
                        try:
                            import streamlit as st
                            import time
                            
                            # Mark all agents as completed
                            for activity in st.session_state.agent_activities:
                                if activity.get('status') == 'active':
                                    activity['status'] = 'completed'
                                    activity['duration'] = time.time() - activity['start_time']
                            
                            st.session_state.current_active_agent = None
                            st.session_state.agent_start_time = None
                            
                        except Exception as e:
                            self.logger.warning(f"Failed to update completion status: {e}")
                            
                except Exception as e:
                    error = e

            # Run execution in a thread with timeout
            thread = threading.Thread(target=execute_crew_with_status)
            thread.daemon = True
            thread.start()
            thread.join(timeout=timeout)
            
            if thread.is_alive():
                # Execution timed out
                self.logger.warning(f"Crew execution timed out after {timeout} seconds")
                return {
                    'success': False,
                    'error': f"Crew execution timed out after {timeout} seconds. This usually happens with rate limits or large datasets.",
                    'timeout': True,
                    'crew_type': 'interactive' if interactive else 'standard',
                    'requirement': requirement,
                    'suggestion': "Try reducing the complexity of your requirement or wait a few minutes before trying again."
                }
            
            if error:
                # Execution failed
                self.logger.error(f"Crew execution failed: {error}")
                
                # Check for specific error types
                error_str = str(error)
                if "rate limit" in error_str.lower() or "tokens per min" in error_str.lower():
                    return {
                        'success': False,
                        'error': "OpenAI rate limit exceeded. Please wait a few minutes and try again with a simpler requirement.",
                        'error_type': 'rate_limit',
                        'crew_type': 'interactive' if interactive else 'standard',
                        'requirement': requirement,
                        'suggestion': "Try breaking your requirement into smaller parts or wait 5-10 minutes before retrying."
                    }
                elif "token" in error_str.lower() and "limit" in error_str.lower():
                    return {
                        'success': False,
                        'error': "Request too large. Please simplify your requirement.",
                        'error_type': 'token_limit',
                        'crew_type': 'interactive' if interactive else 'standard',
                        'requirement': requirement,
                        'suggestion': "Try using shorter, more specific requirements."
                    }
                else:
                    return {
                        'success': False,
                        'error': str(error),
                        'crew_type': 'interactive' if interactive else 'standard',
                        'requirement': requirement
                    }
            
            if result is None:
                return {
                    'success': False,
                    'error': "Crew execution completed but returned no result",
                    'crew_type': 'interactive' if interactive else 'standard',
                    'requirement': requirement
                }
            
            self.logger.info("Crew execution completed successfully")
            
            # Load and parse output files
            outputs = self._load_output_files()
            
            return {
                'success': True,
                'result': result,
                'outputs': outputs,
                'crew_type': 'interactive' if interactive else 'standard',
                'requirement': requirement
            }
            
        except Exception as e:
            self.logger.error(f"Unexpected error in crew execution: {str(e)}")
            return {
                'success': False,
                'error': f"Unexpected error: {str(e)}",
                'crew_type': 'interactive' if interactive else 'standard',
                'requirement': requirement
            }
    
    def _load_output_files(self) -> Dict[str, Any]:
        """Load JSON output files created by the crew tasks."""
        outputs = {}
        
        output_files = [
            'schema_analysis.json',
            'technical_design.json', 
            'implementation_plan.json',
            'schema_analysis_reviewed.json'  # For interactive mode
        ]
        
        for filename in output_files:
            filepath = f'output/{filename}'
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r') as f:
                        outputs[filename.replace('.json', '')] = json.load(f)
                except json.JSONDecodeError as e:
                    self.logger.warning(f"Could not parse {filename}: {e}")
                    # Try to read as text if JSON parsing fails
                    with open(filepath, 'r') as f:
                        outputs[filename.replace('.json', '')] = f.read()
                except Exception as e:
                    self.logger.warning(f"Could not read {filename}: {e}")
        
        return outputs
    
    def _get_timestamp(self) -> str:
        """Get current timestamp for tracking."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def get_available_outputs(self) -> List[str]:
        """Get list of available output files."""
        output_dir = 'output'
        if not os.path.exists(output_dir):
            return []
        
        return [f for f in os.listdir(output_dir) if f.endswith('.json')]


# Helper functions for easy import and usage
def analyze_salesforce_requirement(
    requirement: str, 
    interactive: bool = False,
    **kwargs
) -> Dict[str, Any]:
    """
    Convenience function for analyzing Salesforce requirements.
    
    Args:
        requirement: Business requirement description
        interactive: Whether to enable human review
        **kwargs: Additional context
        
    Returns:
        Analysis results dictionary
    """
    executor = CrewExecutor()
    return executor.execute_requirement_analysis(
        requirement=requirement,
        interactive=interactive,
        additional_context=kwargs
    )


def is_complex_requirement(requirement: str) -> bool:
    """
    Determine if a requirement is complex enough to warrant interactive review.
    
    Args:
        requirement: Business requirement text
        
    Returns:
        True if requirement seems complex
    """
    complexity_indicators = [
        'integration', 'external system', 'api', 'complex approval',
        'multi-step', 'workflow', 'automation', 'multiple objects',
        'reporting', 'dashboard', 'custom ui', 'advanced security',
        'data migration', 'bulk processing', 'real-time', 'synchronization'
    ]
    
    requirement_lower = requirement.lower()
    matches = sum(1 for indicator in complexity_indicators if indicator in requirement_lower)
    
    # Consider complex if multiple indicators or very long requirement
    return matches >= 2 or len(requirement) > 500


# Export main classes and functions
__all__ = [
    'SalesforceImplementationCrew',
    'SalesforceInteractiveCrew', 
    'CrewExecutor',
    'analyze_salesforce_requirement',
    'is_complex_requirement'
] 