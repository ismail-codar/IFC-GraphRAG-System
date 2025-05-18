# Neo4j Setup Guide

This guide will help you set up and start your Neo4j database for use with the IFC Knowledge Graph project.

## Starting Neo4j Database

1. **Open Neo4j Desktop**
   - Make sure Neo4j Desktop is installed and running
   - You should see the Neo4j Desktop GUI

2. **Start Database Instance**
   - In Neo4j Desktop, navigate to the "Projects" tab (left sidebar)
   - Find your "IFC_Knowledge_Graph" project (or create one if it doesn't exist)
   - In the project, look for your database (named "ifc_db")
   - If the database isn't started, you'll see a "Start" button. Click it.
   - Wait for the database to start (the button will turn into a "Stop" button and show a green indication)

3. **Check Connection Details**
   - Once the database is started, click the "..." menu next to the database
   - Select "Connection Details"
   - You should see information like:
     - Bolt URI: `bolt://localhost:7687`
     - Browser URL: `http://localhost:7474/browser/`
     - Username: `neo4j`
     - Password: Your password (default is `neo4j` for new installations)

4. **Open Neo4j Browser**
   - Click the "Open" button to launch Neo4j Browser
   - This should open a web browser with Neo4j Browser
   - Connect using your credentials

## Testing Connection

1. **In Neo4j Browser**
   - Type a simple Cypher query in the command bar at the top:
   ```
   RETURN 'Hello from Neo4j!' AS message
   ```
   - Click the "Run" button (or press Ctrl+Enter)
   - You should see the result "Hello from Neo4j!"

2. **Using Our Test Script**
   - Once the database is started, run our test script:
   ```
   python direct_connection_test.py
   ```
   - The script should connect to Neo4j and return a success message

## Creating a New Database (If Needed)

If you need to create a new database:

1. In Neo4j Desktop, navigate to the "Projects" tab
2. Click on your project (or create a new one)
3. Click "Add" > "Local DBMS"
4. Give it a name (e.g., "ifc_db")
5. Set a password
6. Click "Create"
7. Wait for the database to be created
8. Click "Start" to start the database

## Troubleshooting

If you can't connect to Neo4j:

1. **Check if the database is running**
   - Make sure the database shows as "Started" in Neo4j Desktop
   - Look for the green indicator next to the database name

2. **Check the connection details**
   - Verify the Bolt URI is `bolt://localhost:7687`
   - Ensure you're using the correct username and password

3. **Check for port conflicts**
   - Make sure no other application is using ports 7474, 7473, or 7687
   - You can check this with `netstat -ano | findstr "7474 7473 7687"` in the command prompt

4. **Restart Neo4j**
   - Try stopping and starting the database
   - If needed, restart Neo4j Desktop completely 