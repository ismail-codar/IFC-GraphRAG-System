# Parallel Processing in IFC to Neo4j Knowledge Graph

This document explains the parallel processing feature in the IFC to Neo4j Knowledge Graph tool, its implementation details, and usage guidelines.

## Overview

The parallel processing feature enables faster conversion of IFC models to Neo4j by utilizing multiple CPU cores. This is particularly beneficial for large IFC files with thousands of elements, which can be processed in parallel to significantly reduce the overall conversion time.

## Implementation Details

### Core Components

1. **ParallelProcessor Class**: A generic utility class that manages thread or process pools and provides methods for parallel execution.

2. **TaskBatch Class**: A utility for dividing work into manageable batches for parallel processing.

3. **Parallel Processing Methods**: Specialized methods in the IfcProcessor class for processing elements and relationships in parallel.

### Design Choices

- **Threading vs Multiprocessing**: The implementation primarily uses thread-based parallelism rather than process-based parallelism for database operations, as Neo4j operations are I/O-bound and benefit more from threading.

- **Batch Processing**: Data is processed in batches to reduce overhead and optimize performance.

- **Thread Safety**: The implementation ensures thread safety for critical operations through proper locking mechanisms.

## Performance Benefits

Parallel processing offers several performance advantages:

1. **Reduced Processing Time**: By utilizing multiple CPU cores, the processing time for large IFC files can be reduced significantly.

2. **Improved Throughput**: The number of elements processed per second increases with parallel processing.

3. **Efficient Resource Utilization**: The system can make better use of available CPU resources.

## Usage

### Command Line Interface

To enable parallel processing via the command line:

```bash
python -m ifc_knowledge_graph.cli.ifc_to_neo4j_cli path/to/model.ifc --parallel --workers 4
```

Parameters:
- `--parallel` or `-par`: Enable parallel processing
- `--workers` or `-w`: Specify the number of parallel workers (default: CPU count)

### Programmatic Usage

To enable parallel processing in code:

```python
from ifc_to_graph.processor import IfcProcessor

processor = IfcProcessor(
    ifc_file_path="path/to/model.ifc",
    neo4j_uri="bolt://localhost:7687",
    neo4j_username="neo4j",
    neo4j_password="password",
    parallel_processing=True,
    max_workers=4  # Optional, defaults to CPU count
)

stats = processor.process(batch_size=100)
```

## Benchmarking

The repository includes a benchmarking script that compares sequential and parallel processing:

```bash
python examples/parallel_processing_example.py --ifc-file path/to/model.ifc
```

This script runs tests with different batch sizes in both sequential and parallel modes, and generates a detailed performance comparison report.

## Recommendations

- **Large Models**: For IFC models with thousands of elements, parallel processing is highly recommended.
- **Worker Count**: For optimal performance, use a worker count equal to or slightly higher than your physical CPU core count.
- **Batch Size**: Experiment with different batch sizes (50-200) to find the optimal setting for your specific use case.
- **Memory Requirements**: Parallel processing may require more memory. Ensure your system has sufficient RAM.

## Limitations

- Parallel processing may not provide significant benefits for small IFC files (fewer than a few hundred elements).
- Excessive parallelism (too many workers) can cause contention and degrade performance.
- Process-based parallelism is not suitable for Neo4j operations due to the connection overhead.

## Future Improvements

Potential future enhancements to the parallel processing feature:

1. **Adaptive Worker Count**: Dynamically adjust the number of workers based on system load.
2. **Distributed Processing**: Support for processing across multiple machines.
3. **Fine-grained Task Scheduling**: Implement more sophisticated task scheduling based on task complexity. 