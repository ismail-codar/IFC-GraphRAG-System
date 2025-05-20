from neo4j import GraphDatabase

# Connect to the Neo4j database
driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'test1234'))

# Query to get relationship types and counts
with driver.session() as session:
    print("\nRelationship Types and Counts:\n")
    
    # Get counts by relationship type
    result = session.run('''
        MATCH ()-[r]->() 
        RETURN type(r) AS RelationType, count(r) AS Count 
        ORDER BY Count DESC
    ''')
    
    for record in result:
        print(f"{record['RelationType']}: {record['Count']}")
    
    # Get total node count
    result = session.run('''
        MATCH (n) 
        RETURN count(n) AS NodeCount
    ''')
    node_count = result.single()["NodeCount"]
    print(f"\nTotal Nodes: {node_count}")
    
    # Get total relationship count
    result = session.run('''
        MATCH ()-[r]->() 
        RETURN count(r) AS RelCount
    ''')
    rel_count = result.single()["RelCount"]
    print(f"Total Relationships: {rel_count}")
    
    # Get node counts by label
    print("\nNode Counts by Label:")
    result = session.run('''
        CALL db.labels() YIELD label
        CALL apoc.cypher.run("MATCH (n:" + label + ") RETURN count(n) AS count", {}) YIELD value
        RETURN label, value.count AS count
        ORDER BY count DESC
    ''')
    
    try:
        for record in result:
            print(f"{record['label']}: {record['count']}")
    except Exception as e:
        print(f"Error with node label query: {e}")
        
        # Try a simpler approach without APOC
        print("\nTrying alternative node label count:")
        labels_result = session.run('CALL db.labels() YIELD label RETURN label')
        labels = [record['label'] for record in labels_result]
        
        for label in labels:
            count_result = session.run(f'MATCH (n:{label}) RETURN count(n) AS count')
            count = count_result.single()['count']
            print(f"{label}: {count}")
    
    # Check if topological analyzer was run by looking for topologic entities
    print("\nChecking for topological entities:")
    result = session.run('''
        MATCH (n)
        WHERE n.topologicEntity IS NOT NULL
        RETURN count(n) AS TopologicCount
    ''')
    topologic_count = result.single()["TopologicCount"]
    print(f"Nodes with topologic attributes: {topologic_count}")
    
    # Check for missing relationship types that should be present
    print("\nMissing relationship types that should exist:")
    expected_rel_types = [
        "CONTAINS", "DEFINES", "HAS_PROPERTY_SET", "HAS_PROPERTY", 
        "IS_MADE_OF", "CONNECTED_TO", "BOUNDED_BY", "ADJACENT",
        "CONTAINS_TOPOLOGICALLY", "BOUNDS_SPACE"
    ]
    
    existing_rel_types = session.run('CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType')
    existing_types = [record['relationshipType'] for record in existing_rel_types]
    
    for rel_type in expected_rel_types:
        if rel_type not in existing_types:
            print(f"Missing: {rel_type}")

# Close the driver connection
driver.close() 