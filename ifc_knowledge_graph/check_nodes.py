#!/usr/bin/env python3
"""
Check node labels in the Neo4j database.
"""

from src.ifc_to_graph.database.neo4j_connector import Neo4jConnector

def check_database():
    conn = Neo4jConnector('neo4j://localhost:7687', 'neo4j', 'test1234')
    
    # Check node types
    node_types = conn.run_query('MATCH (n) RETURN DISTINCT labels(n) as labels, count(*) as count ORDER BY count DESC')
    print("\nNode types in the database:")
    for r in node_types:
        print(f"{r['labels']}: {r['count']} nodes")
    
    # Check spatial structure nodes specifically
    spatial_nodes = conn.run_query('''
        MATCH (n) 
        WHERE any(label IN labels(n) WHERE label IN ["IfcProject", "IfcSite", "IfcBuilding", "IfcBuildingStorey", "IfcSpace"])
        RETURN labels(n) as labels, n.GlobalId as id, n.Name as name
    ''')
    
    print("\nSpatial structure nodes:")
    for node in spatial_nodes:
        print(f"{node['labels']}: ID={node['id']}, Name={node['name']}")
    
    # Check CONTAINS relationships
    contains_rels = conn.run_query('''
        MATCH (a)-[r:CONTAINS]->(b)
        RETURN labels(a) as source_type, a.GlobalId as source_id,
               labels(b) as target_type, b.GlobalId as target_id,
               count(*) as count
    ''')
    
    print("\nCONTAINS relationships:")
    for rel in contains_rels:
        print(f"{rel['source_type']} ({rel['source_id']}) CONTAINS {rel['target_type']} ({rel['target_id']})")
    
    # Check space properties
    space_props = conn.run_query('''
        MATCH (s:IfcSpace)
        RETURN s.GlobalId as id, s.Name as name, properties(s) as props
    ''')
    
    print("\nSpace node properties:")
    for space in space_props:
        print(f"Space {space['id']} ({space['name']}): {space['props']}")
    
    # Close connection
    conn.close()

if __name__ == "__main__":
    check_database() 