# BIMConverse: Graph RAG for IFC Knowledge Graphs

## Introduction

BIMConverse is a specialized Graph RAG (Retrieval-Augmented Generation) application that enables natural language interaction with IFC (Industry Foundation Classes) knowledge graphs stored in Neo4j. It combines the powerful querying capabilities of graph databases with the natural language understanding of Large Language Models (LLMs) to provide intuitive access to complex building information.

This document outlines the architecture, setup process, and implementation details for integrating BIMConverse with your IFC knowledge graph.

## System Architecture

The BIMConverse system consists of three primary components:

1. **Neo4j Database**: Houses the IFC knowledge graph created from your BIM models
2. **OpenAI API**: Provides the language processing capability for query translation
3. **BIMConverse Web Application**: Serves as the user interface and system orchestrator

![BIMConverse Architecture Diagram](https://neo4j.com/wp-content/uploads/neo4j-llm-architecture-2.png)

## Component Setup

### 1. Neo4j Desktop Configuration

Neo4j Desktop provides a local environment for managing your IFC knowledge graph:

```
Neo4j Connection Parameters:
- Protocol: bolt
- Hostname: localhost
- Port: 7687
- Username: neo4j
- Password: test1234
```

Key steps:
- Ensure your IFC knowledge graph is successfully loaded (306 nodes, 2328 relationships)
- Verify the database is running and accessible
- Test connectivity with a simple Cypher query: `MATCH (n) RETURN count(n)`

### 2. OpenAI API Integration

To enable natural language processing capabilities:

```
OpenAI Configuration:
- API Service: OpenAI
- Model: gpt-4o (recommended for best results)
- API Key: Your-OpenAI-Key
```

Important considerations:
- Store API keys securely using environment variables
- Monitor token usage to manage costs
- Consider rate limiting for production environments

### 3. BIMConverse Web Application

BIMConverse is built using modern web technologies:

```
Technology Stack:
- Framework: Next.js + React
- Styling: Tailwind CSS
- Language: TypeScript
- Database Connectivity: Neo4j JavaScript driver
```

## Development Environment Setup

To run BIMConverse locally:

1. Clone the repository (based on Neo4j's NeoConverse):
   ```bash
   git clone https://github.com/your-repo/bimconverse.git
   cd bimconverse
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Configure environment variables:
   ```
   # .env.local
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=test1234
   OPENAI_API_KEY=your-api-key
   ```

4. Launch the development server:
   ```bash
   npm run dev
   ```

5. Access the application at `http://localhost:3000`

Visual Studio Code is recommended for development, as it provides real-time feedback and integrated debugging tools.

## Query Flow Implementation

The BIMConverse query processing flow consists of several key steps:

### 1. User Configuration

Before querying, users must configure:

- Neo4j connection parameters
- OpenAI API details
- Graph schema information
- Few-shot examples for training the model

The schema information is particularly important, as it guides the LLM in generating accurate Cypher queries:

```javascript
const graphSchema = `
# Node Labels
:Project, :Building, :Storey, :Space, :Element, :Wall, :Window, :Door, :Material

# Relationship Types
:CONTAINS, :CONNECTED_TO, :ADJACENT, :IS_MADE_OF, :HOSTED_BY

# Key Properties
Project: {Name, GlobalId}
Building: {Name, GlobalId, BuildingType}
Element: {Name, GlobalId, IFCType}
Space: {Name, GlobalId, Area, Function}
Material: {Name, Category, Density}
`;
```

### 2. Query Generation

When a user submits a natural language question, it's processed through several transformations:

```javascript
// 1. Build enhanced prompt with schema and examples
function Cypher_Generation_Prompt(userQuestion, graphSchema, fewShotExamples) {
  return `
You are an expert in Neo4j and Cypher query language.
Generate a Cypher query to answer the following question about a building model.

GRAPH SCHEMA:
${graphSchema}

EXAMPLES:
${fewShotExamples}

USER QUESTION:
${userQuestion}

CYPHER QUERY:
`;
}

// 2. Clean generated Cypher for execution
function cypherCleaning(rawCypher) {
  // Remove backticks, fix common syntax errors
  let cleanedCypher = rawCypher.replace(/```cypher|```/g, '').trim();
  // Additional cleaning logic
  return cleanedCypher;
}
```

### 3. Database Interaction

The cleaned Cypher query is executed against the Neo4j database:

```javascript
async function executeQuery(cypher, params = {}) {
  const session = driver.session();
  try {
    const result = await session.run(cypher, params);
    return result.records.map(record => {
      return record.keys.reduce((obj, key) => {
        obj[key] = record.get(key);
        return obj;
      }, {});
    });
  } finally {
    await session.close();
  }
}
```

### 4. Result Processing

Database results are post-processed to enhance readability:

```javascript
function HUMAN_READABLE_MESSAGE_PROMPT(results, userQuestion) {
  return `
Convert the following JSON results into a natural language response.
Results: ${JSON.stringify(results, null, 2)}

The response should:
1. Directly answer the question: "${userQuestion}"
2. Use clear, non-technical language
3. Group similar items where appropriate
4. Include relevant quantities and measurements
5. Format lists and tables neatly if needed
`;
}
```

### 5. Conversation History

BIMConverse maintains conversation history to enable context-aware interactions:

```javascript
function generatePromptWithHistory(newQuestion, history) {
  return `
Previous conversation:
${history.map(exchange => `User: ${exchange.question}\nAssistant: ${exchange.answer}`).join('\n\n')}

New question: ${newQuestion}
`;
}
```

## Example Queries for IFC Knowledge Graphs

BIMConverse can handle a variety of building-related queries, including:

### 1. Spatial Queries

```
User: "What elements are contained in the Living Room space?"

Generated Cypher:
MATCH (s:Space)-[:CONTAINS]->(e:Element)
WHERE s.Name = 'Living Room'
RETURN e.Name as ElementName, e.IFCType as ElementType
```

### 2. Material Information

```
User: "What materials are used in the external walls?"

Generated Cypher:
MATCH (w:Wall)-[:IS_MADE_OF]->(m:Material)
WHERE w.IsExternal = true
RETURN w.Name as WallName, m.Name as MaterialName, m.Category as MaterialType
```

### 3. Building Systems Analysis

```
User: "Show me all doors that provide access between the kitchen and dining room"

Generated Cypher:
MATCH (s1:Space)-[:CONNECTED_TO]->(d:Door)-[:CONNECTED_TO]->(s2:Space)
WHERE (s1.Name = 'Kitchen' AND s2.Name = 'Dining Room')
   OR (s1.Name = 'Dining Room' AND s2.Name = 'Kitchen')
RETURN d.Name as DoorName, d.GlobalId as DoorID
```

### 4. Path Finding

```
User: "What is the shortest path from the main entrance to the master bedroom?"

Generated Cypher:
MATCH path = shortestPath(
  (e:Space {Function: 'Entrance'})-[:CONNECTED_TO*]-(b:Space {Function: 'Bedroom', Name: 'Master Bedroom'})
)
UNWIND nodes(path) as space
RETURN space.Name as SpaceName, space.Function as SpaceFunction
```

## Customization Guide

BIMConverse can be tailored to specific needs through:

### UI Customization

The appearance of BIMConverse is customizable via:
- Tailwind CSS classes in component files
- Global styles in `globals.css`
- Component structure modifications

Example CSS customization:
```css
/* Customize chat interface */
.chat-container {
  @apply bg-slate-50 rounded-lg shadow-md p-4;
}

.user-message {
  @apply bg-blue-100 rounded-lg p-3 my-2 max-w-[80%] ml-auto;
}

.assistant-message {
  @apply bg-gray-100 rounded-lg p-3 my-2 max-w-[80%];
}
```

### Query Enhancement

To improve query accuracy:
1. Add domain-specific few-shot examples
2. Expand the schema with additional property details
3. Include common query patterns with explanations

### Performance Optimization

For larger graphs:
1. Add appropriate Neo4j indexes:
   ```cypher
   CREATE INDEX element_global_id FOR (e:Element) ON (e.GlobalId);
   CREATE INDEX space_name FOR (s:Space) ON (s.Name);
   ```

2. Implement result pagination:
   ```javascript
   function paginateResults(results, page = 1, pageSize = 20) {
     const start = (page - 1) * pageSize;
     return results.slice(start, start + pageSize);
   }
   ```

## Deployment Options

### Local Deployment

The current setup runs locally on a personal computer:
- Development server via `npm run dev`
- Access through web browser at localhost:3000
- Real-time updates for development

### Production Deployment

For production environments, consider:
- Serverless deployment on Vercel or Netlify
- Containerization using Docker
- Environment-specific configuration
- Authentication and security measures

## Troubleshooting

Common issues and solutions:

1. **Connection Errors**:
   - Verify Neo4j database is running
   - Check connection credentials
   - Ensure correct bolt protocol configuration

2. **Query Generation Issues**:
   - Enhance schema information
   - Provide more specific few-shot examples
   - Review and refine LLM prompt structure

3. **Performance Concerns**:
   - Add database indexes
   - Optimize complex Cypher queries
   - Implement caching for frequent queries

## Future Enhancements

Planned improvements for BIMConverse:

1. **3D Visualization Integration**:
   - Embed 3D viewers for selected elements
   - Highlight query results in the model

2. **Advanced Semantic Processing**:
   - Implement embedding-based node properties
   - Enable similarity searches for concepts

3. **Multi-Model Support**:
   - Compare elements across different building models
   - Track changes between versions

4. **Export Capabilities**:
   - Save query results to CSV/Excel
   - Generate reports from conversations

## References

- [Neo4j Graph RAG Documentation](https://neo4j.com/docs/graph-data-science/current/machine-learning/llm-integration/)
- [Neo4j JavaScript Driver](https://neo4j.com/docs/javascript-manual/current/)
- [OpenAI API Documentation](https://platform.openai.com/docs/api-reference)
- [Next.js Documentation](https://nextjs.org/docs)
- [IFC Knowledge Graph Schema](./schema_documentation.md)

---

*This document serves as both a reference implementation guide and a blueprint for extending BIMConverse functionality.*