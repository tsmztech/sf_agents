from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="salesforce-ai-agent-system",
    version="1.0.0",
    author="Tapas Mukherjee",
    author_email="",
    description="An intelligent agentic AI system for Salesforce implementation planning",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/tapasmukherjee/sf_agents",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Office/Business :: Financial :: Investment",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.8",
    install_requires=[
        "crewai==0.150.0",
        "streamlit==1.37.0",
        "python-dotenv==1.0.0",
        "pydantic==2.7.4",
        "chromadb==1.0.15",
        "langchain-openai==0.2.10",
        "langchain-community==0.3.9",
        "typing-extensions==4.12.0",
        "requests>=2.31.0",
        "simple-salesforce>=1.12.0",
    ],
    keywords="salesforce ai agent crewai streamlit implementation planning",
    project_urls={
        "Bug Reports": "https://github.com/tapasmukherjee/sf_agents/issues",
        "Source": "https://github.com/tapasmukherjee/sf_agents",
        "Documentation": "https://github.com/tapasmukherjee/sf_agents/blob/main/README.md",
    },
) 