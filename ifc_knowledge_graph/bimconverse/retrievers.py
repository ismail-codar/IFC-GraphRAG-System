"""
BIMConverse Advanced Retrievers

This module implements advanced retrieval strategies for GraphRAG with specific 
attention to IFC knowledge graphs and building model queries.
"""

import logging
from typing import Dict, List, Any, Optional, Union, Tuple
import json
import re

from neo4j import Driver, GraphDatabase, Result
import openai

# Import the prompt templates
from .prompts import (
    get_prompt_template, 
    format_prompt, 
    combine_prompts,
    PROMPT_TEMPLATES
)

# Import schema validation utilities
try:
    from .schema import SchemaMapper
    SCHEMA_VALIDATION_AVAILABLE = True
except ImportError:
    SCHEMA_VALIDATION_AVAILABLE = False

# Import visualization module
try:
    from .visualization import enhance_multihop_result_with_visualization
    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False

logger = logging.getLogger(__name__)

class MultihopRetriever:
    """
    A retriever that breaks complex queries into multiple simpler queries,
    executes them in sequence, and combines the results.
    """
    
    def __init__(
        self, 
        driver: Driver, 
        llm: Any, # This would be a LLM interface
        neo4j_schema: Optional[str] = None,
    ):
        """
        Initialize the multihop retriever.
        
        Args:
            driver: Neo4j driver instance
            llm: LLM instance for generating Cypher queries
            neo4j_schema: Optional schema string to override the default
        """
        self.driver = driver
        self.llm = llm
        self.schema = neo4j_schema or get_prompt_template("basic")
        self.schema_mapper = None
        if SCHEMA_VALIDATION_AVAILABLE:
            try:
                self.schema_mapper = SchemaMapper(driver)
                logger.info("Schema validation is enabled for MultihopRetriever")
            except Exception as e:
                logger.warning(f"Failed to initialize schema validation: {e}")
        logger.info("Initialized MultihopRetriever")

    def _decompose_query(self, query: str) -> List[str]:
        """
        Decompose a complex query into multiple simpler sub-queries.
        
        Args:
            query: The user's query
            
        Returns:
            A list of sub-queries
        """
        # Use the enhanced query decomposition prompt template
        prompt = format_prompt(query, strategy="query_decomposition")
        
        # Use the LLM to decompose the query
        response = self._llm_generate(prompt)
        
        # Parse the response to extract sub-queries
        # Improved parsing to handle numbered steps better
        sub_queries = []
        lines = response.split('\n')
        current_query = ""
        in_query = False
        step_pattern = r"^(\d+)[\.:\)]|^Step\s+(\d+)[\.:\)]|^[•*-]"
        
        for i, line in enumerate(lines):
            # Check if line starts a new step
            if re.match(step_pattern, line.strip()):
                # If we were already collecting a query, save it
                if current_query:
                    sub_queries.append(current_query.strip())
                
                # Start a new query collection
                current_query = line
                in_query = True
            elif in_query:
                # Continue collecting the current sub-query
                current_query += " " + line
                
                # Check if this might be the end of the current step
                # by looking ahead to see if the next line starts a new step
                if i + 1 < len(lines) and re.match(step_pattern, lines[i+1].strip()):
                    sub_queries.append(current_query.strip())
                    current_query = ""
                    in_query = False
        
        # Add the last sub-query if there is one
        if current_query:
            sub_queries.append(current_query.strip())
        
        # If no sub-queries were identified, use chain-of-thought to create them
        if not sub_queries:
            logger.info("No sub-queries identified with decomposition, trying chain-of-thought")
            return self._chain_of_thought_decomposition(query)
        
        logger.info(f"Decomposed query into {len(sub_queries)} sub-queries using decomposition prompt")
        return sub_queries
    
    def _chain_of_thought_decomposition(self, query: str) -> List[str]:
        """
        Use chain-of-thought prompting to decompose a complex query.
        
        Args:
            query: The user's query
            
        Returns:
            A list of sub-queries
        """
        # Use the chain-of-thought prompt template
        prompt = format_prompt(query, strategy="chain_of_thought")
        
        # Use the LLM to analyze and decompose the query
        response = self._llm_generate(prompt)
        
        # Extract the reasoning steps and Cypher query patterns
        sub_queries = []
        step_blocks = []
        current_block = ""
        
        lines = response.split('\n')
        in_code_block = False
        
        for line in lines:
            # Track code blocks which contain Cypher queries
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                if not in_code_block and current_block:
                    step_blocks.append(current_block)
                    current_block = ""
                continue
            
            # Collect lines inside code blocks
            if in_code_block:
                # Skip language identifier line if present
                if line.strip().lower() == "cypher":
                    continue
                current_block += line + "\n"
            elif line.strip().startswith("Step") or re.match(r"^\d+\.", line.strip()):
                # This line marks a new reasoning step
                if current_block:
                    step_blocks.append(current_block)
                current_block = line
            elif current_block:
                # Continue collecting the current reasoning step
                current_block += " " + line
        
        # Add the last block if there is one
        if current_block:
            step_blocks.append(current_block)
        
        # Convert reasoning steps to sub-queries
        for block in step_blocks:
            # Extract just the reasoning as a sub-query
            sub_queries.append(block.strip())
        
        logger.info(f"Decomposed query into {len(sub_queries)} sub-queries using chain-of-thought")
        return sub_queries

    def _generate_cypher(self, query: str, previous_context: Optional[str] = None) -> str:
        """
        Generate a Cypher query for a given natural language query.
        
        Args:
            query: The natural language query
            previous_context: Optional context from previous query steps
            
        Returns:
            A Cypher query string
        """
        # If we have previous context, use the context accumulation prompt
        if previous_context:
            prompt = format_prompt(
                query, 
                strategy="context_accumulation", 
                previous_context=previous_context
            )
        else:
            # Otherwise use the schema prompt with the query
            prompt = self.schema + f"\n\nConvert this question to a Cypher query: {query}"
        
        # Use the LLM to generate a Cypher query
        response = self._llm_generate(prompt)
        
        # Extract Cypher from the response (improved handling of code blocks)
        cypher_query = ""
        if "```" in response:
            # Extract code between backticks
            parts = response.split("```")
            for i in range(1, len(parts), 2):
                if i < len(parts):
                    code_block = parts[i]
                    # Remove cypher language identifier if present
                    if code_block.strip().startswith("cypher"):
                        code_block = code_block[6:].strip()
                    else:
                        code_block = code_block.strip()
                    
                    # If this looks like a valid Cypher query, use it
                    if "MATCH" in code_block or "RETURN" in code_block:
                        cypher_query = code_block
                        break
        else:
            # If no code blocks, use the entire response
            cypher_query = response.strip()
        
        logger.info(f"Generated Cypher query: {cypher_query}")
        return cypher_query

    def _execute_cypher(self, cypher_query: str) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query and return the results.
        
        Args:
            cypher_query: The Cypher query to execute
            
        Returns:
            A list of result records as dictionaries
        """
        try:
            with self.driver.session() as session:
                result = session.run(cypher_query)
                records = [record.data() for record in result]
                logger.info(f"Executed Cypher query, got {len(records)} results")
                return records
        except Exception as e:
            logger.error(f"Error executing Cypher query: {e}")
            return []

    def retrieve(self, query: str) -> Dict[str, Any]:
        """
        Execute a multihop retrieval for a complex query.
        
        Args:
            query: The natural language query
            
        Returns:
            A dictionary containing the results and query details
        """
        # Step 1: Decompose the query
        sub_queries = self._decompose_query(query)
        
        # Step 2: Process each sub-query with context accumulation
        intermediate_results = []
        accumulated_context = ""
        
        for i, sub_query in enumerate(sub_queries):
            logger.info(f"Processing sub-query {i+1}/{len(sub_queries)}: {sub_query}")
            
            # Generate Cypher with accumulated context
            cypher_query = self._generate_cypher(sub_query, accumulated_context if i > 0 else None)
            
            # Execute Cypher
            results = self._execute_cypher(cypher_query)
            
            # Store intermediate results
            step_result = {
                "sub_query": sub_query,
                "cypher_query": cypher_query,
                "results": results
            }
            intermediate_results.append(step_result)
            
            # Update accumulated context with this step's results
            if results:
                result_summary = f"Step {i+1} found {len(results)} results. "
                
                # Add a sample of the results if available
                if len(results) > 0:
                    sample = results[0]
                    result_summary += f"Sample result: {str(sample)}"
                
                accumulated_context += result_summary + "\n"
        
        # Step 3: Compile final results
        return {
            "query": query,
            "sub_queries": sub_queries,
            "intermediate_results": intermediate_results,
            "accumulated_context": accumulated_context,
            "strategy": "multihop"
        }
        
    def search(
        self, 
        query: str,
        multihop_detection: bool = True,
        use_cot: bool = True,
        visualize: bool = True,
        max_hops: int = 3
    ) -> Dict[str, Any]:
        """
        Search for results using multihop reasoning.
        
        Args:
            query: User query
            multihop_detection: Whether to detect and handle multihop queries
            use_cot: Whether to use chain-of-thought reasoning
            visualize: Whether to include visualizations in the results
            max_hops: Maximum number of hops to perform
            
        Returns:
            Search results with contextual information
        """
        logger.info(f"Multihop search for query: {query}")
        
        # Check if we need to validate or enhance the schema
        if self.schema_mapper and multihop_detection:
            logger.info("Using schema validation for multihop query")
            enhanced_schema = self.schema_mapper.enhance_schema_prompt()
            if enhanced_schema:
                self.schema = enhanced_schema
                logger.info("Using enhanced schema from database for better query accuracy")
        
        # Determine if this is a multihop query
        is_multihop = False
        if multihop_detection:
            is_multihop = self._is_multihop_query(query)
            logger.info(f"Multihop detection: {is_multihop}")
        
        # Initialize multihop memory for tracking context across steps
        multihop_memory = {
            "query": query,
            "steps": [],
            "accumulated_context": [],
            "is_multihop": is_multihop
        }
        
        if is_multihop:
            # Handle multihop reasoning
            return self._process_multihop_query(query, use_cot, visualize, max_hops, multihop_memory)
        else:
            # Handle single hop query
            return self._process_single_hop_query(query, use_cot, visualize, multihop_memory)
    
    def _is_multihop_query(self, query: str) -> bool:
        """
        Determine if a query requires multihop reasoning.
        
        Args:
            query: User query
            
        Returns:
            Boolean indicating if this is a multihop query
        """
        # Use the chain-of-thought prompt template
        prompt = format_prompt(query, strategy="chain_of_thought")
        
        # Use the LLM to analyze and decompose the query
        response = self._llm_generate(prompt)
        
        # Keywords that suggest multihop reasoning is needed
        multihop_indicators = [
            "multiple steps",
            "first find",
            "then find",
            "next find",
            "step 1",
            "step 2",
            "first identify",
            "then locate",
            "finally determine",
            "multi-step",
            "multihop"
        ]
        
        # Check if the response contains any multihop indicators
        for indicator in multihop_indicators:
            if indicator.lower() in response.lower():
                return True
        
        # As a fallback, check the query itself for common multihop patterns
        multihop_query_patterns = [
            r"(what|which|how many) .+ (that|which|who) .+",
            r"(find|show|get) .+ (that|which) .+ (and|or) .+",
            r"(in|on|near|adjacent to|connected to) .+ (that|which|and) .+",
            r"(made of|composed of|built with) .+ (that|which|and) .+"
        ]
        
        for pattern in multihop_query_patterns:
            if re.search(pattern, query.lower()):
                return True
                
        return False
    
    def _process_multihop_query(
        self, 
        query: str,
        use_cot: bool,
        visualize: bool,
        max_hops: int,
        multihop_memory: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process a query that requires multihop reasoning.
        
        Args:
            query: User query
            use_cot: Whether to use chain-of-thought reasoning
            visualize: Whether to visualize the results
            max_hops: Maximum number of hops to perform
            multihop_memory: Memory context for the multihop process
            
        Returns:
            Search results with reasoning steps
        """
        logger.info("Processing as multihop query")
        
        # Decompose the query into sub-steps
        sub_queries = self._decompose_query(query)
        
        # Track all results
        all_results = []
        accumulated_context = []
        
        # Process each sub-query
        for i, sub_query in enumerate(sub_queries[:max_hops]):
            logger.info(f"Processing sub-query {i+1}: {sub_query}")
            
            # Add context from previous steps
            context_enriched_query = sub_query
            if accumulated_context:
                context_str = ". ".join(accumulated_context)
                context_enriched_query = f"Context: {context_str}. Query: {sub_query}"
            
            # Execute the sub-query
            step_result = self._process_single_hop_query(
                context_enriched_query, 
                use_cot, 
                visualize and i == len(sub_queries) - 1,  # Only visualize the final step
                multihop_memory
            )
            
            # Extract key information to add to the context
            if "result_text" in step_result and step_result["result_text"]:
                accumulated_context.append(step_result["result_text"])
            
            # Record this step
            multihop_memory["steps"].append({
                "sub_query": sub_query,
                "context_enriched_query": context_enriched_query,
                "cypher": step_result.get("cypher", ""),
                "results": step_result.get("results", []),
                "result_text": step_result.get("result_text", "")
            })
            multihop_memory["accumulated_context"] = accumulated_context
            
            all_results.append(step_result)
        
        # Combine all results into a final answer
        final_result = self._combine_multihop_results(all_results, query, multihop_memory)
        
        # Add visualization if requested
        if visualize and VISUALIZATION_AVAILABLE:
            try:
                enhanced_result = enhance_multihop_result_with_visualization(final_result)
                return enhanced_result
            except Exception as e:
                logger.error(f"Error adding visualization to multihop results: {e}")
                return final_result
        else:
            return final_result
            
    def _process_single_hop_query(
        self, 
        query: str,
        use_cot: bool,
        visualize: bool,
        multihop_memory: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process a single-hop query.
        
        Args:
            query: User query
            use_cot: Whether to use chain-of-thought reasoning
            visualize: Whether to visualize the results
            multihop_memory: Memory context for the multihop process
            
        Returns:
            Search results
        """
        # Select the appropriate prompt based on reasoning strategy
        if use_cot:
            prompt_strategy = "chain_of_thought"
        else:
            prompt_strategy = "basic"
            
        # Format the prompt
        prompt = format_prompt(query, strategy=prompt_strategy, schema=self.schema)
        
        # Generate Cypher query
        cypher = self._generate_cypher(prompt)
        
        # Validate and potentially fix the Cypher query if schema validation is available
        if self.schema_mapper:
            try:
                validation = self.schema_mapper.validate_query_against_schema(cypher)
                if not validation["is_valid"] and "fixed_query" in validation:
                    logger.info(f"Fixing invalid Cypher query based on schema validation")
                    logger.info(f"Original: {cypher}")
                    logger.info(f"Fixed: {validation['fixed_query']}")
                    cypher = validation["fixed_query"]
            except Exception as e:
                logger.warning(f"Schema validation failed: {e}")
        
        # Execute Cypher query
        results = self._execute_cypher(cypher)
        
        # Generate a text summary of the results
        result_text = self._generate_result_text(query, cypher, results)
        
        # Package the result
        result = {
            "query": query,
            "cypher": cypher,
            "results": results,
            "result_text": result_text,
            "multihop_memory": multihop_memory
        }
        
        # Add visualization if requested
        if visualize and VISUALIZATION_AVAILABLE:
            try:
                enhanced_result = enhance_multihop_result_with_visualization(result)
                return enhanced_result
            except Exception as e:
                logger.error(f"Error adding visualization to results: {e}")
                return result
        else:
            return result
            
    def _generate_result_text(
        self, 
        query: str, 
        cypher: str, 
        results: List[Dict[str, Any]]
    ) -> str:
        """
        Generate a natural language description of the query results.
        
        Args:
            query: Original query
            cypher: Cypher query executed
            results: Query results
            
        Returns:
            Natural language description of the results
        """
        # Create a concise result summary
        if not results:
            return "No results were found for this query."
            
        # Prepare results for LLM consumption
        result_sample = results[:5]  # Limit to 5 to avoid token limits
        result_str = json.dumps(result_sample, default=str)
        
        # Prompt the LLM to explain the results
        prompt = f"""
        Original query: {query}
        
        Cypher query executed: {cypher}
        
        Results (limited to 5 items): {result_str}
        
        Total results found: {len(results)}
        
        Please provide a concise natural language summary of these results. Explain what was found and how it answers the original query.
        """
        
        try:
            # Generate the result text using the LLM
            response = self._llm_generate(prompt)
            return response
        except Exception as e:
            logger.error(f"Error generating result text: {e}")
            # Fallback: create a basic summary
            if len(results) == 1:
                return f"Found 1 result for the query: {query}"
            else:
                return f"Found {len(results)} results for the query: {query}"
                
    def _combine_multihop_results(
        self, 
        results: List[Dict[str, Any]], 
        query: str,
        multihop_memory: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Combine results from multiple reasoning steps into a final answer.
        
        Args:
            results: Results from each reasoning step
            query: Original query
            multihop_memory: Memory context for the multihop process
            
        Returns:
            Combined results
        """
        # Extract key information from each step
        steps_info = []
        for i, step in enumerate(multihop_memory["steps"]):
            step_summary = {
                "step_number": i+1,
                "sub_query": step["sub_query"],
                "cypher": step["cypher"],
                "result_summary": step["result_text"]
            }
            steps_info.append(step_summary)
            
        # Get the final result data from the last step
        final_result = results[-1] if results else {}
        
        # Add multihop reasoning information
        final_result["original_query"] = query
        final_result["is_multihop"] = True
        final_result["reasoning_steps"] = steps_info
        final_result["multihop_memory"] = multihop_memory
        
        # Generate a complete answer that combines all steps
        final_result["final_answer"] = self._generate_final_answer(query, multihop_memory)
        
        return final_result
        
    def _generate_final_answer(self, query: str, multihop_memory: Dict[str, Any]) -> str:
        """
        Generate a comprehensive final answer from multihop reasoning steps.
        
        Args:
            query: Original query
            multihop_memory: Memory context with all reasoning steps
            
        Returns:
            Final comprehensive answer
        """
        # Create a summary of the reasoning steps
        steps_summary = []
        for i, step in enumerate(multihop_memory["steps"]):
            step_text = f"Step {i+1}: {step['sub_query']}\nResults: {step['result_text']}"
            steps_summary.append(step_text)
            
        steps_str = "\n\n".join(steps_summary)
        
        # Prompt the LLM to create a final answer
        prompt = f"""
        Original query: {query}
        
        The query was answered through a multi-hop reasoning process with the following steps:
        
        {steps_str}
        
        Please provide a comprehensive final answer to the original query, synthesizing the information from all reasoning steps.
        The answer should be clear, concise, and directly address the original question.
        """
        
        try:
            # Generate the final answer using the LLM
            response = self._llm_generate(prompt)
            return response
        except Exception as e:
            logger.error(f"Error generating final answer: {e}")
            # Fallback: concatenate the individual step results
            final_texts = [step.get("result_text", "") for step in multihop_memory["steps"]]
            return " ".join(final_texts)

    def _llm_generate(self, prompt: str) -> str:
        """Adapter method to handle API differences in LLM implementations"""
        try:
            # Try the invoke method first (newer API)
            if hasattr(self.llm, 'invoke'):
                return self.llm.invoke(prompt)
            # Fall back to generate method (older API)
            elif hasattr(self.llm, 'generate'):
                return self.llm.generate(prompt)
            # Last resort: call the object directly if it's callable
            elif callable(self.llm):
                return self.llm(prompt)
            else:
                raise AttributeError("LLM object has no invoke or generate method and is not callable")
        except Exception as e:
            logger.error(f"Error generating text with LLM: {e}")
            return f"ERROR: Could not generate text with LLM: {str(e)}"


class ParentChildRetriever:
    """
    A retriever that leverages the parent-child hierarchy of IFC models
    to provide better context for queries.
    """
    
    def __init__(
        self, 
        driver: Driver, 
        llm: Any,
        neo4j_schema: Optional[str] = None,
    ):
        """
        Initialize the parent-child retriever.
        
        Args:
            driver: Neo4j driver instance
            llm: LLM instance for generating Cypher queries
            neo4j_schema: Optional schema string to override the default
        """
        self.driver = driver
        self.llm = llm
        self.schema = neo4j_schema or get_prompt_template("basic")
        logger.info("Initialized ParentChildRetriever")

    def _extract_target_element(self, query: str) -> str:
        """
        Extract the target element type from a query.
        
        Args:
            query: The natural language query
            
        Returns:
            The element type (Door, Window, Wall, etc.)
        """
        element_types = [
            "Door", "Window", "Wall", "Slab", "Beam", "Column", 
            "Railing", "Furniture", "Space", "Storey", "Building"
        ]
        
        # Use a simple keyword matching approach
        for element_type in element_types:
            if element_type.lower() in query.lower():
                return element_type
        
        # Default to generic Element
        return "Element"

    def _generate_hierarchical_query(self, query: str, element_type: str) -> str:
        """
        Generate a Cypher query that includes parent-child hierarchy.
        
        Args:
            query: The natural language query
            element_type: The target element type
            
        Returns:
            A Cypher query string
        """
        # Format the parent-child template with the query and element type
        prompt = format_prompt(
            query=query, 
            strategy="parent_child",
            element_name=element_type
        )
        
        # Use the LLM to generate a hierarchical Cypher query
        response = self._llm_generate(prompt)
        
        # Extract Cypher from the response
        cypher_query = ""
        if "```" in response:
            parts = response.split("```")
            if len(parts) > 1:
                cypher_block = parts[1]
                if cypher_block.startswith("cypher"):
                    cypher_query = cypher_block[6:].strip()
                else:
                    cypher_query = cypher_block.strip()
        else:
            cypher_query = response.strip()
        
        logger.info(f"Generated hierarchical Cypher query: {cypher_query}")
        return cypher_query

    def retrieve(self, query: str) -> Dict[str, Any]:
        """
        Execute a parent-child retrieval for a query.
        
        Args:
            query: The natural language query
            
        Returns:
            A dictionary containing the results and query details
        """
        # Step 1: Extract the target element type
        element_type = self._extract_target_element(query)
        logger.info(f"Extracted target element type: {element_type}")
        
        # Step 2: Generate a hierarchical Cypher query
        cypher_query = self._generate_hierarchical_query(query, element_type)
        
        # Step 3: Execute the query
        try:
            with self.driver.session() as session:
                result = session.run(cypher_query)
                records = [record.data() for record in result]
                logger.info(f"Executed hierarchical query, got {len(records)} results")
                
                return {
                    "query": query,
                    "element_type": element_type,
                    "cypher_query": cypher_query,
                    "results": records,
                    "strategy": "parent_child"
                }
        except Exception as e:
            logger.error(f"Error executing hierarchical query: {e}")
            return {
                "query": query,
                "element_type": element_type,
                "cypher_query": cypher_query,
                "error": str(e),
                "strategy": "parent_child"
            }

    def _llm_generate(self, prompt: str) -> str:
        """
        Adapter method to handle API differences between different LLM implementations.
        Some LLMs use generate() method while others (like neo4j-graphrag) use invoke().
        
        Args:
            prompt: The prompt to send to the LLM
            
        Returns:
            The LLM's response as a string
        """
        try:
            # Try the 'invoke' method (neo4j-graphrag OpenAILLM)
            if hasattr(self.llm, 'invoke'):
                response = self.llm.invoke(prompt)
                # Handle different response formats
                if hasattr(response, 'content'):
                    return response.content
                elif isinstance(response, str):
                    return response
                else:
                    return str(response)
            # Fall back to 'generate' method (custom implementation)
            elif hasattr(self.llm, 'generate'):
                return self.llm.generate(prompt)
            else:
                raise AttributeError("LLM object has neither 'invoke' nor 'generate' method")
        except Exception as e:
            logger.error(f"Error generating response from LLM: {e}")
            return f"Error: {str(e)}"


class HypotheticalQuestionRetriever:
    """
    A retriever that generates hypothetical questions about building elements
    and uses them to improve retrieval accuracy.
    """
    
    def __init__(
        self, 
        driver: Driver, 
        llm: Any,
        neo4j_schema: Optional[str] = None,
        question_cache: Optional[Dict[str, List[str]]] = None
    ):
        """
        Initialize the hypothetical question retriever.
        
        Args:
            driver: Neo4j driver instance
            llm: LLM instance for generating questions and Cypher queries
            neo4j_schema: Optional schema string to override the default
            question_cache: Optional cache for already generated questions
        """
        self.driver = driver
        self.llm = llm
        self.schema = neo4j_schema or get_prompt_template("basic")
        self.question_cache = question_cache or {}
        logger.info("Initialized HypotheticalQuestionRetriever")
    
    def _generate_hypothetical_questions(self, element_type: str, count: int = 5) -> List[str]:
        """
        Generate hypothetical questions about a building element type.
        
        Args:
            element_type: The building element type
            count: Number of questions to generate
            
        Returns:
            A list of hypothetical questions
        """
        # Check if questions for this element type are already cached
        if element_type in self.question_cache:
            return self.question_cache[element_type][:count]
        
        # Use the hypothetical question template
        prompt = get_prompt_template("hypothetical")
        prompt += f"\n\nGenerate {count} specific questions about {element_type}s in a building model:"
        
        # Use the LLM to generate questions
        response = self._llm_generate(prompt)
        
        # Parse the response to extract questions
        questions = []
        for line in response.split("\n"):
            line = line.strip()
            if line.startswith("-") or line.startswith("*") or (line.startswith(str(len(questions)+1)) and "?" in line):
                question = line.lstrip("- *0123456789. ")
                if question and "?" in question:
                    questions.append(question)
        
        # Cache the questions for future use
        self.question_cache[element_type] = questions
        
        logger.info(f"Generated {len(questions)} hypothetical questions for {element_type}")
        return questions[:count]
    
    def _find_best_matching_question(self, query: str, hypothetical_questions: List[str]) -> str:
        """
        Find the hypothetical question that best matches the user's query.
        
        Args:
            query: The user's query
            hypothetical_questions: List of hypothetical questions
            
        Returns:
            The best matching question
        """
        # This would normally use embeddings and vector similarity
        # For simplicity, we'll use the LLM to choose the best match
        
        prompt = f"""
        I have a user query and a list of hypothetical questions about building elements.
        Please select the hypothetical question that is most similar to the user query.
        
        User query: "{query}"
        
        Hypothetical questions:
        {json.dumps(hypothetical_questions, indent=2)}
        
        Return only the best matching question, enclosed in quotes.
        """
        
        response = self._llm_generate(prompt)
        
        # Extract the question from the response (assuming it's enclosed in quotes)
        match = re.search(r'"([^"]*)"', response)
        if match:
            best_match = match.group(1)
        else:
            # If no quoted text found, use the first hypothetical question
            best_match = hypothetical_questions[0] if hypothetical_questions else query
        
        logger.info(f"Best matching question: {best_match}")
        return best_match
    
    def _generate_cypher_from_question(self, question: str) -> str:
        """
        Generate a Cypher query from a hypothetical question.
        
        Args:
            question: The hypothetical question
            
        Returns:
            A Cypher query string
        """
        prompt = self.schema + f"\n\nConvert this question to a Cypher query: {question}"
        
        # Use the LLM to generate a Cypher query
        response = self._llm_generate(prompt)
        
        # Extract Cypher from the response
        cypher_query = ""
        if "```" in response:
            parts = response.split("```")
            if len(parts) > 1:
                cypher_block = parts[1]
                if cypher_block.startswith("cypher"):
                    cypher_query = cypher_block[6:].strip()
                else:
                    cypher_query = cypher_block.strip()
        else:
            cypher_query = response.strip()
        
        logger.info(f"Generated Cypher query from hypothetical question: {cypher_query}")
        return cypher_query
    
    def retrieve(self, query: str) -> Dict[str, Any]:
        """
        Execute a hypothetical question retrieval for a query.
        
        Args:
            query: The natural language query
            
        Returns:
            A dictionary containing the results and query details
        """
        # Step 1: Extract the target element type
        element_types = [
            "Door", "Window", "Wall", "Slab", "Beam", "Column", 
            "Railing", "Furniture", "Space", "Storey", "Building"
        ]
        
        element_type = "Building"  # Default
        for et in element_types:
            if et.lower() in query.lower():
                element_type = et
                break
        
        # Step 2: Generate hypothetical questions
        hypothetical_questions = self._generate_hypothetical_questions(element_type)
        
        # Step 3: Find best matching question
        best_question = self._find_best_matching_question(query, hypothetical_questions)
        
        # Step 4: Generate Cypher from the best matching question
        cypher_query = self._generate_cypher_from_question(best_question)
        
        # Step 5: Execute the query
        try:
            with self.driver.session() as session:
                result = session.run(cypher_query)
                records = [record.data() for record in result]
                logger.info(f"Executed query from hypothetical question, got {len(records)} results")
                
                return {
                    "query": query,
                    "element_type": element_type,
                    "hypothetical_questions": hypothetical_questions,
                    "best_matching_question": best_question,
                    "cypher_query": cypher_query,
                    "results": records,
                    "strategy": "hypothetical_question"
                }
        except Exception as e:
            logger.error(f"Error executing query from hypothetical question: {e}")
            return {
                "query": query,
                "element_type": element_type,
                "hypothetical_questions": hypothetical_questions,
                "best_matching_question": best_question,
                "cypher_query": cypher_query,
                "error": str(e),
                "strategy": "hypothetical_question"
            }

    def _llm_generate(self, prompt: str) -> str:
        """
        Adapter method to handle API differences between different LLM implementations.
        Some LLMs use generate() method while others (like neo4j-graphrag) use invoke().
        
        Args:
            prompt: The prompt to send to the LLM
            
        Returns:
            The LLM's response as a string
        """
        try:
            # Try the 'invoke' method (neo4j-graphrag OpenAILLM)
            if hasattr(self.llm, 'invoke'):
                response = self.llm.invoke(prompt)
                # Handle different response formats
                if hasattr(response, 'content'):
                    return response.content
                elif isinstance(response, str):
                    return response
                else:
                    return str(response)
            # Fall back to 'generate' method (custom implementation)
            elif hasattr(self.llm, 'generate'):
                return self.llm.generate(prompt)
            else:
                raise AttributeError("LLM object has neither 'invoke' nor 'generate' method")
        except Exception as e:
            logger.error(f"Error generating response from LLM: {e}")
            return f"Error: {str(e)}"


class HybridRetriever:
    """
    A hybrid retriever that combines graph traversal and vector search
    for improved retrieval accuracy.
    """
    
    def __init__(
        self, 
        driver: Driver, 
        llm: Any,
        embeddings_provider: Any,
        neo4j_schema: Optional[str] = None,
        vector_index_name: str = "element_embeddings",
        vector_node_label: str = "Element",
        vector_property: str = "embedding"
    ):
        """
        Initialize the hybrid retriever.
        
        Args:
            driver: Neo4j driver instance
            llm: LLM instance for generating queries
            embeddings_provider: Provider for generating embeddings
            neo4j_schema: Optional schema string to override the default
            vector_index_name: Name of the vector index in Neo4j
            vector_node_label: Label of nodes with vector embeddings
            vector_property: Name of the property containing vector embeddings
        """
        self.driver = driver
        self.llm = llm
        self.embeddings_provider = embeddings_provider
        self.schema = neo4j_schema or get_prompt_template("basic")
        self.vector_index_name = vector_index_name
        self.vector_node_label = vector_node_label
        self.vector_property = vector_property
        logger.info("Initialized HybridRetriever")
    
    def _generate_hybrid_cypher(self, query: str, embedding: List[float], limit: int = 5) -> str:
        """
        Generate a hybrid Cypher query combining vector search and graph traversal.
        
        Args:
            query: The natural language query
            embedding: The query embedding vector
            limit: Maximum number of results to return
            
        Returns:
            A Cypher query string
        """
        # Use the spatial reasoning prompt to generate a base query
        prompt = format_prompt(query, strategy="spatial")
        prompt += f"\n\nNow, generate a Neo4j Cypher query that combines vector similarity search with graph traversal to answer: {query}"
        
        # Add information about vector index
        prompt += f"""
        
        Use the vector index '{self.vector_index_name}' on {self.vector_node_label} nodes for vector similarity search.
        The vector property is '{self.vector_property}'.
        
        For example, a hybrid query might look like:
        ```
        // First find similar elements using vector search
        CALL db.index.vector.queryNodes('{self.vector_index_name}', {limit}, $embedding) YIELD node, score
        WITH node as element, score
        
        // Then traverse the graph to find related information
        MATCH path = (element)-[*1..2]-(related)
        RETURN element, related, score, path
        ```
        
        Generate a hybrid Cypher query for this question, ensuring it combines vector search with graph traversal.
        """
        
        # Use the LLM to generate a hybrid Cypher query
        response = self._llm_generate(prompt)
        
        # Extract Cypher from the response
        cypher_query = ""
        if "```" in response:
            parts = response.split("```")
            if len(parts) > 1:
                cypher_block = parts[1]
                if cypher_block.startswith("cypher"):
                    cypher_query = cypher_block[6:].strip()
                else:
                    cypher_query = cypher_block.strip()
        else:
            cypher_query = response.strip()
        
        logger.info(f"Generated hybrid Cypher query: {cypher_query}")
        return cypher_query
    
    def retrieve(self, query: str) -> Dict[str, Any]:
        """
        Execute a hybrid retrieval for a query.
        
        Args:
            query: The natural language query
            
        Returns:
            A dictionary containing the results and query details
        """
        # Step 1: Generate embeddings for the query
        embedding = self.embeddings_provider.embed_query(query)
        
        # Step 2: Generate a hybrid Cypher query
        cypher_query = self._generate_hybrid_cypher(query, embedding)
        
        # Step 3: Execute the query
        try:
            with self.driver.session() as session:
                # Create Cypher parameters with the embedding
                params = {"embedding": embedding, "query": query}
                
                # Execute the query
                result = session.run(cypher_query, params)
                records = [record.data() for record in result]
                logger.info(f"Executed hybrid query, got {len(records)} results")
                
                return {
                    "query": query,
                    "cypher_query": cypher_query,
                    "results": records,
                    "strategy": "hybrid"
                }
        except Exception as e:
            logger.error(f"Error executing hybrid query: {e}")
            return {
                "query": query,
                "cypher_query": cypher_query,
                "error": str(e),
                "strategy": "hybrid"
            }

    def _llm_generate(self, prompt: str) -> str:
        """
        Adapter method to handle API differences between different LLM implementations.
        Some LLMs use generate() method while others (like neo4j-graphrag) use invoke().
        
        Args:
            prompt: The prompt to send to the LLM
            
        Returns:
            The LLM's response as a string
        """
        try:
            # Try the 'invoke' method (neo4j-graphrag OpenAILLM)
            if hasattr(self.llm, 'invoke'):
                response = self.llm.invoke(prompt)
                # Handle different response formats
                if hasattr(response, 'content'):
                    return response.content
                elif isinstance(response, str):
                    return response
                else:
                    return str(response)
            # Fall back to 'generate' method (custom implementation)
            elif hasattr(self.llm, 'generate'):
                return self.llm.generate(prompt)
            else:
                raise AttributeError("LLM object has neither 'invoke' nor 'generate' method")
        except Exception as e:
            logger.error(f"Error generating response from LLM: {e}")
            return f"Error: {str(e)}"


class RetrievalStrategySelector:
    """
    A selector that chooses the most appropriate retrieval strategy for a given query.
    """
    
    def __init__(
        self, 
        driver: Driver, 
        llm: Any,
        embeddings_provider: Optional[Any] = None,
        retrievers: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the strategy selector.
        
        Args:
            driver: Neo4j driver instance
            llm: LLM instance for strategy selection
            embeddings_provider: Optional provider for generating embeddings
            retrievers: Optional dictionary of retriever instances
        """
        self.driver = driver
        self.llm = llm
        self.embeddings_provider = embeddings_provider
        
        # Initialize retrievers if not provided
        self.retrievers = retrievers or {
            "multihop": MultihopRetriever(driver, llm),
            "parent_child": ParentChildRetriever(driver, llm),
            "hypothetical_question": HypotheticalQuestionRetriever(driver, llm)
        }
        
        # Add hybrid retriever if embeddings provider is available
        if embeddings_provider:
            self.retrievers["hybrid"] = HybridRetriever(driver, llm, embeddings_provider)
        
        logger.info(f"Initialized RetrievalStrategySelector with strategies: {list(self.retrievers.keys())}")
    
    def _select_strategy(self, query: str) -> str:
        """
        Select the most appropriate retrieval strategy for a query.
        
        Args:
            query: The natural language query
            
        Returns:
            The name of the selected strategy
        """
        # Prompt the LLM to classify the query
        prompt = """Based on the following query, determine the most appropriate retrieval strategy from the options below:

1. text2cypher - Simple queries that can be translated directly to Cypher
2. hybrid - Queries requiring both semantic similarity and graph traversal
3. multihop - Complex queries requiring multiple steps of reasoning
4. parent_child - Queries about hierarchical relationships between elements
5. hypothetical - Queries that may benefit from hypothetical questions about element types

Query: """
        prompt += query
        prompt += "\n\nStrategy (just return the name, e.g. 'text2cypher'):"
        
        # Use the LLM to determine the strategy
        response = self._llm_generate(prompt)
        
        # Parse the response to extract the strategy name
        strategy = response.strip().lower()
        
        # Extract just the strategy name if the LLM included additional text
        for known_strategy in ["text2cypher", "hybrid", "multihop", "parent_child", "hypothetical"]:
            if known_strategy in strategy:
                strategy = known_strategy
                break
        
        # Default to text2cypher if no valid strategy was found
        if strategy not in self.retrievers:
            logger.warning(f"Unknown strategy '{strategy}', defaulting to text2cypher")
            strategy = "text2cypher"
            
        logger.info(f"Selected '{strategy}' strategy for query: {query}")
        return strategy
    
    def retrieve(self, query: str) -> Dict[str, Any]:
        """
        Execute retrieval using the most appropriate strategy.
        
        Args:
            query: The natural language query
            
        Returns:
            The results from the selected retriever
        """
        # Step 1: Select the most appropriate strategy
        strategy = self._select_strategy(query)
        
        # Step 2: Retrieve using the selected strategy
        if strategy in self.retrievers:
            retriever = self.retrievers[strategy]
            logger.info(f"Using {strategy} retriever for query: {query}")
            return retriever.retrieve(query)
        else:
            logger.error(f"Unknown strategy: {strategy}")
            return {
                "query": query,
                "error": f"Unknown strategy: {strategy}",
                "strategy": "unknown"
            } 