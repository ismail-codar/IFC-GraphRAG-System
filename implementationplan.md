# Implementation Plan: IFC to Neo4j Knowledge Graph

This document outlines the implementation plan for converting IFC models into a Neo4j knowledge graph, following the design concept in `concept.md`. The plan is organized into phases with specific task checklists.

## Phase 0: Environment Setup

This initial phase focuses on creating the proper development environment with Python 3.12 (required for IfcOpenShell compatibility) and installing all necessary dependencies.

### Tasks:

- [x] **Python 3.12 Installation**
  - [x] Download Python 3.12 from [python.org](https://www.python.org/downloads/)
  - [x] Install Python 3.12 with PATH configuration
  - [x] Verify installation: `python --version`

- [x] **Virtual Environment Setup**
  - [x] Create project directory: `mkdir ifc_knowledge_graph && cd ifc_knowledge_graph`
  - [x] Create virtual environment: `python -m venv venv`
  - [x] Activate virtual environment:
    - Windows: `venv\Scripts\activate`
    - Linux/Mac: `source venv/bin/activate`
  - [x] Verify Python version in virtual environment: `python --version`

- [x] **Install Core Dependencies**
  - [x] Upgrade pip: `pip install --upgrade pip`
  - [x] Install IfcOpenShell: `pip install ifcopenshell`
  - [x] Install TopologicPy: `pip install topologic` (or follow specific installation instructions)
  - [x] Install Neo4j driver: `pip install neo4j`
  - [x] Install development tools: `pip install pytest black isort flake8 pre-commit`
  - [x] Create requirements.txt: `pip freeze > requirements.txt`

- [ ] **Neo4j Desktop Setup**
  - [ ] Download and install Neo4j Desktop from [neo4j.com](https://neo4j.com/download/)
  - [ ] Create a new project in Neo4j Desktop (e.g., "IFC_Knowledge_Graph")
  - [ ] Add a local database (e.g., "ifc_db")
  - [ ] Configure database settings (memory, plugins)
  - [ ] Start the database and verify it's running
  - [ ] Note the connection details (Bolt URI, typically `neo4j://localhost:7687`)

- [ ] **Project Structure Setup**
  - [ ] Create base directories:
    ```
    mkdir -p src/ifc_parser src/topology src/mapping src/graph_loader tests docs
    ```
  - [ ] Create `__init__.py` files in each module
  - [ ] Set up logging configuration
  - [ ] Create CLI entry point skeleton
  - [ ] Create connection configuration file for Neo4j Desktop

## Phase 1: Repository Bootstrap

Set up the repository structure and development tools for the project.

### Tasks:

- [ ] **Repository Initialization**
  - [ ] Initialize git repository: `git init`
  - [ ] Create `.gitignore` file with appropriate exclusions
  - [ ] Set up pre-commit hooks for code quality
  - [ ] Create initial README.md with project overview

- [ ] **CI/CD Setup**
  - [ ] Choose CI platform (GitHub Actions, GitLab CI, etc.)
  - [ ] Create CI configuration for testing and linting
  - [ ] Set up automated test execution
  - [ ] Configure code quality checks

- [ ] **Project Configuration**
  - [ ] Create pyproject.toml or setup.py for package configuration
  - [ ] Configure pytest for testing
  - [ ] Set up logging configuration
  - [ ] Define environment variable templates
  - [ ] Create secure configuration for Neo4j Desktop credentials

## Phase 2: IFC Extraction

Implement the IFC parsing and extraction layer using IfcOpenShell.

### Tasks:

- [ ] **IFC Parser Implementation**
  - [ ] Create `ifc_parser/reader.py` for basic file loading
  - [ ] Implement entity extraction (focusing on Wall, Door, Window, Room, Material)
  - [ ] Extract relevant attributes for each entity type
  - [ ] Extract geometry references

- [ ] **Entity Transformation**
  - [ ] Create data models for extracted entities
  - [ ] Implement property set extraction
  - [ ] Handle units and coordinate systems
  - [ ] Map IFC relationships to internal model

- [ ] **Test IFC Extraction**
  - [ ] Create unit tests for extraction components
  - [ ] Test with sample IFC files
  - [ ] Benchmark extraction performance

## Phase 3: Topology Analysis

Implement the topology analysis using TopologicPy to derive spatial and connectivity relationships.

### Tasks:

- [ ] **Topology Engine Integration**
  - [ ] Create `topology/relationships.py` 
  - [ ] Implement geometry conversion from IfcOpenShell to TopologicPy
  - [ ] Create wrapper for TopologicPy functions

- [ ] **Spatial Relationship Extraction**
  - [ ] Implement containment detection (elements in rooms)
  - [ ] Implement adjacency detection (wall-to-wall, room-to-room)
  - [ ] Implement connectivity detection (doors/windows connecting spaces)

- [ ] **Material Layer Handling**
  - [ ] Implement wall layer ordering algorithm
  - [ ] Determine material orientation (interior/exterior facing)
  - [ ] Connect materials to appropriate elements

- [ ] **Test Topology Functions**
  - [ ] Create unit tests for topology functions
  - [ ] Validate relationship detection with known models
  - [ ] Benchmark topology analysis performance

## Phase 4: Mapping & Buffering

Implement the layer that merges explicit and implicit data and prepares it for graph loading.

### Tasks:

- [ ] **Data Integration**
  - [ ] Create `mapping/mapper.py`
  - [ ] Merge IFC explicit data with topology relationships
  - [ ] Resolve conflicts and duplicates
  - [ ] Validate integrated data model

- [ ] **Graph Model Preparation**
  - [ ] Define Neo4j node and relationship models
  - [ ] Implement property conversion and normalization
  - [ ] Create batch processing logic
  - [ ] Implement data validation before loading

- [ ] **Buffering Strategy**
  - [ ] Implement memory-efficient buffering for large models
  - [ ] Create progress tracking and resumability
  - [ ] Define error handling and recovery strategies

## Phase 5: Neo4j Ingestion

Implement the Neo4j loading functionality using the official Neo4j driver connected to Neo4j Desktop.

### Tasks:

- [ ] **Neo4j Driver Integration**
  - [ ] Create `graph_loader/load.py`