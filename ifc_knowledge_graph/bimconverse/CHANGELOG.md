# Changelog

All notable changes to the BIMConverse project will be documented in this file.

## [2.0.0] - 2023-07-15

### Added
- Multi-hop reasoning capability for complex queries
  - MultihopRetriever class that breaks down complex queries into simpler sub-queries
  - Automatic detection of queries that may benefit from multi-hop reasoning
  - Configuration options for multi-hop settings
  - CLI commands for controlling multi-hop behavior
  - Special query prefixes for forcing retrieval strategies
  - Test script for demonstrating multi-hop functionality
- Enhanced prompt templates for different reasoning strategies
  - Multi-hop reasoning prompt
  - Spatial reasoning prompt
  - Parent-child retrieval prompt
  - Step-back prompt
- Updated CLI interface with new commands and options
- Expanded documentation in README.md
- New retrieval results format that includes retrieval strategy and metadata 