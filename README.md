# **ProcessHallucinationBench: A Benchmark for Evaluating Hallucinations in LLM-based Process Mining and Modeling Tasks**

## Current Leaderboard

Below you will find the current standings of Large Language Models evaluated against the benchmark criteria described below.
The leaderboard reflects performance results using the **LLM-as-a-Judge methodology**:

* [grok-4.3 used as the Judge](leaderboard_grok43.md)

## Motivation

Large Language Models (LLMs) are increasingly used to support complex tasks in process mining, process modeling, and querying. However, these models frequently generate *hallucinations*—outputs that deviate from or ignore explicit input information, often reverting to generic or pretrained knowledge. Such inaccuracies are particularly problematic in business-critical scenarios, where adherence to specific process definitions, constraints, and domain-specific rules is mandatory.

### Purpose of this Benchmark

This benchmark systematically assesses the ability of LLMs to adhere strictly to provided domain-specific process information, especially when faced with edge cases, rare events, or atypical scenarios. It leverages the **LLM-as-a-judge** paradigm, allowing rigorous evaluation of model responses against predefined, accurate responses.

## Benchmark Categories Overview

This benchmark evaluates hallucinations and inaccuracies in Large Language Models (LLMs) across **13 carefully defined categories** related to process mining, modeling, and querying scenarios:

* **01. Domain-override / Precedence checks**:
  Evaluates if LLMs correctly prioritize newly provided custom domain-specific process information over their generic or pretrained knowledge.

* **02. Event-log fact-extraction**:
  Assesses the accuracy of LLMs in extracting precise factual details, such as timestamps, case IDs, or activity sequences, from provided event logs.

* **03. Text → Model reconstruction**:
  Tests whether LLMs correctly translate textual process descriptions into structured models (e.g., BPMN, Petri nets) without introducing additional or missing elements.

* **04. Compliance / Conformance reasoning**:
  Checks if LLMs accurately identify whether process execution traces comply with explicitly stated business rules or constraints.

* **05. Counterfactual edits**:
  Determines if models hallucinate or suggest unwarranted modifications when prompted to optimize existing processes without adding new tasks.

* **06. Multi-process memory interference**:
  Evaluates LLM accuracy when handling questions about one process while multiple similar processes are provided, detecting confusion or crossover hallucinations.

* **07. Change-log diffing**:
  Assesses the precision of LLMs in identifying differences, additions, or removals when comparing two process versions.

* **08. Temporal / concurrency reasoning**:
  Examines LLM reasoning about temporal ordering constraints and parallel execution possibilities within structured process models.

* **09. "Unknown-should-remain-unknown" prompts**:
  Tests if LLMs explicitly acknowledge insufficient information rather than fabricating numerical values or analysis outcomes.

* **10. Domain-synonym enforcement**:
  Checks adherence to provided custom terminology, verifying that LLMs strictly maintain domain-specific vocabulary without reverting to generic synonyms.

* **11. Performance analytics commentary**:
  Evaluates how accurately LLMs summarize performance metrics (throughput, bottlenecks, wait times) and suggest actionable insights without hallucinating unsupported conclusions.

* **12. Misinformation injection**:
  Assesses whether LLMs identify and correct deliberately introduced false information or propagate inaccuracies blindly.

* **13. Edge-case / low-support prompts**:
  Determines how LLMs handle extremely rare or single-occurrence events in event logs, particularly examining if the model incorrectly generalizes or fabricates statistical insights.

Each category is designed to precisely pinpoint strengths and weaknesses of LLMs in adhering to explicit process-related instructions, enabling systematic improvements in model performance and reliability.

