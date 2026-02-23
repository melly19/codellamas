# mock_backend

Simple mock server for `POST /generate` that returns the contents of `generate_result.json` after a 1 second delay.

## Setup
### Mac
```bash
cd mock_backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
### Windows
```bash
cd mock_backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```
## Run

```bash
cd mock_backend
python app.py
```

## Example request

```bash
curl -s -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{"topic":"Library management","code_smells":["duplicate code"],"mode":"single"}'
```

`mode` is optional.

