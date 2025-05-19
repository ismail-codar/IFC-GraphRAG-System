# BIMConverse

BIMConverse is a GraphRAG (Retrieval Augmented Generation) system for querying IFC building knowledge graphs using natural language. It allows users to interact with building models stored in Neo4j using conversational language.

## Features

- Natural language querying of building models
- Integration with Neo4j GraphRAG
- OpenAI embeddings and LLM for high-quality responses
- CLI interface with interactive mode
- Results with generated Cypher queries and graph context
- Multiple output formats (text, JSON, Markdown)
- Statistics display

## Installation

1. Install the required packages:

```bash
pip install -r requirements.txt
```

2. Set up your Neo4j database with an IFC knowledge graph
3. Configure your OpenAI API key

## Configuration

Create a configuration file using the CLI wizard:

```bash
python bimconverse.py cli --create-config
```

This will guide you through setting up:
- Neo4j connection details
- OpenAI API key
- Project information

## Usage

### Command Line Interface

To start the interactive CLI:

```bash
python bimconverse.py cli --config path/to/config.json
```

To run a single query:

```bash
python bimconverse.py cli --config path/to/config.json --query "What spaces are on the ground floor?"
```

To display database statistics:

```bash
python bimconverse.py cli --config path/to/config.json --stats
```

### CLI Options

```
--config, -c          Path to configuration file
--create-config       Create a new configuration file
--query, -q           Execute a single query and exit
--stats               Display database statistics and exit
--no-sources          Don't include source information in query results
--output, -o          Output format (text, json, markdown)
--save                Save query results to file
--verbose, -v         Enable verbose output
```

### Interactive Mode Commands

In interactive mode, you can use the following commands:

- `:help` - Display help message
- `:stats` - Display database statistics
- `:exit` - Exit the program
- `:save [filename]` - Save last query result to file
- `:clear` - Clear the screen

## Example Queries

- "What spaces are on the ground floor?"
- "Show me all doors between the kitchen and dining room"
- "Which walls use concrete as a material?"
- "What is the total area of all bedrooms?"
- "How many windows are in the north-facing walls?"

## Integration with IFC Knowledge Graph Pipeline

BIMConverse is designed to work with the existing IFC knowledge graph pipeline. After processing your IFC files and creating a knowledge graph in Neo4j, you can use BIMConverse to query the graph using natural language.

## Future Development

- Web interface with Gradio
- Interactive graph visualization
- Multi-model support
- Conversation history management
- Query templates 