"""
Test Neo4j Connection and Setup Constraints/Indexes

This script:
1. Tests connection to Neo4j database
2. Creates constraints and indexes for IFC data model
"""

from neo4j import GraphDatabase
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

# Connection parameters
URI = "neo4j://localhost:7687"  # This connects to the DBMS (ifc_db)
DATABASE = "ifcdb"              # This is the specific database within the DBMS
USERNAME = "neo4j"
PASSWORD = "test1234"           # Using the provided password

def test_connection(uri, auth, database):
    """Test the connection to Neo4j database"""
    try:
        with GraphDatabase.driver(uri, auth=auth) as driver:
            # Test if we can connect and run a simple query
            with driver.session(database=database) as session:
                # Use a simple boolean query to avoid type comparison issues
                result = session.run("RETURN true AS connected")
                record = result.single()
                
                # Log the result for debugging
                if record and "connected" in record:
                    logger.info(f"Connection successful! Test result: {record['connected']}")
                    return True
                else:
                    logger.warning("Connection test returned unexpected result")
                    return False
    except Exception as e:
        logger.error(f"Connection failed: {e}")
        return False

def create_constraints_and_indexes(uri, auth, database):
    """Create constraints and indexes for IFC data model"""
    try:
        with GraphDatabase.driver(uri, auth=auth) as driver:
            with driver.session(database=database) as session:
                # Create constraints - assuming IfcGuid is a unique identifier
                logger.info("Creating constraints...")
                
                # UniqueId constraint for IfcElement nodes
                session.run("""
                    CREATE CONSTRAINT IF NOT EXISTS FOR (e:IfcElement) 
                    REQUIRE e.GlobalId IS UNIQUE
                """)
                
                # UniqueId constraint for IfcSpatialElement nodes
                session.run("""
                    CREATE CONSTRAINT IF NOT EXISTS FOR (s:IfcSpatialElement) 
                    REQUIRE s.GlobalId IS UNIQUE
                """)
                
                # Create indexes for common properties to improve query performance
                logger.info("Creating indexes...")
                
                # Index on name property for all nodes
                session.run("""
                    CREATE INDEX IF NOT EXISTS FOR (n:IfcProduct) ON (n.Name)
                """)
                
                # Index on type for classification
                session.run("""
                    CREATE INDEX IF NOT EXISTS FOR (n:IfcProduct) ON (n.ObjectType)
                """)
                
                # Check the constraints and indexes
                logger.info("Listing created constraints and indexes:")
                result = session.run("SHOW CONSTRAINTS")
                for record in result:
                    logger.info(f"Constraint: {record}")
                
                result = session.run("SHOW INDEXES")
                for record in result:
                    logger.info(f"Index: {record}")
                
                return True
    except Exception as e:
        logger.error(f"Failed to create constraints and indexes: {e}")
        return False

if __name__ == "__main__":
    logger.info("Testing connection to Neo4j database...")
    
    # Use hardcoded credentials
    auth = (USERNAME, PASSWORD)
    
    if test_connection(URI, auth, DATABASE):
        logger.info("Creating constraints and indexes...")
        create_constraints_and_indexes(URI, auth, DATABASE)
        logger.info("Setup complete!")
    else:
        logger.error("Connection test failed. Please check your connection settings.") 