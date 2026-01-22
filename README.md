# codellamas
An assessment generation VSCode extension!

# How to Run the Backend

.\.venv\Scripts\Activate.ps1 (Optional)
cd src
python -m uvicorn codellamas_backend.api:app --reload

# Test Generation
curl -X POST "http://127.0.0.1:8000/generate" `
  -H "Content-Type: application/json" `
  --data-binary "[generate.json file location]"

# Test Evaluation
curl -X POST "http://127.0.0.1:8000/evaluate/submission" `
  -H "Content-Type: application/json" `
  --data-binary "[payload.json file location]"