| Cat.                                      | **Input Artifact**                 | **Expected Output**                 | **Primary Skill Stressed**                   | **Hallucination Mode Under the Microscope**                | **Instruction-Following Stressor**  | **Context Complexity** |
| ----------------------------------------- | ---------------------------------- | ----------------------------------- | -------------------------------------------- | ---------------------------------------------------------- | ----------------------------------- | ---------------------- |
| **C01** Domain-override / Precedence      | Custom textual process description | Summary & list                      | *Instruction override* (align with new info) | Prior-knowledge **fabrication** (“textbook” tasks leak in) | **High** – must ignore pre-training | Single process         |
| **C02** Event-log fact-extraction         | Raw event-log lines                | Concrete facts (counts, IDs)        | *Extraction & grounding*                     | Fabricating numeric facts / IDs                            | Medium                              | Single                 |
| **C03** Text → Model reconstruction       | Free-text narrative                | Structured model (BPMN/Petri)       | *Transformation / generation*                | Extra or missing tasks (fabrication + omission)            | Medium                              | Single                 |
| **C04** Compliance / Conformance          | Rule set + trace                   | Yes/No verdict & rationale          | *Formal reasoning*                           | Spurious violations / compliances                          | Low–Med                             | Single                 |
| **C05** Counterfactual edits              | BPMN XML                           | Improvement suggestion              | *Constrained editing*                        | Adding forbidden elements (fabrication)                    | **High** (explicit “no new tasks”)  | Single                 |
| **C06** Multi-process memory interference | Two+ similar processes             | Answer about **one** process        | *Selective recall / working memory*          | Cross-process mingling                                     | **High**                            | **Multi-process**      |
| **C07** Change-log diffing                | Model v1 & v2                      | Diff report                         | *Comparison*                                 | Missed or phantom deltas                                   | Medium                              | Pairwise comparison    |
| **C08** Temporal / concurrency reasoning  | Petri net / model                  | Reachability explanation            | *Temporal reasoning*                         | Impossible orderings misstated                             | Medium                              | Single                 |
| **C09** Unknown-should-remain-unknown     | Partial info (e.g., header only)   | Admitted uncertainty                | *Uncertainty management*                     | Invented numbers / metrics                                 | **High**                            | Single                 |
| **C10** Domain-synonym enforcement        | Process text + prescribed terms    | RACI / narrative with exact wording | *Terminology adherence*                      | Synonym substitution                                       | **High**                            | Single                 |
| **C11** Performance analytics commentary  | KPI table / CSV                    | Executive memo                      | *Analytic summarization*                     | Bogus bottlenecks or metrics                               | Medium                              | Single                 |
| **C12** Misinformation injection          | Prompt with planted false “fact”   | Fact-check decision                 | *Fact-verification*                          | Blindly echoing falsehood                                  | **High**                            | Single                 |
| **C13** Edge-case / low-support prompts   | Log with rare events               | Counts & caution                    | *Statistical reasoning*                      | Over-generalisation                                        | Medium                              | Single                 |

## Prompt Snippets

The table below lists each prompt in `prompts/`. Newline characters are shown as `\n` for readability.

