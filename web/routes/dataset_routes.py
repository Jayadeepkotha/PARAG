# web/routes/dataset_routes.py
# Blueprint for dataset upload, validation, and multi-cloud dual-ingestion execution

import os
import sys
import json
import time
import logging
import subprocess
from flask import Blueprint, request, jsonify
from web.services.pipeline_service import PipelineService
from src.managers.ingestion_manager import IngestionManager

logger = logging.getLogger("RAG_Web_DatasetRoutes")
dataset_bp = Blueprint("dataset", __name__)

_ingest_progress = {
    "status": "idle",
    "stage": 0,
    "total_stages": 7,
    "stage_name": "Idle",
    "message": "Ready to execute pipeline",
    "elapsed_s": 0,
    "error": None
}


@dataset_bp.route("/ingest-progress", methods=["GET"])
@dataset_bp.route("/dataset/ingest-progress", methods=["GET"])
def get_ingest_progress():
    """Returns real-time pipeline execution progress telemetry for the UI."""
    return jsonify(_ingest_progress)


@dataset_bp.route("/upload-dataset", methods=["POST"])
@dataset_bp.route("/dataset/upload-dataset", methods=["POST"])
def upload_dataset():
    service = PipelineService.get_instance()
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file uploaded in form-data"}), 400
        
        file = request.files["file"]
        if not file.filename.endswith(".json"):
            return jsonify({"error": "Invalid format. Only .json HotpotQA benchmark files are accepted."}), 400

        content = json.load(file.stream)
        if not isinstance(content, list) or len(content) == 0:
            return jsonify({"error": "Dataset must be a non-empty JSON list."}), 400

        sample_item = content[0]
        required_keys = ["_id", "question", "answer", "context", "supporting_facts"]
        missing = [k for k in required_keys if k not in sample_item]
        if missing:
            return jsonify({
                "error": f"Invalid HotpotQA benchmark schema. Missing required keys: {', '.join(missing)}"
            }), 400

        target_path = os.path.join(service.artifacts_dir, "hotpot_dev_distractor_v1.json")
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(content, f, indent=2, ensure_ascii=False)

        # Automatically extract fresh question list
        import importlib
        gen_mod = importlib.import_module("scripts.06_generate_question_list")
        gen_mod.generate_question_list()

        return jsonify({
            "success": True,
            "message": f"Dataset verified and uploaded successfully ({len(content)} questions).",
            "question_count": len(content)
        })
    except Exception as e:
        logger.error(f"Dataset upload exception: {e}")
        return jsonify({"error": str(e)}), 500


