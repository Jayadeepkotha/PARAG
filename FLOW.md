# Permission-Aware RAG: Comprehensive UI & Feature Flow Guide (`FLOW.md`)

This guide is a complete visual and operational walkthrough of the **Permission-Aware RAG (PARAG)** Web Dashboard. It details every interactive card, button, telemetry metric, and test scenario.

---

## 🧭 Navigation Overview

The web dashboard is organized into **5 primary tabs** accessible from the top navigation bar:

```
[ Dataset & Ingestion ]  [ Pipeline Config & Operations ]  [ Query & Audit ]  [ Evaluation Matrix ]  [ Concepts & Architecture ]
```

---

## 🗂️ TAB 1: Dataset & Ingestion Center

The **Dataset & Ingestion** view is the control room for benchmark datasets, identity provider bridging, cloud storage topologies, and dual-index orchestration.

```
+---------------------------------------+-------------------------------------------------------+
| LEFT COLUMN (Ingestion Controls)      | RIGHT COLUMN (Cloud Storage & IAM Topology)           |
+---------------------------------------+-------------------------------------------------------+
| 1. Active Benchmark Dataset Card      | Multi-Cloud Storage & IAM Access Topology Inspector   |
| 2. Upload HotpotQA Benchmark Dropzone | - Amazon Web Services (S3) [5 Buckets + ABAC Tags]    |
| 3. Identity & Access Provider (IdP)   | - Google Cloud Platform (GCS) [5 Buckets + RBAC Roles]|
| 4. Execution & Teardown Action Card   | Dual-Index Architecture Breakdown (Stages 01-07)      |
+---------------------------------------+-------------------------------------------------------+
```

### Key Elements & How to Use Them:

1. **Active Benchmark Dataset Card**:
   * Displays the current active dataset (`hotpot_dev_distractor_v1.json`), question count ($5$ multi-hop pairs), and cloud topology ($10$ buckets).
2. **Upload HotpotQA JSON Benchmark**:
   * Drag-and-drop zone to load custom benchmark files. Automatically validates required JSON keys: `_id`, `question`, `answer`, `context`, and `supporting_facts`.
3. **Identity & Access Provider (IdP) Mode**:
   * **`Auth0 Enterprise (OIDC + STS)`**: Uses Auth0 JWT bearer tokens federated via AWS STS AssumeRoleWithWebIdentity and GCP Workload Identity Federation.
   * **`Static IAM (Permanent Keys)`**: Uses native AWS IAM User credentials and GCP Service Account keys.
4. **Execute Multi-Cloud Ingestion Pipeline**:
   * Orchestrates **Stages 01 through 07** with a live progress bar showing elapsed seconds and active stage description:
     * *Stage 1:* Access model generation
     * *Stage 2:* Cloud bucket provisioning & IAM policies
     * *Stage 3 & 4:* Document chunking & multi-cloud upload
     * *Stage 5 & 6:* Visibility ground-truth & question benchmark
     * *Stage 7:* Dense FAISS + Sparse BM25 + SQLite metadata build.
5. **Clear Pipeline (Execute Teardown Sequence)**:
   * Safety teardown: Deletes cloud buckets, cleans up IAM roles, and resets local indices for a fresh test cycle.
6. **Multi-Cloud Storage & IAM Access Topology Inspector**:
   * Shows all $10$ provisioned buckets in real time ($5$ AWS S3 with ABAC tags `attribute_a`, `attribute_b`, etc., and $5$ GCP GCS with RBAC roles `role_read_gcp_bucket_1-5`) and live document counts per bucket.

---

## ⚙️ TAB 2: Pipeline Config & Operations

This view controls runtime performance optimizations, caching, and real-time cloud data drift detection.

### 1. In-Memory Permission Cache (Unix TTL)
* **Decision Caching Toggle**: Enables or disables in-memory caching of cloud IAM verdicts.
* **Telemetry Counters**:
  * **HITS**: Number of permission checks resolved instantly from cache.
  * **MISSES**: Number of checks that required live cloud network calls.
  * **HIT RATIO**: Percentage of queries served from memory.
  * **SPEED**: Average retrieval speed ($\approx \mathbf{0.05\text{ ms}}$ for cached checks vs $1500\text{–}3000\text{ ms}$ for cold cloud calls).
* **Flush All Cache**: Instantly clears all cached verdicts.
* **Evict User**: Granular dropdown (e.g. `user-1 (Restricted)`) to invalidate only a specific user's cached permissions without affecting other personas.

