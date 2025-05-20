"""
BIMConverse Prompt Templates

This module contains the prompt templates for the BIMConverse GraphRAG system,
with a focus on advanced reasoning capabilities for building information modeling.
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# Base prompt for text to Cypher generation
SCHEMA_PROMPT = """
You are a specialist in converting natural language questions about buildings into Cypher queries for Neo4j.
The database contains an IFC (Industry Foundation Classes) building model represented as a graph.

Node properties:
Project {GlobalId: STRING, Name: STRING, Description: STRING}
Site {GlobalId: STRING, Name: STRING, Description: STRING}
Building {GlobalId: STRING, Name: STRING, Description: STRING, IFCType: STRING}
Storey {GlobalId: STRING, Name: STRING, Description: STRING, IFCType: STRING}
Space {GlobalId: STRING, Name: STRING, Description: STRING, IFCType: STRING}
Element {GlobalId: STRING, Name: STRING, Description: STRING, IFCType: STRING}
Wall {GlobalId: STRING, Name: STRING, Description: STRING, IFCType: STRING}
Window {GlobalId: STRING, Name: STRING, Description: STRING, IFCType: STRING}
Door {GlobalId: STRING, Name: STRING, Description: STRING, IFCType: STRING}
Slab {GlobalId: STRING, Name: STRING, Description: STRING, IFCType: STRING}
Beam {GlobalId: STRING, Name: STRING, Description: STRING, IFCType: STRING}
Column {GlobalId: STRING, Name: STRING, Description: STRING, IFCType: STRING}
Railing {GlobalId: STRING, Name: STRING, Description: STRING, IFCType: STRING}
Furniture {GlobalId: STRING, Name: STRING, Description: STRING, IFCType: STRING}
Material {Name: STRING, Description: STRING}
PropertySet {Name: STRING}
Property {Name: STRING, Value: STRING}

Relationship properties:
CONTAINS {}
DEFINES {}
HAS_PROPERTY_SET {}
HAS_PROPERTY {}
IS_MADE_OF {}
CONNECTED_TO {}
BOUNDED_BY {}
ADJACENT_TO {}

The relationships:
(:Project)-[:CONTAINS]->(:Site)
(:Site)-[:CONTAINS]->(:Building)
(:Building)-[:CONTAINS]->(:Storey)
(:Storey)-[:CONTAINS]->(:Space)
(:Space)-[:CONTAINS]->(:Element)
(:Space)-[:CONTAINS]->(:Wall)
(:Space)-[:CONTAINS]->(:Door)
(:Space)-[:CONTAINS]->(:Window)
(:Space)-[:CONTAINS]->(:Furniture)
(:Element)-[:HAS_PROPERTY_SET]->(:PropertySet)
(:PropertySet)-[:HAS_PROPERTY]->(:Property)
(:Element)-[:IS_MADE_OF]->(:Material)
(:Wall)-[:IS_MADE_OF]->(:Material)
(:Wall)-[:CONNECTED_TO]->(:Wall)
(:Space)-[:ADJACENT_TO]->(:Space)
(:Wall)-[:BOUNDED_BY]->(:Space)
"""

# Advanced multi-hop reasoning prompt - helps the model break complex questions down
MULTI_HOP_REASONING_PROMPT = """
When answering complex questions about building models, I'll break the question down into multiple steps:

1. IDENTIFY the key entities mentioned in the question (e.g., spaces, elements, materials)
2. DETERMINE the relationships that need to be traversed
3. PLAN the query path through the graph
4. FORMULATE Cypher queries that navigate multiple hops through the graph
5. INTEGRATE the results from multiple steps

For example, if asked "What materials are used in walls adjacent to the kitchen?", I'll:
1. IDENTIFY: "kitchen" (a Space), "walls" (Wall nodes), "materials" (Material nodes)
2. DETERMINE: Need to find walls adjacent to kitchen, then materials of those walls
3. PLAN: Kitchen Space -> BOUNDED_BY -> Walls -> IS_MADE_OF -> Materials
4. FORMULATE: 
   ```
   MATCH (space:Space)-[:BOUNDED_BY]-(wall:Wall)-[:IS_MADE_OF]->(material:Material)
   WHERE space.Name CONTAINS 'Kitchen'
   RETURN material.Name, COUNT(DISTINCT wall) as WallCount
   ```
5. INTEGRATE: Return the materials and their frequencies

Question: {query}
"""

# Step-back prompting strategy - helps create more conceptual understanding 
STEP_BACK_PROMPT = """
Before answering questions about specific building elements, I'll first take a step back to understand:

1. The GENERAL PRINCIPLE or concept involved (spatial relationships, material usage, etc.)
2. The BUILDING HIERARCHY relevant to the question (project, site, building, storey, space)
3. The DOMAIN KNOWLEDGE needed (construction principles, building codes, IFC specifications)

