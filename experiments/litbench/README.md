# 📘 Multi-Agent Debate System for Creative Writing Evaluation  
**Branch:** `litbench`  
**Last Updated:** November 30, 2025
**Author:** Angela Yu  

---

# Creative Writing Evaluation via Multi-Agent Debate

This branch contains experiments exploring how a **multi-agent debate system** can be used to judge **creative writing quality**, drawing inspiration from evaluation approaches such as **LitBench**, **EQ-Bench**, and recent work on literary reasoning in LLMs.

## Purpose

The objective of this work is to evaluate paired creative writing responses (**Story A** vs. **Story B**) using a structured rubric that focuses on five key dimensions:

- **Originality** – uniqueness of ideas and creative risk-taking  
- **Imagery** – sensory detail and descriptive richness  
- **Emotional Impact** – how strongly the writing affects the reader  
- **Coherence** – clarity, flow, and narrative structure  
- **Technical Skill** – style, language control, and overall craft  

Each agent participating in the debate is instructed to output in the following format:

```text
Reasoning: [your evaluation]
Preferred: [A or B]

---

## ✨ Key Findings (Summary)

1. **Multi-round debate > more agents.**  
   Adding rounds improved stability more than adding additional agents.

2. **Emotionally rich stories consistently win.**  
   Across all experiments, agents preferred stories with relational tension, introspection, or implied conflict — strongly aligning with EQ-Bench patterns.

3. **Medium-length prompts work best.**  
   One-sentence prompts were too shallow for discussion; medium prompts triggered deeper reasoning; huge prompts were too big

4. **System behavior is consistent and interpretable.**  
   Despite variations in agents/rounds, the final results converged almost every time.

---

## 🧪 Experimental Configurations

### Story Pairs  
We tested three categories of prompts:

| Category | Purpose | Benchmark Connection |
|---------|----------|---------------------|
| **One-line hooks** | Test basic debate behavior | LitBench minimal prompts |
| **Medium mystery & introspection** | Evaluate narrative reasoning | LitBench opening-lines |
| **Emotion-driven family & identity prompts** | Evaluate empathy, subtlety | EQ-Bench-style scenarios |

### Debate System Settings

The following configurations were tested:

| Experiment | Prompt Size | Agents | Rounds | Purpose |
|-----------|-------------|--------|--------|---------|
| 1 | Small | 5 | 1 | Validate working pipeline |
| 2 | Medium | 3 | 3 | Compare stability over debate |
| 3 | Medium EQ-style | 2 | 5 | Test emotional sensitivity |

All experiments used **gpt-4o-mini**.

---

## 📂 File Structure

