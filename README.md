# InstruCoT

This repository contains the official implementation of the paper **"Know Thy Enemy: Securing LLMs Against Prompt Injection via Diverse Data Synthesis and Instruction-Level Chain-of-Thought Learning"**.

## Overview

Large language model (LLM)-integrated applications have become increasingly prevalent, yet face critical security vulnerabilities from **prompt injection (PI) attacks**. Defending against PI attacks faces two major issues:

1. **Multi-Vector Injection**: Malicious instructions can be injected through diverse vectors (user input, environment, memory, retrieved data)
2. **Ambiguous Semantic Boundaries**: Injected instructions often lack clear semantic boundaries from the surrounding context, making them difficult to identify

To address these issues, we propose **InstruCoT**, a model enhancement method for PI defense that synthesizes diverse training data and employs instruction-level chain-of-thought fine-tuning, enabling LLMs to effectively identify and reject malicious instructions regardless of their source or position in the context.

![Method Overview](https://github.com/lsplx/InstruCoT-LLM/blob/main/fig/method_overview.png?raw=true)

We evaluate InstruCoT across three critical dimensions: **Behavior Deviation**, **Privacy Leakage**, and **Harmful Output**. Experimental results across four LLMs demonstrate that InstruCoT significantly outperforms baselines in all dimensions while maintaining utility performance without degradation.

## Violation Pattern Taxonomy

Our framework categorizes prompt injection attacks into three main categories:

### Behavior Deviation

| Level | Name | Description |
|-------|------|-------------|
| Level 1 | Same Domain, Related Topic | Boundary case requests that seem reasonable but exceed defined responsibilities |
| Level 2 | Same Domain, Unrelated Topic | Content completely unrelated to core responsibilities |
| Level 3 | Different Domain, Related Topic | Cross-domain questions with weak relevance |
| Level 4 | Different Domain, Unrelated Topic | Entirely irrelevant requests |

### Privacy Leakage

- System prompt extraction attempts
- Personal identifiable information (PII) requests
- Confidential business data extraction
- Internal configuration leakage

### Harmful Output

Covers 13 safety categories: Illegal Activity, Hate Speech, Malware Generation, Physical Harm, Economic Harm, Fraud, Pornography, Political Lobbying, Privacy Violation, Legal Opinion, Financial Advice, Health Consultation, and Government Decision.

## Dataset

The generated instruction-level CoT dataset is available in the `data/` directory. The dataset contains training samples with chain-of-thought annotations for prompt injection defense. We will release the full dataset upon the completion of the review process.

## Code Description

### PI_generation.py

This script generates diverse prompt injection samples across all violation patterns.

**Features:**
- Generates injections for 6 violation types (4 Behavior Deviation levels + Privacy Leakage + Harmful Output)
- Automatically saves results incrementally to prevent data loss
- Supports custom input/output file paths

**Usage:**
```bash
python PI_generation.  
python CoT_generation.py
