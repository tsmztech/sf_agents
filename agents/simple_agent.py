"""
Simple agent implementation to replace CrewAI for better deployment compatibility.
Uses OpenAI directly without heavyweight dependencies.
"""

import openai
from typing import Dict, Any, Optional
import os
import time

class SimpleAgent:
    """A simple agent that uses OpenAI directly."""
    
    def __init__(self, role: str, goal: str, backstory: str, model: str = "gpt-4"):
        self.role = role
        self.goal = goal
        self.backstory = backstory
        self.model = model
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    def execute_task(self, task_description: str, context: str = "") -> str:
        """Execute a task using OpenAI."""
        
        system_prompt = f"""
        You are a {self.role}.
        
        Goal: {self.goal}
        
        Background: {self.backstory}
        
        Execute the following task with expertise and attention to detail.
        """
        
        user_prompt = f"""
        Context: {context}
        
        Task: {task_description}
        
        Please provide a detailed response based on your role and expertise.
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Error executing task: {str(e)}"

class SimpleTask:
    """A simple task implementation."""
    
    def __init__(self, description: str, expected_output: str, agent: SimpleAgent):
        self.description = description
        self.expected_output = expected_output
        self.agent = agent
    
    def execute(self, context: str = "") -> str:
        """Execute the task."""
        return self.agent.execute_task(self.description, context)

class SimpleCrew:
    """A simple crew implementation."""
    
    def __init__(self, agents: list, tasks: list):
        self.agents = agents
        self.tasks = tasks
    
    def kickoff(self) -> str:
        """Execute all tasks and return the final result."""
        results = []
        context = ""
        
        for task in self.tasks:
            result = task.execute(context)
            results.append(result)
            context += f"\n\nPrevious task result: {result}"
        
        return results[-1] if results else ""

# Compatibility aliases for existing code
Agent = SimpleAgent
Task = SimpleTask  
Crew = SimpleCrew 