### 2. Multi-Cloud Event Drift Queues
* **AWS S3 – SQS (`drift-queue`)**: Binds AWS SQS to S3 `ObjectCreated` and `ObjectRemoved` bucket events.
* **GCP GCS – Pub/Sub (`drift-sub`)**: Subscribes to Google Cloud Storage object change notifications.
* **`Deploy Queues` / `Destroy All`**: One-click provisioning and cleanup of cloud queues.

### 3. Real-Time Drift Listener Daemon & Streaming Console
* **`Start Listener Daemon`**: Launches an asynchronous background daemon that polls AWS SQS and GCP Pub/Sub.
* **Provider Selector**: Filter events by `Unified Multi-Cloud`, `AWS S3 Only`, or `GCP GCS Only`.
* **Streaming Terminal Console**: Displays real-time JSON event packets whenever a file is uploaded, modified, or deleted in any S3 or GCS bucket, followed by automatic index synchronization.

---

## 🔍 TAB 3: Query & Audit Studio

The **Query & Audit Studio** is where you test interactive retrieval, examine IAM filtering in real time, and inspect LLM answers.

```
+-------------------------------------------------------------------------------------------------+
| PROGRESSIVE STEPPER: [1. Multi-Hop Retrieval] ---> [2. IAM Authorization] ---> [3. Grounded Synthesis] |
+---------------------------------------------+---------------------------------------------------+
| PINNED CONTROLS:                            | ANSWER & GROUNDING VIEWPORT:                      |
| [Restricted: 0%] [Dept: 16%] [Admin: 100%]   | - Grounded Output ("I don't know." / Answer)      |
| [Hybrid (RRF) | FAISS]  Top-K: [----O] 5    | - Gold Reference & EM/F1 Score Pills              |
|                                             |                                                   |
| 2. BENCHMARK GOLDEN QUESTIONS:              | RETRIEVED DOCUMENTS LEDGER:                       |
| [Q1: Malaria / Artemisinin Clinical Trial]  | #1 doc_id_535.txt [AWS Bucket-2] [Allowed/Blocked]|
| [Q2: Genentech / RAG Repository]            | #2 doc_id_531.txt [AWS Bucket-1] [Allowed/Blocked]|
| [Q3: NASA Ames Helicopter on Mars]          | ...                                               |
| 3. CUSTOM QUESTION INPUT & [GENERATE]       |                                                   |
+---------------------------------------------+---------------------------------------------------+
```

### Walkthrough of Features:

1. **System Stepper Bar**:
   * Shows execution timing for each stage:
     * **Multi-Hop Retrieval:** Dense vector cosine + BM25 score fusion ($15\text{–}35\text{ms}$).
     * **IAM Authorization:** Cloud IAM security check or cache resolution ($0.05\text{ms}$ on hit).
     * **Grounded Synthesis:** Gemini LLM answer generation ($2.5\text{–}4.0\text{s}$).

2. **Pinned Persona Clearance Selector**:
   * **Restricted ($0\%$ Access):** Blocked from all S3 and GCS buckets.
   * **Departmental ($16\%$ Access):** Permitted to access Bucket 1 only.
   * **Admin ($100\%$ Access):** Unrestricted access across all $10$ cloud buckets.
   * *Permanently pinned at the top: Never scrolls away.*

3. **Search Mode & Top-K Slider**:
   * **`Hybrid (RRF)`**: Combines semantic embeddings with BM25 keyword rankings. Best for questions with exact IDs (e.g. PMID numbers).
   * **`FAISS`**: Pure cosine similarity vector search.
   * **`Top-K`**: Adjust candidates retrieved from $1$ to $10$.

4. **Benchmark Golden Questions**:
   * Click any question chip (Q1 to Q5) to populate the query box instantly:
     * **Q1:** *Medical registry identifier (PMID) for phytochemical synergy against malaria...*
     * **Q2:** *Organization whose GitHub repository hosts RAG code for Nobel chemist...*
     * **Q3:** *Research center collaborating on Mars helicopter and country of research...*
     * **Q4:** *Institution awarding prize shared in 2015 by artemisinin discoverer...*
     * **Q5:** *Geographic region of sweet wormwood and NASA Perseverance program...*