For example, if asked about "Which spaces have the most windows?", I'll first recognize this as:
- A question about QUANTITATIVE DISTRIBUTION of elements across spaces
- Requiring understanding of the SPACE-WINDOW containment relationship
- Needing COUNT aggregation in the graph query

Let me take a step back from the specific question "{query}" and think about:
1. What general building concept does this relate to?
2. Which levels of the building hierarchy are involved?
3. What domain knowledge is needed to interpret the results correctly?
"""

# Spatial reasoning prompt - helps with understanding spatial relationships
SPATIAL_REASONING_PROMPT = """
When analyzing spatial relationships in building models, I'll focus on these key relationship types:

1. CONTAINMENT: Elements within other elements (Building contains Storeys, Storeys contain Spaces)
2. ADJACENCY: Elements sharing boundaries (Spaces adjacent to other Spaces)
3. CONNECTIVITY: Elements physically connected (Walls connected to other Walls)
4. BOUNDARY: Elements defining the boundaries of spaces (Walls bounding Spaces)

For spatial queries like "{query}", I need to consider:
- The SCALE of the analysis (building-wide, floor-specific, space-specific)
- The RELATIONSHIP TYPE most relevant (containment, adjacency, connectivity, boundary)
- The GRAPH TRAVERSAL PATTERN needed to capture this spatial relationship

Relevant Cypher patterns for spatial relationships:
- Containment: (container)-[:CONTAINS]->(contained)
- Adjacency: (space1)-[:ADJACENT_TO]-(space2)
- Connectivity: (element1)-[:CONNECTED_TO]-(element2)
- Boundary: (space)-[:BOUNDED_BY]-(element)
"""

# Parent-child document retrieval for IFC hierarchies
PARENT_CHILD_RETRIEVAL_PROMPT = """
When retrieving information about building elements, it's important to consider their position in the IFC hierarchy.
For the query "{query}", I'll consider both:

1. The SPECIFIC ELEMENT mentioned (the "child" document)
2. The PARENT CONTEXT of that element

This means that when searching for information about elements like windows or doors, I should also retrieve information about:
- The SPACE that contains the element
- The STOREY that contains the space
- The BUILDING that contains the storey

This contextual information provides important metadata like:
- Spatial location and orientation
- Relevant property sets inherited from parent elements
- Functional context of the element

Cypher pattern for retrieving parent context:
```
MATCH (building:Building)-[:CONTAINS]->(storey:Storey)-[:CONTAINS]->(space:Space)-[:CONTAINS]->(element)
WHERE element.Name CONTAINS '{element_name}'
RETURN building.Name, storey.Name, space.Name, element
```
"""

# Hypothetical question generation prompt
HYPOTHETICAL_QUESTION_TEMPLATE = """
Based on the building model schema, here are common types of questions users might ask:

1. INVENTORY QUESTIONS:
   - "How many spaces are on the second floor?"
   - "What types of walls are used in the building?"
   - "How many windows are in the living room?"

2. SPATIAL RELATIONSHIP QUESTIONS:
   - "Which spaces are adjacent to the kitchen?"
   - "What rooms have doors connecting to the hallway?"
   - "Which spaces are directly above the lobby?"

3. MATERIAL QUESTIONS:
   - "What materials are used in the exterior walls?"
   - "Which spaces have concrete floors?"
   - "How much glass is used in the facade?"

4. PROPERTY QUESTIONS:
   - "What is the total area of all residential spaces?"
   - "Which rooms have a ceiling height greater than 3m?"
   - "What is the fire rating of doors in evacuation routes?"

For each building element in the database, I can generate relevant hypothetical questions that would help with retrieval.
"""

# Chain-of-thought prompting for complex building queries
CHAIN_OF_THOUGHT_PROMPT = """
To answer complex building queries, I'll use a chain-of-thought approach with these steps:

1. ANALYZE the query to identify:
   - ENTITIES: What building elements are mentioned (spaces, walls, windows, etc.)?
   - RELATIONSHIPS: What connections between elements must be traversed?
   - CONSTRAINTS: What conditions or filters should be applied?
   - DESIRED OUTPUT: What information is being requested?

2. REASON through a step-by-step process:
   - START with the most specific entity mentioned
   - NAVIGATE through relevant relationships
   - APPLY filters at each step
   - COLLECT the required information

3. FORMULATE a Cypher query that follows this reasoning process

For example, with the query "Find all rooms adjacent to the kitchen that have more than 2 windows":

Step 1: IDENTIFY the kitchen space
```
MATCH (kitchen:Space)
WHERE kitchen.Name CONTAINS 'Kitchen'
```

