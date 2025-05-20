#!/usr/bin/env python3
"""
Fix the Neo4j database schema by dropping old non-prefixed constraints.
"""

import logging
from src.ifc_to_graph.database.neo4j_connector import Neo4jConnector

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Main function to fix schema"""
    try:
        # Connect to Neo4j
        logger.info("Connecting to Neo4j database")
        conn = Neo4jConnector('neo4j://localhost:7687', 'neo4j', 'test1234')
        
        # 1. List all constraints
        logger.info("Fetching all database constraints")
        constraints = conn.run_query("SHOW CONSTRAINTS")
        
        # 2. Identify old-style non-prefixed constraints to drop
        old_style_constraints = []
        for constraint in constraints:
            name = constraint.get('name')
            labels = constraint.get('labelsOrTypes', [])
            if not name:
                continue
                
            # Check if this is a non-prefixed spatial element label
            is_old_style = False
            for label in labels:
                if label in ['Project', 'Site', 'Building', 'Storey', 'Space']:
                    is_old_style = True
                    logger.info(f"Found old-style constraint: {name} for label {label}")
                    break
                    
            if is_old_style:
                old_style_constraints.append(name)
        
        # 3. Drop the old-style constraints
        logger.info(f"Found {len(old_style_constraints)} old-style constraints to drop")
        for constraint_name in old_style_constraints:
            logger.info(f"Dropping constraint: {constraint_name}")
            try:
                conn.run_query(f"DROP CONSTRAINT {constraint_name}")
                logger.info(f"Successfully dropped constraint: {constraint_name}")
            except Exception as e:
                logger.error(f"Error dropping constraint {constraint_name}: {str(e)}")
        
        # 4. Verify remaining constraints
        logger.info("Verifying remaining constraints")
        remaining = conn.run_query("SHOW CONSTRAINTS")
        
        logger.info("Remaining constraints:")
        for constraint in remaining:
            name = constraint.get('name')
            labels = constraint.get('labelsOrTypes', [])
            logger.info(f"  {name}: {labels}")
        
        # 5. Check for any indexes not associated with constraints that might need cleanup
        logger.info("Checking for any standalone indexes not associated with constraints")
        indexes = conn.run_query("SHOW INDEXES")
        
        standalone_indexes = []
        for index in indexes:
            if not index.get('owningConstraint') and index.get('name') != 'index_343aff4e' and index.get('name') != 'index_f7700477':
                # Skip the token lookup indexes which are system indexes
                labels = index.get('labelsOrTypes', [])
                if labels and any(label in ['Project', 'Site', 'Building', 'Storey', 'Space'] for label in labels):
                    standalone_indexes.append(index.get('name'))
                    logger.info(f"Found standalone index for old label: {index.get('name')} - {labels}")
        
        # 6. Drop standalone indexes for old labels
        for index_name in standalone_indexes:
            logger.info(f"Dropping index: {index_name}")
            try:
                conn.run_query(f"DROP INDEX {index_name}")
                logger.info(f"Successfully dropped index: {index_name}")
            except Exception as e:
                logger.error(f"Error dropping index {index_name}: {str(e)}")
        
        # 7. Verify schema is correct now
        logger.info("\n=== VERIFYING FINAL SCHEMA ===")
        
        logger.info("Checking node labels in database:")
        labels_result = conn.run_query("CALL db.labels()")
        db_labels = [record["label"] for record in labels_result]
        for label in sorted(db_labels):
            logger.info(f"Label: {label}")
        
        logger.info("\nChecking constraints in database:")
        final_constraints = conn.run_query("SHOW CONSTRAINTS")
        for constraint in final_constraints:
            name = constraint.get('name')
            labels = constraint.get('labelsOrTypes', [])
            properties = constraint.get('properties', [])
            logger.info(f"Constraint: {name} - Labels: {labels}, Properties: {properties}")
            
        # Report success
        logger.info("\nSchema cleanup completed successfully!")
        
        # Close connection
        conn.close()
        logger.info("Database connection closed")
    
    except Exception as e:
        logger.error(f"Error fixing schema: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 