5. **Security Audit Ledger (Retrieved Documents)**:
   * Displays every candidate document retrieved from the index with:
     * Document ID & Rank
     * Score & Method (`Hybrid RRF` or `FAISS Cosine`)
     * **Supporting Document Badge** (indicates if this document contains necessary facts)
     * **Storage Source:** Pinpoints the exact cloud bucket (e.g. `vcsuqmpi-aws-bucket-2 (AWS)`)
     * **IAM Verdict Badge:**
       * 🟢 `Allowed by IAM`: User has verified clearance; document is admitted to LLM context.
       * 🟠 `Blocked by IAM`: User lacks clearance; document is purged before synthesis.

---

## 📈 TAB 4: Evaluation Matrix

The **Evaluation Matrix** tab presents quantitative validation of security and accuracy across all test personas:

* **Mode:** Retrieval technique (`Hybrid` or `FAISS`).
* **User ID:** Identity persona (`Restricted`, `Departmental`, `Admin`).
* **Permission Coverage:** Proportion of total cloud storage accessible to this persona.
* **Security Match:** Percentage of unauthorized documents successfully blocked (**$100\%$ across all personas**).
* **Exact Match (EM) & F1 Score:** String similarity and token overlap against the gold standard answer.
* **EM@Admin:** Baseline accuracy when the user has full clearance.
* **Docs Auth / Retr:** Ratio of documents authorized vs retrieved.

---

## 🧠 TAB 5: Concepts & Architecture Hub

An educational reference hub detailing the underlying mathematics and HCI principles:

1. **Retrieval Scoring & Mathematical Caps**:
   * **FAISS Cosine Similarity:** Measures angular proximity in $384$-dimensional embedding space. $\text{Cap} = 1.000$.
   * **Hybrid RRF Fusion:** Sums reciprocal ranks across FAISS and BM25:
     $$\text{RRF}(d) = \sum_{m} \frac{1}{60 + \text{rank}_m(d)}$$
     Theoretical maximum score for a document ranked #1 in both is $\frac{1}{61} + \frac{1}{61} \approx \mathbf{0.0328}$.
2. **Multi-Hop Reasoning Pathways**:
   * Interactive SVG diagram demonstrating how multi-hop queries bridge facts across disjoint documents (Bridge Fact $\rightarrow$ Target Fact $\rightarrow$ Grounded Synthesis).
3. **IAM Zero-Leak Enforcement Mechanics**:
   * Explains how pre-synthesis document purging prevents prompt injection or inference leakage.

---

## 🧪 Recommended Test Scenarios

Try these $3$ quick experiments in the **Query & Audit** tab to see PARAG in action:

### Scenario 1: Zero-Leak Security Enforcement
1. Select **Restricted Persona** ($0\%$ Access).
2. Click **Question Q1** (*"What is the medical registry identifier (PMID)..."*).
3. Click **Generate LLM Response**.
4. **Observe:**
   * Both supporting documents (`doc_id_531.txt` and `doc_id_535.txt`) are tagged with 🟠 **`Blocked by IAM`**.
   * Grounded Output displays: **`"I don't know."`**
   * Status Badge: **`Blocked by IAM (Zero Leaks)`**.
   * **Result:** Even though the documents contained the exact answer (`PMID: 42596018`), the LLM was physically denied access to the text.

### Scenario 2: Grounded Multi-Hop Synthesis
1. Select **Admin Persona** ($100\%$ Access).
2. Click **Question Q1** and click **Generate LLM Response**.
3. **Observe:**
   * Supporting documents are tagged with 🟢 **`Allowed by IAM`**.
   * Grounded Output displays: **`"42596018"`** or **`"PMID: 42596018"`**.
   * Status Badge: **`Allowed Grounded`**.
   * Metrics: **`EM: 1.00 | F1: 1.00`**.

### Scenario 3: Sub-Millisecond Permission Caching
1. Go to **Pipeline Config & Operations** and verify **Decision Caching** is toggled **Enabled**.
2. Return to **Query & Audit** and run Question Q1 as **Admin**.
   * Notice Stepper Step 2 (IAM Authorization) takes $\approx 1500\text{–}2500\text{ms}$ on the initial cold run.
3. Immediately click **Generate LLM Response** again with the same question.
   * **Observe:** Stepper Step 2 takes **$0\text{ ms}$**!
   * A green badge appears: `⚡ Cache: HIT (0 ms)`.
   * Check **Pipeline Config & Operations** to see the `HITS` counter increment.