Step 2: FIND spaces adjacent to the kitchen
```
MATCH (kitchen:Space)-[:ADJACENT_TO]-(adjacent_space:Space)
WHERE kitchen.Name CONTAINS 'Kitchen'
```

Step 3: FIND windows in these adjacent spaces
```
MATCH (kitchen:Space)-[:ADJACENT_TO]-(adjacent_space:Space)<-[:BOUNDED_BY]-(window:Window)
WHERE kitchen.Name CONTAINS 'Kitchen'
```

Step 4: COUNT windows per adjacent space and FILTER those with more than 2
```
MATCH (kitchen:Space)-[:ADJACENT_TO]-(adjacent_space:Space)
WHERE kitchen.Name CONTAINS 'Kitchen'
WITH adjacent_space
MATCH (adjacent_space)<-[:BOUNDED_BY]-(window:Window)
WITH adjacent_space, COUNT(window) as window_count
WHERE window_count > 2
RETURN adjacent_space.Name, window_count
```

Query to analyze: {query}

Let me walk through my reasoning process:
"""

# Enhanced query decomposition prompt to break down multi-part questions
QUERY_DECOMPOSITION_PROMPT = """
Complex building queries often require multiple steps to answer properly. I need to decompose this query into simpler sub-queries.

Original query: "{query}"

I'll break this down into the following steps:

1. 
2. 
3. 

For each step, I need to:
- Identify what information is needed
- Determine which graph patterns will find this information
- Understand how this information contributes to the final answer
- Consider how to pass context between steps

Let me decompose this query step by step:
"""

# Context accumulation prompt for reasoning across multiple query steps
CONTEXT_ACCUMULATION_PROMPT = """
As I work through this multi-hop query, I need to keep track of important context from previous steps.

Original query: "{query}"

Previous context:
{previous_context}

For the next step, I need to:
1. RECALL key findings from previous steps
2. INTEGRATE this context into my current reasoning
3. IDENTIFY what additional information is still needed
4. FORMULATE a query that builds on what I've already learned

Let me incorporate the previous context as I reason through the next step:
"""

# Dict of prompt templates for different reasoning strategies
PROMPT_TEMPLATES = {
    "basic": SCHEMA_PROMPT,
    "multi_hop": MULTI_HOP_REASONING_PROMPT,
    "step_back": STEP_BACK_PROMPT,
    "spatial": SPATIAL_REASONING_PROMPT,
    "parent_child": PARENT_CHILD_RETRIEVAL_PROMPT,
    "hypothetical": HYPOTHETICAL_QUESTION_TEMPLATE,
    "chain_of_thought": CHAIN_OF_THOUGHT_PROMPT,
    "query_decomposition": QUERY_DECOMPOSITION_PROMPT,
    "context_accumulation": CONTEXT_ACCUMULATION_PROMPT
}

def get_prompt_template(strategy: str = "basic") -> str:
    """
    Get the prompt template for a specific strategy.
    
    Args:
        strategy: The reasoning strategy to use
        
    Returns:
        The prompt template as a string
    """
    if strategy not in PROMPT_TEMPLATES:
        logger.warning(f"Unknown strategy: {strategy}, falling back to basic")
        strategy = "basic"
    
    return PROMPT_TEMPLATES[strategy]

def format_prompt(query: str, strategy: str = "basic", **kwargs) -> str:
    """
    Format a prompt for a specific query and strategy.
    
    Args:
        query: The user's query
        strategy: The reasoning strategy to use
        **kwargs: Additional format parameters
        
    Returns:
        The formatted prompt
    """
    template = get_prompt_template(strategy)
    
    # Combine query and any additional kwargs
    format_args = {"query": query, **kwargs}
    
    try:
        # Format the template with the query and any additional parameters
        return template.format(**format_args)
    except KeyError as e:
        logger.error(f"Missing format parameter: {e}")
        # Fall back to basic formatting with just the query
        return template.format(query=query)

def combine_prompts(query: str, strategies: List[str], **kwargs) -> str:
    """
    Combine multiple prompt strategies for a single query.
    
    Args:
        query: The user's query
        strategies: List of strategies to combine
        **kwargs: Additional format parameters
        
    Returns:
        The combined prompt
    """
    combined = SCHEMA_PROMPT + "\n\n"
    
    for strategy in strategies:
        if strategy in PROMPT_TEMPLATES and strategy != "basic":
            template = get_prompt_template(strategy)
            try:
                combined += template.format(query=query, **kwargs) + "\n\n"
            except KeyError as e:
                logger.warning(f"Skipping {strategy} due to missing parameter: {e}")
    
    combined += f"Now, based on the strategies above, answer this question: {query}"
    return combined 