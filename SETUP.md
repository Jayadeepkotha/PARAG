# Permission-Aware RAG: Setup & Installation Guide (`SETUP.md`)

This guide provides clear, step-by-step instructions to clone, configure, provision, and run the **Permission-Aware RAG (PARAG)** system on your local machine from scratch.

---

## 📋 1. Prerequisites

Before starting, ensure you have the following installed and configured:

1. **Python 3.10 or 3.11** (64-bit). Verify with:
   ```bash
   python --version
   ```
2. **Git** installed on your system.
3. **Amazon Web Services (AWS) Account**:
   - An IAM User with programmatic access (`AWS_ADMIN_ACCESS_KEY` and `AWS_ADMIN_SECRET_KEY`).
   - Permissions: `AmazonS3FullAccess` and `IAMFullAccess`.
4. **Google Cloud Platform (GCP) Account**:
   - A GCP Project with billing enabled.
   - APIs Enabled: **Cloud Storage API** and **Identity and Access Management (IAM) API**.
   - A Service Account with **Storage Admin** and **Security Admin** (or **Owner**) roles.
   - Downloaded Service Account JSON Key file.
5. **Google Gemini API Key**:
   - Obtain a free API key from [Google AI Studio](https://aistudio.google.com/).

---

## 📥 2. Clone the Repository

Clone your repository and navigate into the project root directory:

```bash
git clone https://github.com/Jayadeepkotha/PARAG.git
cd PARAG
```

---

## 🐍 3. Create & Activate Virtual Environment

### On Windows (PowerShell):
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```
*(If PowerShell displays an execution policy error, run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` once, then re-run).*

### On Linux / macOS (Bash / Zsh):
```bash
python3 -m venv venv
source venv/bin/activate
```

---

## 📦 4. Install Dependencies

Upgrade `pip` and install all required Python packages from `requirements.txt`:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> **Note on FAISS:** `requirements.txt` installs `faiss-cpu`, which requires no specialized GPU hardware and runs natively on Windows, macOS, and Linux.

---

## 🔑 5. Environment & Credentials Configuration

### Step 5.1: Create your `config/.env` file
The repository includes a ready-to-use template: [`.env.example`](.env.example). Copy it to `config/.env`:

```bash
# On Windows PowerShell
Copy-Item .env.example config\.env

# On Linux / macOS
cp .env.example config/.env
```

### Step 5.2: Populate Your Active Credentials
Open `config/.env` in your code editor and fill in your actual credentials:

```dotenv
# =============================================================================
# 1. GOOGLE CLOUD PLATFORM (GCP)
# =============================================================================
GCP_PROJECT_ID=your-actual-gcp-project-id
GCP_BUCKET_LOCATION=asia-south1
GCP_ADMIN_KEY_PATH=config/your_gcp_service_account_key.json

# =============================================================================
# 2. AMAZON WEB SERVICES (AWS)
# =============================================================================
AWS_REGION=ap-south-1
AWS_ADMIN_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE
AWS_ADMIN_SECRET_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY

# =============================================================================
# 3. LLM INFERENCE
# =============================================================================
GOOGLE_GEMINI_API_KEY=AIzaSyYourActualGeminiApiKey

# =============================================================================
# 4. IDENTITY PROVIDER (IdP) MODE
# =============================================================================
AUTH_MODE=static
```

### Step 5.3: Place Your GCP JSON Key File
Copy your downloaded GCP Service Account JSON key into the `config/` directory (e.g. `config/Permission_Aware_Rag_GCP_ADMIN_KEY.json`) and make sure `GCP_ADMIN_KEY_PATH` in `config/.env` points to its exact path.

> [!NOTE]
> `config/.env` and `*.json` key files are strictly git-ignored by [`.gitignore`](.gitignore) and will never be pushed to your repository.

---

## 📊 6. Benchmark Dataset Verification

The system includes a pre-filtered multi-hop benchmark dataset located at:
```text
artifacts/hotpot_dev_distractor_v1.json
```
If you ever need to re-download the official HotpotQA distractor dataset manually, run:
```bash
curl -Lo artifacts/hotpot_dev_distractor_v1.json https://hotpotqa.s3.amazonaws.com/hotpot_dev_distractor_v1.json
```

---

## 🚀 7. Running the Ingestion Pipeline

