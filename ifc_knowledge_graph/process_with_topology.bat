@echo off
REM Process IFC file with topological analysis enabled
REM This script activates the Python virtual environment and runs the processor

ECHO "Starting IFC processing with topological analysis..."

REM Activate the virtual environment
CALL venv\Scripts\activate.bat

REM Find sample IFC file in the data directory
FOR /F "tokens=*" %%G IN ('dir /b /s data\*.ifc') DO (
    SET IFC_FILE=%%G
    GOTO FOUND_FILE
)

:FOUND_FILE
ECHO "Using IFC file: %IFC_FILE%"

REM Clear the database and run the processor
python run_with_topology.py --ifc-file "%IFC_FILE%" --clear --batch-size 100

REM Deactivate the virtual environment
CALL venv\Scripts\deactivate.bat

ECHO "Processing completed."
pause 