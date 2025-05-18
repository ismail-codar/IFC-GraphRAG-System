"""
Parallel Processing Utilities

This module provides utilities for parallel processing of tasks,
including thread and process pools with proper resource management.
"""

import logging
import time
import threading
import concurrent.futures
from typing import List, Callable, Any, Dict, Optional, Tuple, TypeVar, Generic, Iterator
from functools import partial
import os

# Configure logging
logger = logging.getLogger(__name__)

# Type variable for generic functions
T = TypeVar('T')
R = TypeVar('R')

class TaskBatch(Generic[T]):
    """
    A batch of items to be processed in parallel.
    """
    
    def __init__(self, items: List[T], batch_size: int, name: str = "Task"):
        """
        Initialize a batch of tasks.
        
        Args:
            items: List of items to process
            batch_size: Size of each batch
            name: Name of the task for logging
        """
        self.items = items
        self.batch_size = batch_size
        self.name = name
        self.total_items = len(items)
        
    def get_batches(self) -> List[List[T]]:
        """
        Split items into batches.
        
        Returns:
            List of batches, each containing up to batch_size items
        """
        return [
            self.items[i:i + self.batch_size]
            for i in range(0, self.total_items, self.batch_size)
        ]
        
    def iter_batches(self) -> Iterator[Tuple[int, List[T]]]:
        """
        Iterate over batches with their indices.
        
        Yields:
            Tuples of (batch_index, batch_items)
        """
        batches = self.get_batches()
        for i, batch in enumerate(batches):
            yield i, batch


class ParallelProcessor:
    """
    Process tasks in parallel using a thread or process pool.
    """
    
    def __init__(
        self, 
        max_workers: Optional[int] = None, 
        use_processes: bool = False,
        name: str = "Parallel Processor"
    ):
        """
        Initialize the parallel processor.
        
        Args:
            max_workers: Maximum number of workers (default: number of CPUs)
            use_processes: Whether to use processes instead of threads
            name: Name of the processor for logging
        """
        self.max_workers = max_workers or os.cpu_count() or 4
        self.use_processes = use_processes
        self.name = name
        self._executor = None
        self._lock = threading.RLock()
        
        # Choose executor class based on use_processes
        self._executor_class = (
            concurrent.futures.ProcessPoolExecutor 
            if use_processes 
            else concurrent.futures.ThreadPoolExecutor
        )
        
        logger.info(
            f"Initialized {self.name} with {self.max_workers} "
            f"{'processes' if use_processes else 'threads'}"
        )
    
    def __enter__(self):
        """Support context manager protocol."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up resources."""
        self.shutdown()
    
    def get_executor(self) -> concurrent.futures.Executor:
        """
        Get or create the executor instance.
        
        Returns:
            Thread or process pool executor
        """
        with self._lock:
            if self._executor is None:
                self._executor = self._executor_class(max_workers=self.max_workers)
            return self._executor
    
    def shutdown(self) -> None:
        """Shut down the executor."""
        with self._lock:
            if self._executor is not None:
                self._executor.shutdown(wait=True)
                self._executor = None
    
    def map(self, fn: Callable[[T], R], items: List[T], timeout: Optional[float] = None) -> List[R]:
        """
        Apply a function to each item in parallel.
        
        Args:
            fn: Function to apply to each item
            items: List of items to process
            timeout: Maximum time to wait for completion (None = no limit)
            
        Returns:
            List of results in the same order as items
        """
        if not items:
            return []
        
        executor = self.get_executor()
        
        try:
            start_time = time.time()
            results = list(executor.map(fn, items, timeout=timeout))
            elapsed = time.time() - start_time
            
            logger.info(
                f"Processed {len(items)} items in {elapsed:.2f}s "
                f"({len(items)/elapsed:.2f} items/s)"
            )
            
            return results
        
        except concurrent.futures.TimeoutError:
            logger.error(f"Timeout occurred after {timeout}s while processing items")
            raise
    
    def process_batches(
        self, 
        batch_processor: Callable[[List[T]], List[R]], 
        task_batch: TaskBatch[T],
        timeout: Optional[float] = None,
        show_progress: bool = True
    ) -> List[R]:
        """
        Process batches of items in parallel.
        
        Args:
            batch_processor: Function to process a batch of items
            task_batch: TaskBatch object containing items and batch configuration
            timeout: Maximum time to wait for batch completion
            show_progress: Whether to log progress information
            
        Returns:
            Combined list of results from all batches
        """
        batches = task_batch.get_batches()
        batch_count = len(batches)
        
        if batch_count == 0:
            return []
        
        if batch_count == 1:
            # No need for parallelism with a single batch
            logger.info(f"Processing single batch of {len(batches[0])} {task_batch.name} items")
            return batch_processor(batches[0])
        
        logger.info(
            f"Processing {task_batch.total_items} {task_batch.name} items "
            f"in {batch_count} batches with {self.max_workers} workers"
        )
        
        start_time = time.time()
        
        # Create a lock for thread-safe progress updates
        progress_lock = threading.RLock()
        completed_batches = [0]  # Use list for mutable reference in closure
        
        def process_batch_with_progress(batch_index: int, batch: List[T]) -> List[R]:
            """Process a batch and update progress."""
            batch_start = time.time()
            try:
                result = batch_processor(batch)
                batch_time = time.time() - batch_start
                
                if show_progress:
                    with progress_lock:
                        completed_batches[0] += 1
                        progress = completed_batches[0] / batch_count * 100
                        logger.info(
                            f"Batch {batch_index+1}/{batch_count} complete "
                            f"({progress:.1f}%, {len(batch)/batch_time:.1f} items/s)"
                        )
                
                return result
            except Exception as e:
                logger.error(f"Error processing batch {batch_index+1}: {str(e)}")
                raise
        
        executor = self.get_executor()
        futures = []
        
        # Submit all batches
        for i, batch in enumerate(batches):
            future = executor.submit(
                process_batch_with_progress, i, batch
            )
            futures.append(future)
        
        # Collect results as they complete
        results = []
        try:
            for future in concurrent.futures.as_completed(futures, timeout=timeout):
                batch_result = future.result()
                results.extend(batch_result)
        except concurrent.futures.TimeoutError:
            logger.error(f"Timeout occurred after {timeout}s while processing batches")
            raise
        
        elapsed = time.time() - start_time
        
        logger.info(
            f"Completed processing {task_batch.total_items} {task_batch.name} items "
            f"in {elapsed:.2f}s ({task_batch.total_items/elapsed:.2f} items/s)"
        )
        
        return results