@dataset_bp.route("/ingest", methods=["POST"])
@dataset_bp.route("/dataset/ingest", methods=["POST"])
def run_ingest():
    global _ingest_progress
    service = PipelineService.get_instance()
    t0 = time.time()

    def update_progress(stage: int, name: str, msg: str):
        global _ingest_progress
        _ingest_progress.update({
            "status": "running",
            "stage": stage,
            "total_stages": 7,
            "stage_name": name,
            "message": msg,
            "elapsed_s": round(time.time() - t0, 1),
            "error": None
        })
        logger.info(f"[STAGE {stage}/7] {name}: {msg}")

    try:
        # Safely release open database handles before rebuilding
        if service.metadata_store and hasattr(service.metadata_store, "close"):
            service.metadata_store.close()

        import importlib
        access_model_path = os.path.join(service.artifacts_dir, "generated_access_model.json")
        storage_map_path = os.path.join(service.artifacts_dir, "file_to_storage_info.json")
        cred_path = os.path.join(service.artifacts_dir, "test_credential.txt")

        # -----------------------------------------------------------------
        # STAGE 1: Access Model (Script 01)
        # -----------------------------------------------------------------
        update_progress(1, "Access Model Synthesis", "Synthesizing fine-grained AWS/GCP permission matrix...")
        if not os.path.exists(access_model_path):
            script_01 = os.path.join(service.project_root, "scripts", "01_generate_access_model.py")
            subprocess.run([sys.executable, "-u", script_01], cwd=service.project_root, check=True)
        if not os.path.exists(access_model_path):
            raise RuntimeError("Stage 1 failed: generated_access_model.json was not created.")

        # -----------------------------------------------------------------
        # STAGE 2: Cloud Resource & IAM Provisioning (Script 02)
        # -----------------------------------------------------------------
        update_progress(2, "Cloud Resource & IAM Provisioning", "Creating AWS S3/GCP GCS buckets, test personas, and IAM credentials...")
        auth_mode = os.environ.get("AUTH_MODE", "static").strip().lower()
        script_02 = os.path.join(service.project_root, "scripts", "02_gcp_aws_resource_creator.py")
        if os.path.exists(script_02):
            res_02 = subprocess.run(
                [sys.executable, "-u", script_02, "--auth_mode", auth_mode],
                cwd=service.project_root,
                capture_output=True,
                text=True,
                timeout=300
            )
            if res_02.returncode != 0 and not os.path.exists(cred_path):
                err_detail = (res_02.stderr or res_02.stdout or "Unknown error")[-500:]
                raise RuntimeError(f"Stage 2 failed: Cloud resource creator exited with code {res_02.returncode}: {err_detail}")

        # Fail-Fast Gate: Verify test_credential.txt exists and is non-empty
        if not os.path.exists(cred_path) or os.path.getsize(cred_path) < 20:
            raise RuntimeError("Stage 2 validation failed: artifacts/test_credential.txt was not generated.")

        # -----------------------------------------------------------------
        # STAGE 3: Document Preparation & Mapping (Script 03)
        # -----------------------------------------------------------------
        update_progress(3, "Document Preparation", "Partitioning document corpus and mapping cloud bucket storage identifiers...")
        prep_mod = importlib.import_module("scripts.03_prepare_documents")
        prep_mod.generate_documents_and_storage_info()
        if not os.path.exists(storage_map_path):
            raise RuntimeError("Stage 3 failed: file_to_storage_info.json was not created.")

        # -----------------------------------------------------------------
        # STAGE 4: Upload Resources to Multi-Cloud (Script 04)
        # -----------------------------------------------------------------
        update_progress(4, "Multi-Cloud Storage Upload", "Uploading document objects into AWS S3 and GCP GCS buckets...")
        upload_mod = importlib.import_module("scripts.04_upload_resources")
        upload_mod.upload_all(max_workers=20)

        # -----------------------------------------------------------------
        # STAGE 5: User File Visibility Matrix (Script 05)
        # -----------------------------------------------------------------
        update_progress(5, "User File Visibility Matrix", "Computing per-persona file accessibility authorization tables...")
        vis_mod = importlib.import_module("scripts.05_generate_user_accessible_file_list")
        vis_mod.generate_access_visibility()

        # -----------------------------------------------------------------
        # STAGE 6: Benchmark Question Extraction (Script 06)
        # -----------------------------------------------------------------
        update_progress(6, "Benchmark Questions Extraction", "Extracting golden benchmark questions and supporting fact references...")
        q_mod = importlib.import_module("scripts.06_generate_question_list")
        q_mod.generate_question_list()

        # -----------------------------------------------------------------
        # STAGE 7: Dual FAISS + BM25 Vector Ingestion Manager (Script 07)
        # -----------------------------------------------------------------
        update_progress(7, "Dual Vector & BM25 Ingestion", "Building FAISS dense index (all-MiniLM-L6-v2) and BM25 sparse index...")
        from src.managers.ingestion_manager import IngestionManager, IngestionConfig
        cfg = IngestionConfig(
            hotpot_file_path=os.path.join(service.artifacts_dir, "hotpot_dev_distractor_v1.json"),
            storage_map_path=storage_map_path,
            output_dir=service.artifacts_dir,
            vector_db_dir=service.vector_db_dir
        )
        im = IngestionManager(cfg)
        im.ingest()

        # Reload live components into memory
        service.reload()
        elapsed = round(time.time() - t0, 2)

        if not service.is_ready:
            raise RuntimeError("Pipeline reloaded, but service.is_ready is False. Verify credential and index presence.")

        _ingest_progress.update({
            "status": "completed",
            "stage": 7,
            "stage_name": "Pipeline Complete",
            "message": f"Multi-Cloud Ingestion Pipeline completed successfully in {elapsed}s.",
            "elapsed_s": elapsed,
            "error": None
        })

        return jsonify({
            "success": True,
            "message": f"Multi-Cloud Ingestion Pipeline (01-07) completed successfully in {elapsed}s",
            "elapsed_s": elapsed
        })

    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        elapsed = round(time.time() - t0, 2)
        _ingest_progress.update({
            "status": "failed",
            "stage_name": "Error",
            "message": f"Ingestion failed: {str(e)}",
            "elapsed_s": elapsed,
            "error": str(e)
        })
        return jsonify({"error": str(e), "elapsed_s": elapsed}), 500


