@echo off
REM Process an IFC file with topology analysis enabled

if "%1"=="" (
    echo Error: Please provide an IFC file path as the first argument
    echo Usage: process_with_topology.bat path\to\your\file.ifc [--clear]
    exit /b 1
)

REM Activate virtual environment if present
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

REM Process the file with topology analysis enabled
if "%2"=="--clear" (
    python run_with_topology.py %1 --clear
) else (
    python run_with_topology.py %1
)

echo.
echo To use the enriched graph, connect to Neo4j and try these queries:
echo.
echo 1. View all relationship types:
echo MATCH ()-[r]-() RETURN type(r) as type, count(r) as count ORDER BY count DESC
echo.
echo 2. Find all adjacent elements:
echo MATCH (a)-[r:ADJACENT]->(b) RETURN a.Name, b.Name, r.relationshipSource LIMIT 10
echo.
echo 3. Find all spaces connected by openings:
echo MATCH (a:Space)-[r:CONNECTS_SPACES]->(b:Space) RETURN a.Name, b.Name 