You can provision the cloud storage buckets and build the dual vector indices in **two ways**:

### Option A: One-Click Web UI Execution (Recommended)
1. Start the web application:
   ```bash
   python app.py
   ```
2. Open your browser to `http://127.0.0.1:8000`.
3. In the default **"Dataset & Ingestion"** tab, click the dark blue button:
   **`Execute Multi-Cloud Ingestion Pipeline`**
4. A real-time live progress bar will show the stages (01 to 07) executing:
   * **Stage 1:** Synthesizing access model (`artifacts/generated_access_model.json`)
   * **Stage 2:** Provisioning 5 AWS S3 buckets + 5 GCP GCS buckets with IAM credentials
   * **Stage 3 & 4:** Partitioning documents and uploading them to S3 and GCS
   * **Stage 5 & 6:** Emitting user-accessible ground-truth and golden questions
   * **Stage 7:** Building FAISS vector store, BM25 index, and metadata database.

---

### Option B: Command-Line Stage-by-Stage Execution
If you prefer running the pipeline via terminal scripts:

```bash
# Stage 1: Generate Access Model
python scripts/01_generate_access_model.py

# Stage 2: Provision Cloud Buckets & IAM Personas
python scripts/02_gcp_aws_resource_creator.py --auth_mode static

# Stage 3: Prepare and Slice Multi-Hop Documents
python scripts/03_prepare_documents.py

# Stage 4: Upload Partitioned Documents to AWS S3 & GCP GCS
python scripts/04_upload_resources.py

# Stage 5: Generate Ground-Truth User Visibility Lists
python scripts/05_generate_user_accessible_file_list.py

# Stage 6: Generate Golden Evaluation Questions
python scripts/06_generate_question_list.py

# Stage 7: Build FAISS Dense + BM25 Sparse Indices
python scripts/07_run_ingestion_manager.py
```

---

## 🖥️ 8. Launching the Web Interface

Run the application:
```bash
python app.py
```
You will see:
```text
========================================================
  PERMISSION-AWARE RAG: HCI WEB INTERFACE RUNNING
  Local URL: http://127.0.0.1:8000
========================================================
```
Open **`http://127.0.0.1:8000`** in your browser (Google Chrome, Microsoft Edge, or Mozilla Firefox).

---

## 🔍 9. Sanity Check & Verification

To verify that your local instance is 100% operational, open a second terminal and query the system health endpoint:

```bash
# Windows PowerShell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/status"

# Linux / Mac
curl http://127.0.0.1:8000/api/status
```

Expected JSON response:
```json
{
  "status": "online",
  "is_ready": true,
  "indices": {
    "bm25": true,
    "faiss": true,
    "metadata": true
  },
  "dataset": {
    "loaded": true,
    "question_count": 5
  }
}
```

---

## 🛠️ 10. Common Troubleshooting & Solutions

### 1. Windows SQLite File Lock (`[WinError 32]`)
* **Symptom:** `The process cannot access the file because it is being used by another process: 'artifacts\metadata.db'` when clicking Re-ingest.
* **Solution:** This is already fixed in [`src/managers/ingestion_manager.py`](src/managers/ingestion_manager.py) by utilizing transactional `DROP TABLE IF EXISTS metadata;` instead of raw `os.remove()`, allowing Flask read handles to coexist safely.

### 2. Gemini `429 RESOURCE_EXHAUSTED` / High Latency
* **Symptom:** Generating answer takes 20+ seconds or fails with quota errors.
* **Solution:** In [`config/models.ini`](config/models.ini), ensure `model_1 = gemini-3.5-flash` (which has high free-tier rate limits and 3–4s latency) rather than `gemini-3.8-flash`.

### 3. AWS Cross-Region S3 Redirects
* **Symptom:** AWS permission checks take 5+ seconds.
* **Solution:** In `config/.env`, explicitly set `AWS_REGION=ap-south-1` (or your actual bucket region) so boto3 connects directly without cross-region routing.

### 4. Teardown / Clean Slate
* **Symptom:** You want to switch AWS accounts or delete all test buckets from the cloud.
* **Solution:** Click **"Clear Pipeline (Execute Teardown Sequence)"** on the *Dataset & Ingestion* tab, or run:
  ```bash
  python scripts/ops/teardown_all.py
  ```
  This tears down cloud buckets, IAM policies, and wipes local indices for a clean slate.