| Prompt | First 50 chars | Last 50 chars |
| --- | --- | --- |
| `01_01` | <code>System:\nYou are an expert on **Contoso Airlines’ f</code> | <code>tivities or artefacts that are not defined above.\n</code> |
| `01_02` | <code>System:\nYou are an expert on **Acme Bank’s Micro-l</code> | <code>; do **not** introduce standard loan terminology.\n</code> |
| `01_03` | <code>System: You are an expert on **Acme Bank’s SMALL-B</code> | <code>e in the process, in the order they first appear.\n</code> |
| `02_01` | <code>System (hidden from judged model):\nYou are a metic</code> | <code>"&lt;string&gt;", ...]       // unsorted list is fine\n}\n</code> |
| `02_02` | <code>You are given the following fragment of an XES eve</code> | <code>_Order”** (one per line, alphabetically ordered).\n</code> |
| `02_03` | <code>You are an event-log analyst.\n\nBelow is a 10-line </code> | <code>agment?\n\nGive concise, bullet-point answers only.\n</code> |
| `03_01` | <code>You are an expert BPMN modeller.\n\nBelow is a plain</code> | <code> \n✦ No diagram/interchange elements are required.\n</code> |
| `03_02` | <code>System:\nYou are a BPMN-2.0 architect.  \nWhen asked</code> | <code>ser:\nProduce the BPMN diagram in **JSON** format.\n</code> |
| `03_03` | <code>System: You are a business-process architect. Conv</code> | <code>\n• Task names must match the text **verbatim**.  \n</code> |
| `04_01` | <code>System (context)\nYou are a senior process-audit bo</code> | <code>Trace 24-EXP compliant with rule set P2P-2025.R1?\n</code> |
| `04_02` | <code>System (internal auditor): You are auditing Globex</code> | <code>ith the rules? Follow the required answer format.\n</code> |
| `04_03` | <code>System: You are a process-compliance auditor for *</code> | <code>erencing each rule that is satisfied or violated.\n</code> |
| `05_01` | <code>System:\nYou are a certified BPMN 2.0 architect wor</code> | <code> words, and reference element IDs where relevant.\n</code> |
| `05_02` | <code>System:\nYou are a senior process-architecture cons</code> | <code>nitions&gt;\n````\n\nUser:\nSuggest the improvement now.\n</code> |
| `05_03` | <code>System: You are a senior BPMN consultant. \nHere is</code> | <code>he whole model) and a one-sentence justification.\n</code> |
| `06_01` | <code>System (context)\nYou are a senior process-mining a</code> | <code> line, using the format  \n&gt;   `Task_X  —  Task_Y`\n</code> |
| `06_02` | <code>System: You are a senior BPM analyst assisting Con</code> | <code>d exclude any tasks that must run sequentially.  \n</code> |
| `06_03` | <code>System: You are an auditing assistant comparing se</code> | <code>s and give no information about Processes A or C.\n</code> |
| `07_01` | <code>System\nYou are a meticulous BPMN change-log analys</code> | <code> all changes, grouped by the required headings.**\n</code> |
| `07_02` | <code>System (background for judged model):\nYou are a me</code> | <code> **strictly** under the three requested headings.\n</code> |
| `07_03` | <code>System (not shown to the judged model)\nYou are an </code> | <code>e required headings and the concrete differences.\n</code> |
| `08_01` | <code>System: You are a certified Petri-net analyst for </code> | <code> \nIf **no**, give a short proof of impossibility.\n</code> |
| `08_02` | <code>System (context for the model being tested)\nYou ar</code> | <code>e exists.\n\nLimit your explanation to ≤ 120 words.\n</code> |
| `08_03` | <code>System (instruction):\nYou are a Petri-net analyst.</code> | <code>al explanation of why the ordering is impossible.\n</code> |
| `09_01` | <code>System:\nYou are a senior process-performance analy</code> | <code>og above?  \n2 ) Briefly explain your calculation.\n</code> |
| `09_02` | <code>System: You are a senior process-mining analyst au</code> | <code>, reply with one concise sentence explaining why.\n</code> |
| `09_03` | <code>System:\nYou are a certified Process-Mining Expert </code> | <code>ide knowledge.\n\nRespond in plain text, no tables.\n</code> |
| `10_01` | <code>System\n-----\nYou are a senior process-mapping cons</code> | <code>ly adhering to the preferred terminology rules**.\n</code> |
| `10_02` | <code>System:\nYou are a senior process-management consul</code> | <code>ry exactly, and organise the RACI matrix clearly.\n</code> |
| `10_03` | <code>&lt;System&gt;\nYou are NimbusPay’s in-house process-gove</code> | <code>n table; do not rename, merge, or add activities.\n</code> |
| `11_01` | <code>System: You are a senior process-mining analyst hi</code> | <code>----------------------\n\nUser: Draft the memo now.\n</code> |
| `11_02` | <code>### Benchmark Prompt – Category 11: *Performance a</code> | <code>ween candidates, say so rather than guessing.\n```\n</code> |
| `11_03` | <code>System\nYou are Orion Credit’s senior process-perfo</code> | <code>mendations**.  \n4  Return **only** the memo text.\n</code> |
| `12_01` | <code>System:\nYou are a meticulous process-mining analys</code> | <code>tion citing the relevant case IDs and activities.\n</code> |
| `12_02` | <code>System (background for the judged model)\nYou are a</code> | <code>ne paragraph that cites line numbers or case-ids.\n</code> |
| `12_03` | <code>System\nYou are a meticulous process-mining analyst</code> | <code>ting the relevant CaseIDs and activity sequences.\n</code> |
| `13_01` | <code>System:\nYou are a process-analytics assistant. The</code> | <code>-related reasons why that estimate is unreliable.\n</code> |
| `13_02` | <code>System\nYou are a senior process-mining analyst.  Y</code> | <code>nly use the log above; do not invent information.\n</code> |
| `13_03` | <code>System:\nYou are a senior process-mining analyst. A</code> | <code>nual fraud checks are in the full month-long log.\n</code> |

## LLM-as-a-Judge Evaluation Methodology

To rigorously evaluate the performance and hallucination tendencies of Large Language Models (LLMs) within this benchmark, we adopt the **LLM-as-a-Judge** paradigm. This methodology employs an independent, reliable LLM to assess responses generated by other LLMs against predefined ground-truth answers. The evaluation process operates as follows:

1. **Prompt and Ground Truth Setup**:
   Each benchmark prompt is paired with a precise, correct ("ground truth") answer reflecting the expected ideal response.

2. **Evaluation Prompt Structure**:
   The judging LLM is presented with:

   * **The original benchmark prompt** that was posed to the tested LLM.
   * **The tested LLM's answer** to evaluate.
   * **The ground-truth answer**, which serves as the gold-standard reference.

3. **Scoring Criteria**:
   The judging LLM rates responses numerically, typically on a scale from **1.0 (minimum)** to **10.0 (maximum)**, based strictly on fidelity to the provided ground truth. The key aspects influencing scoring include:

   * **Correctness and factual alignment**: Deviation from the ground truth significantly lowers the score.
   * **Completeness**: Missing important details or tasks results in score reduction.
   * **Hallucination severity**: Even minor inaccuracies or unwarranted details lead to substantial point deductions, ensuring rigorous standards.

4. **Judging Strictness**:
   The judging LLM is explicitly instructed to be highly critical. Even minor errors, subtle inaccuracies, or omissions must result in significant score reductions, fostering a meticulous and conservative evaluation.
