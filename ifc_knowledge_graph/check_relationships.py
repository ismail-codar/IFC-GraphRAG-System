#!/usr/bin/env python3
"""
Check relationships in the Neo4j database.
"""

from src.ifc_to_graph.database.neo4j_connector import Neo4jConnector

def main():
    try:
        # Connect to Neo4j
        conn = Neo4jConnector('neo4j://localhost:7687', 'neo4j', 'test1234')
        
        # Check Project->Site relationships
        print('Project->Site relationships:')
        result = conn.run_query('MATCH (p:IfcProject)-[r]->(s:IfcSite) RETURN type(r) as rel_type, count(*) as count')
        for r in result:
            print(f'{r["rel_type"]}: {r["count"]}')
        
        # Check Site->Building relationships
        print('\nSite->Building relationships:')
        result = conn.run_query('MATCH (s:IfcSite)-[r]->(b:IfcBuilding) RETURN type(r) as rel_type, count(*) as count')
        for r in result:
            print(f'{r["rel_type"]}: {r["count"]}')
        
        # Check Building->Storey relationships
        print('\nBuilding->Storey relationships:')
        result = conn.run_query('MATCH (b:IfcBuilding)-[r]->(s:IfcBuildingStorey) RETURN type(r) as rel_type, count(*) as count')
        for r in result:
            print(f'{r["rel_type"]}: {r["count"]}')
        
        # Create missing relationships
        print('\nCreating missing spatial hierarchy relationships:')
        
        # Project->Site
        print('Creating Project->Site relationship...')
        result = conn.run_query('''
        MATCH (p:IfcProject {GlobalId: "1xS3BCk291UvhgP2a6eflL"})
        MATCH (s:IfcSite {GlobalId: "1xS3BCk291UvhgP2a6eflN"})
        MERGE (p)-[r:CONTAINS]->(s)
        RETURN count(r) as created
        ''')
        created = result[0]["created"] if result else 0
        print(f"Project->Site relationship created: {created}")
        
        # Site->Building
        print('Creating Site->Building relationship...')
        result = conn.run_query('''
        MATCH (s:IfcSite {GlobalId: "1xS3BCk291UvhgP2a6eflN"})
        MATCH (b:IfcBuilding {GlobalId: "1xS3BCk291UvhgP2a6eflK"})
        MERGE (s)-[r:CONTAINS]->(b)
        RETURN count(r) as created
        ''')
        created = result[0]["created"] if result else 0
        print(f"Site->Building relationship created: {created}")
        
        # Building->Storeys
        print('Creating Building->Storey relationships...')
        storey_ids = [
            "1xS3BCk291UvhgP2dvNMKI",
            "1xS3BCk291UvhgP2dvNMQJ",
            "1xS3BCk291UvhgP2dvNsgp",
            "1xS3BCk291UvhgP2dvNtSE"
        ]
        
        total_created = 0
        for storey_id in storey_ids:
            result = conn.run_query(f'''
            MATCH (b:IfcBuilding {{GlobalId: "1xS3BCk291UvhgP2a6eflK"}})
            MATCH (st:IfcBuildingStorey {{GlobalId: "{storey_id}"}})
            MERGE (b)-[r:CONTAINS]->(st)
            RETURN count(r) as created
            ''')
            created = result[0]["created"] if result else 0
            total_created += created
            print(f"Building->Storey ({storey_id}) relationship created: {created}")
        
        print(f"Total Building->Storey relationships created: {total_created}")
        
        # Verify relationships again
        print('\nVerifying relationships after creation:')
        
        # Project->Site
        result = conn.run_query('MATCH path=(p:IfcProject)-[:CONTAINS]->(s:IfcSite) RETURN count(path) as count')
        count = result[0]["count"] if result else 0
        print(f"Project->Site path count: {count}")
        
        # Site->Building
        result = conn.run_query('MATCH path=(s:IfcSite)-[:CONTAINS]->(b:IfcBuilding) RETURN count(path) as count')
        count = result[0]["count"] if result else 0
        print(f"Site->Building path count: {count}")
        
        # Building->Storey
        result = conn.run_query('MATCH path=(b:IfcBuilding)-[:CONTAINS]->(s:IfcBuildingStorey) RETURN count(path) as count')
        count = result[0]["count"] if result else 0
        print(f"Building->Storey path count: {count}")
        
        # Complete hierarchy
        result = conn.run_query('''
        MATCH path=(p:IfcProject)-[:CONTAINS]->(s:IfcSite)-[:CONTAINS]->(b:IfcBuilding)-[:CONTAINS]->(st:IfcBuildingStorey)
        RETURN count(path) as count
        ''')
        count = result[0]["count"] if result else 0
        print(f"Complete hierarchy path count: {count}")
        
        # Close connection
        conn.close()
    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main() 