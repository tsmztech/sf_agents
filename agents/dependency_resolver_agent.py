import json
from typing import Dict, Any, List
from datetime import datetime
from agents.simple_agent import Agent, Task, Crew
import openai
import os
from config import Config

class DependencyResolverAgent:
    """
    Dependency Resolver and Task Creator Agent for Salesforce implementations.
    Analyzes technical designs and creates ordered, executable implementation tasks.
    """
    
    def __init__(self):
        # OpenAI is handled by the simple agent implementation
        self._initialize_agent()
    
    def _initialize_agent(self):
        """Initialize the Dependency Resolver agent with task creation capabilities."""
        self.agent = Agent(
            role="Senior Salesforce Implementation Strategist & Dependency Resolver",
            goal="""Analyze technical architectures and create ordered, executable implementation 
                    tasks with proper dependency management. Convert complex technical designs into 
                    clear, actionable user stories and development tasks.""",
            backstory="""You are an expert Salesforce Implementation Strategist with 15+ years of 
                        experience leading complex enterprise Salesforce deployments. You excel at:
                        
                        • Dependency Analysis: Understanding component interdependencies and sequencing
                        • Task Decomposition: Breaking complex features into manageable development tasks
                        • Risk Assessment: Identifying implementation blockers and critical path items
                        • Resource Planning: Estimating effort and identifying skill requirements
                        • Change Management: Planning rollout strategies and user adoption approaches
                        
                        Your expertise includes:
                        - Salesforce deployment methodologies (Agile, Waterfall, DevOps)
                        - Data migration and system integration patterns
                        - Environment management and release strategies
                        - User training and change management
                        - Testing strategies and quality assurance
                        
                        You think systematically about:
                        - What must be built first to enable other components
                        - How to minimize deployment risks and rollback scenarios
                        - User impact and training requirements
                        - Testing dependencies and validation strategies
                        - Performance and scalability considerations during implementation
                        
                        You create clear, actionable tasks that development teams can execute 
                        efficiently with minimal dependencies and maximum value delivery.""",
        )
    
    def create_implementation_tasks(self, technical_design: Dict[str, Any], requirements_context: str = "") -> Dict[str, Any]:
        """Create ordered implementation tasks from technical design."""
        
        # Create task analysis and ordering task
        task_creation_task = Task(
            description=f"""
            Analyze the following technical design and create a comprehensive implementation plan 
            with ordered, executable tasks.
            
            TECHNICAL DESIGN:
            {json.dumps(technical_design, indent=2)}
            
            ORIGINAL REQUIREMENTS CONTEXT:
            {requirements_context}
            
            YOUR TASK:
            Create a detailed implementation plan that includes:
            
            1. **DEPENDENCY ANALYSIS**:
               - Identify all component dependencies
               - Map prerequisite relationships
               - Flag critical path items
               - Identify potential blockers
            
            2. **TASK BREAKDOWN**:
               Create specific, actionable tasks organized by phase:
               
               **Phase 1: Foundation Setup**
               - Environment preparation
               - Security setup (Profiles, Permission Sets)
               - Basic configuration
               
               **Phase 2: Data Model Implementation**
               - Custom Objects creation
               - Field definitions
               - Relationships and lookups
               - Validation rules
               
               **Phase 3: Automation Development**
               - Process flows
               - Apex triggers
               - Apex classes
               - Scheduled jobs
               
               **Phase 4: User Interface Development**
               - Lightning Web Components
               - Page layouts
               - Lightning pages
               - List views and reports
               
               **Phase 5: Integration & Testing**
               - External system connections
               - Data migration
               - User acceptance testing
               - Performance testing
               
               **Phase 6: Deployment & Training**
               - Production deployment
               - User training
               - Go-live support
            
            3. **TASK SPECIFICATIONS**:
               For each task, provide:
               - Task ID and title
               - Detailed description
               - Acceptance criteria
               - Dependencies (prerequisite tasks)
               - Estimated effort (hours/days)
               - Required skills/roles
               - Risk level (Low/Medium/High)
               - Testing requirements
            
            4. **RISK ASSESSMENT**:
               - Critical path analysis
               - Potential blockers and mitigation strategies
               - Rollback plans for each phase
               - Change management considerations
            
            Format as structured JSON for easy parsing and project management tool import.
            """,
            agent=self.agent,
            expected_output="""A comprehensive JSON implementation plan with ordered tasks, 
                              dependencies, effort estimates, and risk assessments."""
        )
        
        # Execute task creation
        crew = Crew(
            agents=[self.agent],
            tasks=[task_creation_task],
            verbose=True
        )
        
        result = crew.kickoff()
        
        # Parse and structure the implementation plan
        return self._parse_implementation_plan(result)
    
    def optimize_task_sequence(self, implementation_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize task sequence for efficiency and risk minimization."""
        
        optimization_task = Task(
            description=f"""
            Review and optimize the following implementation plan for maximum efficiency 
            and minimum risk:
            
            CURRENT PLAN:
            {json.dumps(implementation_plan, indent=2)}
            
            Optimize for:
            1. Parallel execution opportunities
            2. Early value delivery (quick wins)
            3. Risk mitigation and early validation
            4. Resource utilization efficiency
            5. User adoption and change management
            
            Provide optimized sequence with rationale for changes.
            """,
            agent=self.agent,
            expected_output="Optimized implementation plan with improved sequencing"
        )
        
        crew = Crew(
            agents=[self.agent],
            tasks=[optimization_task],
            verbose=True
        )
        
        optimization_result = crew.kickoff()
        
        return {
            "optimization_status": "completed",
            "optimized_plan": str(optimization_result),
            "optimized_at": datetime.now().isoformat()
        }
    
    def create_user_stories(self, implementation_plan: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert implementation tasks into user stories format."""
        
        user_story_task = Task(
            description=f"""
            Convert the following implementation tasks into properly formatted user stories 
            following Agile best practices:
            
            IMPLEMENTATION PLAN:
            {json.dumps(implementation_plan, indent=2)}
            
            Create user stories in the format:
            "As a [user type], I want [functionality] so that [business value]"
            
            Include:
            - Epic grouping
            - Story points estimation
            - Acceptance criteria
            - Definition of done
            - Dependencies between stories
            
            Focus on business value and user outcomes, not just technical tasks.
            """,
            agent=self.agent,
            expected_output="List of user stories with epics, acceptance criteria, and estimates"
        )
        
        crew = Crew(
            agents=[self.agent],
            tasks=[user_story_task],
            verbose=True
        )
        
        result = crew.kickoff()
        
        return self._parse_user_stories(result)
    
    def _parse_implementation_plan(self, raw_result) -> Dict[str, Any]:
        """Parse and structure the implementation plan result."""
        try:
            # Try to extract JSON from the result
            result_str = str(raw_result)
            
            # Find JSON content in the response
            start_idx = result_str.find('{')
            end_idx = result_str.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = result_str[start_idx:end_idx]
                implementation_plan = json.loads(json_str)
            else:
                # If no JSON found, structure the response
                implementation_plan = {
                    "overview": result_str,
                    "phases": [],
                    "dependencies": {},
                    "risk_assessment": {},
                    "timeline": {}
                }
        
        except (json.JSONDecodeError, Exception) as e:
            # Fallback structure
            implementation_plan = {
                "overview": str(raw_result),
                "parsing_note": f"Could not parse as JSON: {str(e)}",
                "phases": [{"name": "Review Required", "tasks": []}],
                "dependencies": {},
                "risk_assessment": {"note": "See overview for risk details"},
                "timeline": {"note": "See overview for timeline details"}
            }
        
        # Add metadata
        implementation_plan["created_at"] = datetime.now().isoformat()
        implementation_plan["created_by"] = "Dependency Resolver Agent"
        implementation_plan["version"] = "1.0"
        implementation_plan["total_tasks"] = self._count_total_tasks(implementation_plan)
        
        return implementation_plan
    
    def _parse_user_stories(self, raw_result) -> List[Dict[str, Any]]:
        """Parse user stories from the result."""
        try:
            result_str = str(raw_result)
            
            # Try to find JSON array
            start_idx = result_str.find('[')
            end_idx = result_str.rfind(']') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = result_str[start_idx:end_idx]
                user_stories = json.loads(json_str)
            else:
                # Fallback: create structured stories from text
                user_stories = [{
                    "id": "US001",
                    "title": "Review User Stories",
                    "description": result_str,
                    "acceptance_criteria": ["Manual review required"],
                    "story_points": 0,
                    "epic": "Planning"
                }]
        
        except (json.JSONDecodeError, Exception):
            user_stories = [{
                "id": "US001",
                "title": "Review User Stories Output",
                "description": str(raw_result),
                "acceptance_criteria": ["Review and parse user stories manually"],
                "story_points": 0,
                "epic": "Planning"
            }]
        
        return user_stories
    
    def _count_total_tasks(self, implementation_plan: Dict[str, Any]) -> int:
        """Count total tasks in the implementation plan."""
        total = 0
        phases = implementation_plan.get("phases", [])
        
        for phase in phases:
            if isinstance(phase, dict) and "tasks" in phase:
                total += len(phase["tasks"])
        
        return total
    
    def generate_gantt_data(self, implementation_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Generate data structure for Gantt chart visualization."""
        
        gantt_task = Task(
            description=f"""
            Generate Gantt chart data from the implementation plan:
            
            IMPLEMENTATION PLAN:
            {json.dumps(implementation_plan, indent=2)}
            
            Create a data structure suitable for Gantt chart visualization including:
            - Task names and IDs
            - Start and end dates
            - Dependencies
            - Critical path
            - Resource assignments
            - Milestones
            
            Assume a standard work week and reasonable effort estimates.
            """,
            agent=self.agent,
            expected_output="Gantt chart data structure with timeline and dependencies"
        )
        
        crew = Crew(
            agents=[self.agent],
            tasks=[gantt_task],
            verbose=True
        )
        
        result = crew.kickoff()
        
        return {
            "gantt_data": str(result),
            "generated_at": datetime.now().isoformat()
        } 