@dataset_bp.route("/teardown", methods=["POST"])
@dataset_bp.route("/dataset/teardown", methods=["POST"])
def run_teardown():
    """Executes the complete multi-cloud and local data teardown sequence."""
    service = PipelineService.get_instance()
    script_path = os.path.join(service.project_root, "scripts", "ops", "utils", "run_teardown_sequence.py")
    if not os.path.exists(script_path):
        return jsonify({"error": f"Teardown script not found: {script_path}"}), 500

    try:
        t0 = time.time()
        logger.info("Executing Complete Teardown Sequence (scripts/ops/utils/run_teardown_sequence.py)...")
        res = subprocess.run(
            [sys.executable, "-u", script_path],
            cwd=service.project_root,
            capture_output=True,
            text=True,
            timeout=180
        )
        elapsed = round(time.time() - t0, 2)
        # Reload pipeline service to reflect purged state
        service.reload()
        return jsonify({
            "success": True,
            "message": f"Teardown & Reset Sequence completed in {elapsed}s",
            "elapsed_s": elapsed,
            "output": res.stdout[-800:] if res.stdout else "",
            "returncode": res.returncode
        })
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Teardown sequence timed out after 180s"}), 504
    except Exception as e:
        logger.error(f"Teardown exception: {e}")
        return jsonify({"error": str(e)}), 500


@dataset_bp.route("/storage-summary", methods=["GET"])
@dataset_bp.route("/dataset/storage-summary", methods=["GET"])
def get_storage_summary():
    """Returns real-time multi-cloud storage telemetry: AWS & GCP buckets and per-bucket file counts."""
    service = PipelineService.get_instance()
    access_model_path = os.path.join(service.artifacts_dir, "generated_access_model.json")
    storage_map_path = os.path.join(service.artifacts_dir, "file_to_storage_info.json")

    access_model = {}
    if os.path.exists(access_model_path):
        try:
            with open(access_model_path, "r", encoding="utf-8") as f:
                access_model = json.load(f)
        except Exception as e:
            logger.error(f"Error reading access model: {e}")

    storage_map = {}
    if os.path.exists(storage_map_path):
        try:
            with open(storage_map_path, "r", encoding="utf-8") as f:
                storage_map = json.load(f)
        except Exception as e:
            logger.error(f"Error reading storage map: {e}")

    # Count files per bucket
    bucket_counts = {}
    for doc_name, doc_info in storage_map.items():
        b = doc_info.get("bucket")
        if b:
            bucket_counts[b] = bucket_counts.get(b, 0) + 1

    # AWS Buckets
    aws_buckets = []
    aws_abac = access_model.get("AWS_ABAC", {})
    for b_name, attrs in aws_abac.items():
        attr_str = ", ".join(f"{k}={v}" for k, v in attrs.items())
        aws_buckets.append({
            "name": b_name,
            "policy": f"ABAC: {attr_str}" if attr_str else "ABAC",
            "file_count": bucket_counts.get(b_name, 0)
        })

    # GCP Buckets
    gcp_buckets = []
    gcp_rbac = access_model.get("GCP_RBAC", {})
    for role_name, b_name in gcp_rbac.items():
        gcp_buckets.append({
            "name": b_name,
            "policy": f"RBAC: {role_name}",
            "file_count": bucket_counts.get(b_name, 0)
        })

    total_aws_files = sum(b["file_count"] for b in aws_buckets)
    total_gcp_files = sum(b["file_count"] for b in gcp_buckets)

    return jsonify({
        "status": "success",
        "total_documents": len(storage_map),
        "aws": {
            "provider": "Amazon Web Services (S3)",
            "region": os.environ.get("AWS_REGION", "ap-south-1"),
            "total_files": total_aws_files,
            "buckets": aws_buckets
        },
        "gcp": {
            "provider": "Google Cloud Platform (GCS)",
            "region": os.environ.get("GCP_BUCKET_LOCATION", "asia-south1"),
            "total_files": total_gcp_files,
            "buckets": gcp_buckets
        }
    })
