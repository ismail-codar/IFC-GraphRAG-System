# BIMConverse

BIMConverse is a GraphRAG (Retrieval Augmented Generation) system for querying IFC building knowledge graphs using natural language. It allows users to interact with building models stored in Neo4j using conversational language.

## Features

- Natural language querying of building models using Neo4j GraphRAG
- Text2CypherRetriever for dynamic conversion of natural language to Cypher queries
- Conversation context management for follow-up questions
- Integration with Neo4j GraphRAG and OpenAI GPT models
- CLI interface with interactive mode
- Results with generated Cypher queries and graph context
- Multiple output formats (text, JSON, Markdown)
- Statistics display

## Technical Implementation

BIMConverse uses Neo4j GraphRAG's Text2CypherRetriever to convert natural language queries into Cypher queries that are executed against the Neo4j database. This approach offers several advantages:

- No need to create and maintain vector embeddings
- Direct translation from natural language to Cypher queries
- Ability to leverage the full power of graph traversal
- Clear visibility into the query generation process
- Contextual understanding of conversational interactions

The system consists of the following components:

- **core.py**: Implements the BIMConverseRAG class that connects to Neo4j and manages the Text2CypherRetriever
- **cli.py**: Provides a command-line interface for interacting with the system
- **bimconverse.py**: Entry point for the application

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
python cli.py --create-config
```

This will guide you through setting up:
- Neo4j connection details
- OpenAI API key
- Project information
- Conversation context settings

## Usage

### Command Line Interface

To start the interactive CLI:

```bash
python cli.py --config path/to/config.json
```

To run a single query:

```bash
python cli.py --config path/to/config.json --query "What spaces are on the ground floor?"
```

To display database statistics:

```bash
python cli.py --config path/to/config.json --stats
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
--context             Enable conversation context for follow-up questions
```

### Interactive Mode Commands

In interactive mode, you can use the following commands:

- `:help` - Display help message
- `:stats` - Display database statistics
- `:exit` - Exit the program
- `:save [filename]` - Save last query result to file
- `:clear` - Clear the screen
- `:context` - Show conversation context settings
- `:context on|off` - Enable or disable conversation context
- `:context clear` - Clear conversation history
- `:context maxlen [n]` - Set maximum conversation history length

## Example Queries

- "What spaces are on the ground floor?"
- "Show me all doors between the kitchen and dining room"
- "Which walls use concrete as a material?"
- "What is the total area of all bedrooms?"
- "How many windows are in the north-facing walls?"

### Follow-up Queries (with context enabled)

After asking "What spaces are on the ground floor?":
- "How many are there?"
- "Which one has the largest area?"
- "What materials are used in their walls?"

## Integration with IFC Knowledge Graph Pipeline

BIMConverse is designed to work with the existing IFC knowledge graph pipeline. After processing your IFC files and creating a knowledge graph in Neo4j, you can use BIMConverse to query the graph using natural language.

## Testing

A test script is included to verify the functionality of the core implementation:

```bash
python test_core.py
```

This will test:
- Connection to Neo4j
- Text2Cypher query generation and execution
- Conversation context management
- Graph statistics retrieval

## Future Development

- Web interface with Gradio
- Interactive graph visualization
- Multi-model support
- Query templates
- Extended schema support for different IFC versions 