def parallel_process(
    items: List[T],
    processor_function: Callable[[T], R],
    max_workers: Optional[int] = None,
    batch_size: int = 100,
    use_processes: bool = False,
    task_name: str = "items"
) -> List[R]:
    """
    Process a list of items in parallel using a simplified interface.
    
    Args:
        items: List of items to process
        processor_function: Function to apply to each item
        max_workers: Maximum number of workers (default: CPU count)
        batch_size: Size of each batch
        use_processes: Whether to use processes instead of threads
        task_name: Name of the tasks for logging
        
    Returns:
        List of results from processing each item
    """
    with ParallelProcessor(max_workers=max_workers, use_processes=use_processes) as processor:
        return processor.map(processor_function, items)


def parallel_batch_process(
    items: List[T],
    batch_processor: Callable[[List[T]], List[R]],
    max_workers: Optional[int] = None,
    batch_size: int = 100,
    use_processes: bool = False,
    task_name: str = "items",
    timeout: Optional[float] = None
) -> List[R]:
    """
    Process batches of items in parallel using a simplified interface.
    
    Args:
        items: List of items to process
        batch_processor: Function to process a batch of items
        max_workers: Maximum number of workers (default: CPU count)
        batch_size: Size of each batch
        use_processes: Whether to use processes instead of threads
        task_name: Name of the tasks for logging
        timeout: Maximum time to wait for completion
        
    Returns:
        Combined list of results from all batches
    """
    task_batch = TaskBatch(items, batch_size, task_name)
    
    with ParallelProcessor(max_workers=max_workers, use_processes=use_processes) as processor:
        return processor.process_batches(
            batch_processor,
            task_batch,
            timeout=timeout
        ) 