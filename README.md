# Idempotent Data Ingestion Pipeline

An automated ETL (Extract, Transform, Load) system designed to reliably convert unstructured, messy text (like raw OCR data from invoices, receipts, or medical records) into clean, structured database records using Large Language Models.

Unlike standard AI wrappers that blindly trust LLM outputs, this pipeline introduces **deterministic guardrails** and a **self-healing feedback loop**. Powered by **Gemini 3.5 Flash-Lite**, it validates extracted data against strict business logic and guarantees **idempotency** to prevent duplicate records.

## 🚀 Key Features

* **Self-Healing LLM Loop:** Uses Pydantic to enforce strict programmatic tests (e.g., `subtotal + tax = total`). If Gemini makes a math or logic error, the pipeline catches it and prompts the model to correct its own mistake.
* **Idempotent Storage:** Hashes raw document text (SHA-256) before saving to the SQLite database. If a document is processed multiple times, it is safely skipped to prevent duplicate database entries.
* **Fast & Cost-Effective:** Utilizes Gemini 3.5 Flash-Lite for high-speed, lightweight, and cost-efficient structured data extraction.
* **Deterministic Guardrails:** Ensures data integrity before it ever touches your database.

## 📁 Project Structure

* `main.py`: The entry point of the application. Reads raw text and orchestrates the pipeline.
* `pipeline.py`: Handles the interaction with Gemini 3.5 Flash-Lite and contains the self-healing `try...except` retry loop.
* `schemas.py`: Defines the Pydantic models (`BaseModel`) and validators (`@model_validator`) used to enforce math and business logic on the extracted data.
* `db.py`: Manages the SQLite database connection, table initialization, and the idempotent saving logic (hashing).
* `sample_invoice.txt`: Dummy text data used to test the pipeline (includes deliberate errors to test the self-healing loop).
* `requirements.txt`: Contains the required Python dependencies for the project.

## 🛠️ Getting Started

### Prerequisites

* Python 3.8+
* A valid Gemini API Key

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/idempotent-data-pipeline.git
   cd idempotent-data-pipeline
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set your API Key:**
   ```bash
   export GEMINI_API_KEY="your-api-key-here" # Or whichever env variable your pipeline.py expects
   ```

### Usage

Run the main execution script to process the sample invoice:

```bash
python main.py
```

**What to expect:**
1. On the **first run**, the pipeline will read `sample_invoice.txt`, extract the data using Gemini, validate the math, self-heal if necessary, and save it to the SQLite database.
2. On the **second run**, the pipeline will recognize the document hash and skip processing, outputting a "Duplicate found, skipping" message to demonstrate idempotency.

## 🧠 How It Works (Architecture)

1. **Raw Document Input:** Reads unstructured text files.
2. **Extraction Node:** Gemini 3.5 Flash-Lite extracts data into a strict JSON schema.
3. **Invariant Engine:** Pydantic parses the JSON and tests the business logic.
4. **Targeted Feedback Loop:** If validation fails, the exact error is fed back to Gemini for correction (up to a set max retries).
5. **Idempotent Storage Node:** The original text is hashed. If the hash is new, the validated data is inserted into the SQLite database.