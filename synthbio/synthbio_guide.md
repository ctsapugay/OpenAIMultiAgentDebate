# SynthBio Dataset Guide

## What the Dataset Is

SynthBio is a synthetic, human-edited dataset created as a clean,
unbiased evaluation set for the WikiBio structure-to-text task. Instead
of using real individuals (which leads to memorization, bias, and
contamination in LLMs), SynthBio contains **fictional people** with
human-revised attribute lists (infoboxes) and multiple biographies per
individual.

### Key Goals

-   Avoid memorization of real-world facts by LLMs\
-   Reduce noise and hallucinations in reference data\
-   Improve balance across gender and nationality\
-   Provide multiple references per input\
-   Enable testing of grounded, faithful text generation

### Dataset Scale

-   **2,249** fictional individuals
-   **4,692** biography references
-   **\~2.1 biographies per infobox**

------------------------------------------------------------------------

## Dataset Structure

The dataset is released as a JSON file.\
Each entry corresponds to one fictional person and contains:

``` json
{
  "attributes": {
    "name": "Example Name",
    "gender": "female",
    "nationality": "Canadian",
    "birth_date": "12 March 1965",
    "birth_place": "...",
    "occupation": "...",
    "field_or_notability_specific_attributes": "...",
    ...
  },
  "biographies": [
    "Biography text version 1",
    "Biography text version 2",
    ...
  ]
}
```

### 1. **Attributes (Infobox)**

These are structured fields describing the fictional person. They come
from: - Templates (gender, nationality, birth date) - LLM-generated
fields (birth place, education, parents, partner, occupation details) -
Notability-specific fields (instrument for musicians, sport for
athletes, etc.) - Human revision ensuring: - factual plausibility\
- proper Wikipedia-style formatting\
- no contradictions\
- removal of hallucinated content

### 2. **Biographies (Natural Language Text)**

For each infobox: - An LLM generates **three** biographies - A human
editor revises them for: - **faithfulness** (must reflect only the
infobox attributes) - **fluency** - **formatting** - removing
hallucinations or invented details

Biographies are typically short paragraphs wrapped in `{}`.

------------------------------------------------------------------------

## How to Use SynthBio

### 1. **Evaluate a structure-to-text model**

This is the primary purpose.\
Given structured attributes → generate a biography.

SynthBio is ideal for evaluation because: - No contamination (the people
do not exist) - Less noise than WikiBio - Multiple references per input
allow robust comparisons - Balanced demographics help fairness testing

Typical evaluation metrics: - **PARENT** (precision, recall, F)\
- **BLEURT** / **BLEURT-20**\
- **ROUGE-L**

### 2. **Test hallucination resistance**

Because biographies must strictly match the infobox: - Models cannot
rely on real-world priors - Hallucinated details lower scores - Perfect
for grounded text-generation testing

### 3. **Generalization testing**

Includes both: - Common occupations (musician, scientist) - Rare
occupations (spy, mountaineer, theologian)

Great for analyzing: - long-tail schema robustness\
- attribute coverage

### 4. **Fairness and bias analysis**

The dataset intentionally balances: - gender\
- nationality\
- notability types

It allows: - measuring performance across demographic attributes\
- testing for distribution-sensitive behavior

### 5. **Multi-reference training or evaluation**

Each infobox has on average 2.1 biographies.\
Useful for: - non-deterministic generation evaluation\
- training models to handle stylistic variation

------------------------------------------------------------------------

## Example Workflow for a Coding Agent

### Step 1: Load the JSON

``` python
import json

with open("SynthBio.json", "r") as f:
    data = json.load(f)
```

### Step 2: Access attributes and biographies

``` python
item = data[0]
attributes = item["attributes"]
biographies = item["biographies"]
```

### Step 3: Feed attributes into your model

``` python
generated_bio = model.generate(attributes)
```

### Step 4: Evaluate generated biography

Compute metrics like: - ROUGE-L - BLEURT - PARENT

### Step 5: Use multiple references if needed

``` python
for ref in biographies:
    score = metric(generated_bio, ref)
```

------------------------------------------------------------------------

## Summary

The SynthBio dataset is: - synthetic but human-edited\
- more balanced and faithful than WikiBio\
- ideal for testing grounded generation\
- structured as JSON with infobox + multiple biographies

It is a strong evaluation benchmark for any system converting structured
data to natural language text.
