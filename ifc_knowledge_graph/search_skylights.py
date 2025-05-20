#!/usr/bin/env python3
"""
Search for skylight nodes in the Neo4j database
"""

from neo4j import GraphDatabase
import json

# Load configuration
with open('config.json') as f:
    config = json.load(f)

# Connect to Neo4j
driver = GraphDatabase.driver(
    config['neo4j']['uri'],
    auth=(config['neo4j']['username'], config['neo4j']['password'])
)

# Search for nodes that might be skylights
with driver.session() as session:
    # Search by name or description
    query1 = """
    MATCH (n) 
    WHERE n.name CONTAINS 'skylight' OR n.description CONTAINS 'skylight'
    RETURN n.name AS name, n.description AS description, labels(n) AS type
    """
    
    print("\n=== Searching for 'skylight' in name/description ===")
    result1 = session.run(query1)
    for record in result1:
        print(f"Found: {record}")
    
    # Look for any nodes with roof-related elements
    query2 = """
    MATCH (n) 
    WHERE n.name CONTAINS 'roof' OR n.description CONTAINS 'roof'
    RETURN n.name AS name, n.description AS description, labels(n) AS type
    """
    
    print("\n=== Searching for 'roof' in name/description ===")
    result2 = session.run(query2)
    for record in result2:
        print(f"Found: {record}")
    
    # Look for any opening elements that might be skylights
    query3 = """
    MATCH (n:Window) 
    RETURN n.name AS name, n.description AS description, n.IFCType AS ifcType, labels(n) AS type
    LIMIT 10
    """
    
    print("\n=== Checking Window elements ===")
    result3 = session.run(query3)
    for record in result3:
        print(f"Window: {record}")
    
    # Search for properties that might indicate skylights
    query4 = """
    MATCH (n)-[:HAS_PROPERTY_SET]->(ps)
    WHERE ps.name CONTAINS 'skylight' OR ps.name CONTAINS 'roof'
    RETURN n.name AS element_name, labels(n) AS element_type, ps.name AS property_set
    """
    
    print("\n=== Searching for skylight/roof in property sets ===")
    result4 = session.run(query4)
    for record in result4:
        print(f"Property Set: {record}")
    
    # Look at relationship patterns that might indicate skylights
    query5 = """
    MATCH path = (a)-[:CONTAINS]->(b)
    WHERE a.name CONTAINS 'roof' OR b.name CONTAINS 'opening'
    RETURN a.name AS container_name, labels(a) AS container_type, 
           b.name AS element_name, labels(b) AS element_type
    LIMIT 10
    """
    
    print("\n=== Checking for roof-opening relationships ===")
    result5 = session.run(query5)
    for record in result5:
        print(f"Relationship: {record}")

# Close the driver
driver.close()

print("\nDone searching for skylights")
