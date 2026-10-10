# Project Apollo Architecture & Technical Guidelines
Version: 1.0
Author: Infrastructure Team
Date: 2026-10-01

## 1. System Overview
Project Apollo is a distributed vector processing microservice architecture. 
All vector store instances must persist embeddings to resilient disk volumes. 
The vector store handles high-throughput similarity search queries across billions of embeddings.

## 2. Milestone Deadlines & Schedules
The deployment deadline is 15 November.
All team members must finalize infrastructure validation by this date.
Production freeze begins on 10 November.

## 3. Technology Stack & Security
Apollo uses PostgreSQL with pgvector for persistent document metadata and dense vector indexing.
Hybrid retrieval is mandatory, combining semantic similarity and lexical BM25 token matching.
Direct prompt injections must be neutralized by isolating retrieved context inside strict structural boundaries.
