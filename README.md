# Intelligent Logistics Gateway (ILG) Auditor

> A four-layer data pipeline that connects edge computer vision tracking with a cloud analytics lakehouse to automate fleet manifest auditing.

This system replaces manual gate logs with an automated pipeline that tracks vehicles, extracts license plate text, runs data quality checks in a distributed lakehouse, and surfaces operational alerts on an interactive dashboard.

**Live Dashboard →** [Hugging Face Spaces](https://huggingface.co/spaces/YOUR_USERNAME/ilg-auditor)  
**Demo Video →** [Watch the edge layer running locally](YOUR_VIDEO_LINK)

---

## System Architecture

```
[1. EDGE LAYER]              [2. API LAYER]           [3. LAKEHOUSE LAYER]        [4. DASHBOARD LAYER]
  Local Video Feed    →→→    FastAPI + Docker   →→→   Databricks (PySpark)   →→→  Streamlit on HF Spaces
  YOLOv11 + ByteTrack        Async ingestion          Bronze → Silver → Gold       Live operational UI
  PaddleOCR                  Local Docker container   Medallion architecture       Confidence sliders
  TemporalVoter              Logs to CSV/DB           Manifest reconciliation      IDS breach alerts
```

**Design decision — why live video is not in the public dashboard:**  
The computer vision models run locally on edge hardware. Only the finalized, cleaned text logs are piped to the cloud lakehouse. This intentionally mirrors real industrial deployments where heavy video inference stays on-premise to save bandwidth, while analytics and reporting run in the cloud.

---

## Layer Breakdown

### 1. Edge Layer — Visual Intelligence
Processes raw video frames to produce clean, structured text records.

- **YOLOv11 + ByteTrack** — detects and tracks individual vehicles frame-by-frame, assigning a unique `track_id` to each vehicle so it is only logged once as it crosses the gate zone
- **PaddleOCR** — extracts license plate and container ID text from cropped bounding box regions
- **TemporalVoter (custom)** — aggregates OCR reads across multiple frames for the same `track_id` and commits only the majority-vote result, eliminating jitter from motion blur and lighting variation

### 2. API Layer — Data Ingestion
An asynchronous FastAPI service running inside a local Docker container.

- Acts as the gateway checkpoint between the edge camera and the cloud
- Accepts structured JSON payloads from the edge layer (tracking ID, plate text, confidence score, entry/exit timestamps)
- Writes finalized records to the local landing zone before cloud upload

### 3. Lakehouse Layer — Data Engineering
Built inside Databricks Community Edition using PySpark. Processes raw logs through a Medallion architecture.

| Layer | Purpose |
|-------|---------|
| **Bronze** | Raw ingestion — stores all incoming records without modification |
| **Silver** | Data quality filtering — removes background noise and low-confidence reads |
| **Gold** | Business logic — LEFT JOIN against the corporate shipping manifest to flag missing arrivals |

**Notable engineering fix:** Resolved a PySpark namespace collision where importing `pyspark.sql.functions.abs` silently overrode Python's built-in `abs()`, causing incorrect metric calculations in the Gold layer. Fixed by aliasing the import at the module level.

### 4. Presentation Layer — Operational Dashboard
A containerized Streamlit app hosted on Hugging Face Spaces.

- Displays the full audit log with confidence scores and manual review flags
- Live slider controls for minimum confidence threshold and minimum plate character length
- Carrier Reliability leaderboard ranked by on-time arrival rate
- IDS breach alerts highlighted automatically when discrepancy exceeds threshold

---

## Tech Stack

| Category | Tools |
|----------|-------|
| Computer Vision | YOLOv11, ByteTrack, PaddleOCR, OpenCV |
| Backend & DevOps | FastAPI, Docker, Python 3.10 |
| Data Engineering | Databricks, PySpark SQL, Delta Lake |
| Dashboard & Hosting | Streamlit, Pandas, Hugging Face Spaces |

---

## Business Metrics

### Data Quality Guardrails (Silver Layer)

| Rule | Condition | Action |
|------|-----------|--------|
| Hard discard | Confidence < 65% OR plate length < 3 chars | Record dropped — background noise |
| Manual review flag | Confidence 65–75% | Accepted but flagged on dashboard for operator verification |
| Clean record | Confidence ≥ 75% AND plate length ≥ 3 chars | Written to Gold layer |

### Inventory Discrepancy Score (IDS)

Measures variance between planned corporate dispatches and physically verified gate arrivals:

$$IDS = \frac{|Visual_{Count} - Scheduled_{Count}|}{Scheduled_{Count}}$$

**Validation test:** A synthetic shipping manifest was loaded with one intentionally absent carrier (`TRK-9999`) to test anomaly detection end-to-end. The Gold layer correctly identified the missing arrival and generated a **33.3% IDS**, triggering an automated breach alert on the dashboard.

### Carrier Reliability Score (CRS)

Ranks carriers by their 7-day on-time arrival rate to identify unreliable vendors:

$$CRS_{carrier} = \frac{On\text{-}Time\ Arrivals_{7d}}{Scheduled\ Arrivals_{7d}}$$

---

## Production Troubleshooting Log

Real problems encountered and resolved during deployment — included here as a record of production engineering decisions.

**Port 8501 alignment**  
Hugging Face Spaces health checks expected application responses on port `8501`. The initial Dockerfile exposed port `7860`, causing the container to loop in a `Restarting` state. Fixed by aligning the `EXPOSE` directive and the Streamlit startup command to port `8501`.

**Iframe CORS block (403 error)**  
Streamlit's built-in XSRF protection flagged file uploads as unauthorized cross-site requests because the app runs inside an HTML iframe on Hugging Face. Fixed by launching the container with CORS and XSRF protection explicitly disabled for this public hosting environment:

```dockerfile
CMD streamlit run app.py \
    --server.port=8501 \
    --server.address=0.0.0.0 \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false
```

---

## Repository Structure

```
ilg-auditor/
├── README.md
├── edge_node/
│   └── inference.py          # CV loop: YOLOv11, ByteTrack, PaddleOCR, TemporalVoter
├── backend_api/
│   ├── main.py               # FastAPI ingestion endpoint
│   ├── Dockerfile            # Local container config
│   └── requirements.txt
└── cloud_dashboard/
    ├── app.py                # Streamlit dashboard
    ├── Dockerfile            # HF Spaces container config (port 8501, CORS disabled)
    └── requirements.txt
```

---

## Data Sources

- **UA-DETRAC** — public vehicle tracking dataset used for edge layer development and testing
- **CCPD** — public Chinese license plate dataset used for PaddleOCR fine-tuning and validation
- **Synthetic shipping manifest** — generated programmatically to simulate a corporate dispatch schedule for Gold layer reconciliation testing
