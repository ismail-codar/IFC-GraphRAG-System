#!/usr/bin/env python3
"""
Check specific IFC element types in the Neo4j database.
"""

from src.ifc_to_graph.database.neo4j_connector import Neo4jConnector

def main():
    # Connect to Neo4j
    conn = Neo4jConnector('neo4j://localhost:7687', 'neo4j', 'test1234')
    
    # Query nodes with IFCType property
    query = """
    MATCH (n) 
    WHERE n.IFCType IS NOT NULL
    RETURN n.IFCType as element_type, count(*) as count 
    ORDER BY count DESC
    """
    
    result = conn.run_query(query)
    
    print("IFC Element Types in the database:")
    print("---------------------------------")
    total = 0
    for record in result:
        element_type = record["element_type"]
        count = record["count"]
        total += count
        print(f"{element_type}: {count}")
    
    print("---------------------------------")
    print(f"Total nodes with IFCType: {total}")
    
    # Check if specific building element labels exist
    query_labels = """
    MATCH (n)
    WHERE any(label IN labels(n) WHERE label IN ['Wall', 'Door', 'Window', 'Slab', 'Column', 'Beam', 'Space', 'Storey', 'Building', 'Site'])
    RETURN labels(n) as node_labels, count(*) as count
    ORDER BY count DESC
    """
    
    result = conn.run_query(query_labels)
    
    print("\nSpecific Building Element Labels:")
    print("---------------------------------")
    total_specific = 0
    for record in result:
        labels = record["node_labels"]
        count = record["count"]
        total_specific += count
        print(f"{labels}: {count}")
    
    print("---------------------------------")
    print(f"Total nodes with specific building element labels: {total_specific}")
    
    # Query any element that has a GlobalId but is not labelled only as 'IfcElement'
    query_untyped = """
    MATCH (n)
    WHERE n.GlobalId IS NOT NULL AND NOT (labels(n) = ['IfcElement'])
    RETURN labels(n) as node_labels, count(*) as count
    ORDER BY count DESC
    LIMIT 10
    """
    
    result = conn.run_query(query_untyped)
    
    print("\nElements with GlobalId (excluding generic IfcElement):")
    print("---------------------------------")
    for record in result:
        labels = record["node_labels"]
        count = record["count"]
        print(f"{labels}: {count}")
    
    # Close connection
    conn.close()

if __name__ == "__main__":
    main() 