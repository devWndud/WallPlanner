## Life Calendar Image API (Flask)

Simple Flask API that returns a generated PNG similar to LifeCal:

- **Endpoint**: `/goal`
- **Query params**:
  - `goal` (string, optional): title text (e.g. `Back to School`)
  - `goal_date` (YYYY-MM-DD, required): target date
  - `start_date` (YYYY-MM-DD, required): start date
  - `width` (int, optional, default `1080`)
  - `height` (int, optional, default `2340`)

Example:

```text
GET /goal?goal=Back%20to%20School&goal_date=2026-03-03&start_date=2026-01-01&width=1080&height=2340
```

### Local development

```bash
pip install -r requirements.txt
python app.py
```

Then open in your browser:

```text
http://127.0.0.1:5000/goal?goal=Back%20to%20School&goal_date=2026-03-03&start_date=2026-01-01&width=1080&height=2340
```


