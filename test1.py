from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware   # 👈 NEW
from pydantic import BaseModel
import os, re, asyncpg
from dotenv import load_dotenv
from google import genai
from datetime import datetime

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

if not DATABASE_URL:
    raise RuntimeError("Please set DATABASE_URL")
if not GEMINI_API_KEY:
    raise RuntimeError("Please set GEMINI_API_KEY or GOOGLE_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)

app = FastAPI(title="Energy DB — ZEIT SYSTEM")

# ✅ Add CORS for React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pool: asyncpg.pool.Pool | None = None


@app.on_event("startup")
async def startup():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)

@app.on_event("shutdown")
async def shutdown():
    global pool
    if pool:
        await pool.close()

TABLE_NAME = "energy_data"
COLUMNS = ["id", "timestamp", "voltage", "current", "power", "pf", "kwh", "machine_id"]

class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    sql: str
    rows: list
    answer: str

FORBIDDEN_SQL_PATTERNS = re.compile(
    r"\b(drop|delete|insert|update|alter|truncate|create|grant|revoke|;|--|/\*)\b",
    re.IGNORECASE
)

def is_sql_safe(sql: str) -> bool:
    if FORBIDDEN_SQL_PATTERNS.search(sql):
        return False
    if not sql.strip().lower().startswith("select"):
        return False
    if TABLE_NAME not in sql.lower():
        return False
    return True

SQL_SYSTEM_PROMPT = f"""
You are an expert SQL generator for PostgreSQL.  
Your job: Convert the user’s question into ONE safe SQL SELECT query for the table `{TABLE_NAME}` with columns: {', '.join(COLUMNS)}.

===============================
STRICT RULES
===============================

1. **Output**
   - Output only one SQL SELECT statement (no explanation, no markdown, no semicolon).
   - Never invent columns or tables.
   - Only use `{TABLE_NAME}` and its listed columns.
   - Column names must be lowercase exactly as in schema.

2. **Date & Time Handling**
   - Parse natural language dates (e.g., "August 2" → "YYYY-MM-DD 00:00:00") using the year in the question or assume 2025 if not given.
   - Month/day names are case-insensitive (e.g., "Aug", "august").
   - Always use `timestamp >=` and `<` for ranges.
   - For exact days with "and", use `timestamp IN ('date1','date2')`.

3. **"AND" vs "BETWEEN"**
   - **"and"** between two dates/times → Use `timestamp IN ('date1','date2')`.
   - **"between"** → Use `timestamp >= date1 AND timestamp <= date2 ORDER BY timestamp ASC`.
   - Logic is case-insensitive.

4. **Machine Filters**
   - Machine IDs are strictly 'M1', 'M2', 'M3'.
   - Normalize:
     - "machine 1" → 'M1'
     - "m1" / "M1" → 'M1'
   - If multiple machines → `machine_id IN (...)`.
   - If none mentioned → all machines.

5. **Metric Handling**
   - Map user terms to schema:
     - "voltage" → `voltage`
     - "current" → `current`
     - "power" → `power`
     - "power factor" → `power_factor`
     - "load" → `load`
     - "kwh" → `kwh`
   - Case-insensitive.

6. **Aggregation Rules**
   - Use aggregation only if requested or implied:
     - SUM → total, sum
     - AVG → average, avg
     - MIN → min, minimum, lowest, smallest
     - MAX → max, maximum, highest, largest
     - DIFFERENCE → use subtraction (`MAX(column) - MIN(column) AS difference`)
   - If no aggregation → return raw rows with `machine_id`, `timestamp`, and requested metric(s).
   - When aggregating, include all non-aggregated columns in GROUP BY.

7. **Ordering & Limits**
   - Use `ORDER BY` when results should be sorted by metric or timestamp.
   - Use `LIMIT` only for “first”, “latest”, “top” requests.

8. **Restrictions**
   - No deletes, updates, or table creation.
   - Never guess data.
   - Only return columns needed to answer the question.

9. **STRICT Power Consumption Rule**
   - "power consumption", "energy consumption", "units consumed", "kwh used" → ALWAYS calculate from `kwh`.
   - ❌ Never use `power` column for consumption queries.
   - ❌ Never use `SUM(power)` for consumption.
   - ✅ Always compute consumption from `kwh`:
     - For a single day: `(MAX(kwh on that day) - MAX(kwh on previous day))`.
     - For a date range: `MAX(kwh) - MIN(kwh)`.
   - Subqueries/self-joins are allowed only to fetch previous day’s reading.
   - If the query asks for "power consumption" and you use `power`, it is **wrong**.

10. **Power vs. Consumption Distinction**
   - If the user asks for "power" → return `power` (instantaneous values).
   - If the user asks for "power consumption" → return calculation using `kwh`.
   - Never confuse these two.

===============================
FEW-SHOT EXAMPLES
===============================

User: What is the voltage on 2025-08-07 and 2025-07-29 for M1?  
SQL: SELECT machine_id, timestamp, voltage FROM {TABLE_NAME} WHERE machine_id = 'M1' AND timestamp IN ('2025-08-07 00:00:00','2025-07-29 00:00:00');

User: What is the voltage between 2025-08-01 and 2025-08-05 for M1 and M2?  
SQL: SELECT machine_id, timestamp, voltage FROM {TABLE_NAME} WHERE machine_id IN ('M1','M2') AND timestamp >= '2025-08-01 00:00:00' AND timestamp <= '2025-08-05 23:59:59' ORDER BY timestamp ASC;

User: What is the highest voltage between August 1 and August 5 for M1?  
SQL: SELECT machine_id, MAX(voltage) AS highest_voltage FROM {TABLE_NAME} WHERE machine_id = 'M1' AND timestamp >= '2025-08-01 00:00:00' AND timestamp <= '2025-08-05 23:59:59' GROUP BY machine_id;

User: What is the difference in power between Aug 1 and Aug 3 for M2?  
SQL: SELECT machine_id, MAX(power) - MIN(power) AS difference FROM {TABLE_NAME} WHERE machine_id = 'M2' AND timestamp IN ('2025-08-01 00:00:00','2025-08-03 00:00:00') GROUP BY machine_id;

User: What is the sum of load for M3 between July 29 and Aug 1?  
SQL: SELECT machine_id, SUM(load) AS total_load FROM {TABLE_NAME} WHERE machine_id = 'M3' AND timestamp >= '2025-07-29 00:00:00' AND timestamp <= '2025-08-01 23:59:59' GROUP BY machine_id;

User: What is the average power for M2 in August 2025?  
SQL: SELECT machine_id, AVG(power) AS average_power FROM {TABLE_NAME} WHERE machine_id = 'M2' AND timestamp >= '2025-08-01 00:00:00' AND timestamp < '2025-09-01 00:00:00' GROUP BY machine_id;

User: What is the power consumption on Aug 1 for M1?  
SQL: SELECT t1.machine_id, (MAX(t1.kwh) - (SELECT MAX(kwh) FROM {TABLE_NAME} WHERE machine_id = 'M1' AND timestamp < '2025-08-01 00:00:00')) AS power_consumption FROM {TABLE_NAME} t1 WHERE t1.machine_id = 'M1' AND DATE(t1.timestamp) = '2025-08-01' GROUP BY t1.machine_id;

User: What is the power consumption between Aug 1 and Aug 5 for M1?  
SQL: SELECT machine_id, MAX(kwh) - MIN(kwh) AS power_consumption FROM {TABLE_NAME} WHERE machine_id = 'M1' AND timestamp >= '2025-08-01 00:00:00' AND timestamp <= '2025-08-05 23:59:59' GROUP BY machine_id;

===============================
TASK
===============================
Now, given the user's question, generate exactly one correct SQL SELECT query following all rules above.
"""

ANALYSIS_SYSTEM_PROMPT = """
You are an assistant that, given the user's question and the SQL results, produces a concise answer.
Rules:
- Base answer ONLY on returned rows — no invented values.
- Mention machine_id if present.
- If rows are empty, say so.
"""

async def classify_intent(question: str) -> str:
    prompt = f"""
    Classify this message: "{question}"
    One word only: greeting, help, data_query, or other.
    """
    resp = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
    return (getattr(resp, 'text', None) or str(resp)).strip().lower()

async def generate_sql_from_question(question: str) -> str:
    prompt = SQL_SYSTEM_PROMPT + "\nUser question: " + question + "\nSQL:"
    resp = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
    sql = getattr(resp, 'text', None) or str(resp)
    lines = [l.strip() for l in sql.splitlines() if l.strip()]
    candidate = next((line for line in reversed(lines) if line.lower().startswith("select")), sql.strip())
    return candidate.rstrip(';')

def ensure_machine_in_select_for_top_row(sql: str) -> str:
    low = sql.lower()
    if "order by" in low and re.search(r"limit\s+1\b", low) and "machine_id" not in low:
        m = re.search(r"select\s+(.*?)\s+from\s+" + re.escape(TABLE_NAME), sql, flags=re.I | re.S)
        if m:
            cols = m.group(1).strip()
            if cols != "*" and "machine_id" not in cols.lower():
                new_cols = cols + ", machine_id"
                sql = re.sub(
                    r"(select\s+)(.*?)(\s+from\s+" + re.escape(TABLE_NAME) + r")",
                    lambda mo: mo.group(1) + new_cols + mo.group(3),
                    sql, flags=re.I | re.S
                )
    return sql

async def generate_answer_from_rows(question: str, rows: list) -> str:
    rows_preview = str(rows)[:3000]
    prompt = ANALYSIS_SYSTEM_PROMPT + "\nUser question: " + question + "\nSQL results: " + rows_preview + "\nAnswer:"
    resp = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
    return (getattr(resp, 'text', None) or str(resp)).strip()

# -----------------------------------------
# Manual handler for between / sum / avg / latest
# -----------------------------------------
def detect_manual_sql(question: str):
    q_lower = question.lower()
    machines = re.findall(r"m\d+", q_lower)
    machine_filter = ""
    if machines:
        machine_list = ", ".join(f"'{m.upper()}'" for m in machines)
        machine_filter = f"AND machine_id IN ({machine_list})"

    # ⚡ Strict Rule: Power Consumption must always use kwh
    if any(term in q_lower for term in ["power consumption", "energy consumption", "units consumed", "kwh used"]):
        # Detect date(s)
        date_matches = re.findall(r"\d{4}-\d{2}-\d{2}", question)
        if len(date_matches) == 1:  
            # Single day → max(today) - max(previous day)
            date = date_matches[0]
            return f"""
                SELECT t1.machine_id,
                       (MAX(t1.kwh) - COALESCE(
                           (SELECT MAX(kwh) FROM {TABLE_NAME}
                            WHERE machine_id = t1.machine_id
                              AND timestamp < '{date} 00:00:00'), 0)
                       ) AS power_consumption
                FROM {TABLE_NAME} t1
                WHERE DATE(t1.timestamp) = '{date}'
                  {machine_filter}
                GROUP BY t1.machine_id
            """.strip()
        elif len(date_matches) >= 2:  
            # Range → max - min
            start_date, end_date = date_matches[0], date_matches[1]
            return f"""
                SELECT machine_id,
                       MAX(kwh) - MIN(kwh) AS power_consumption
                FROM {TABLE_NAME}
                WHERE timestamp >= '{start_date} 00:00:00'
                  AND timestamp <= '{end_date} 23:59:59'
                  {machine_filter}
                GROUP BY machine_id
            """.strip()
        else:
            # No explicit date → assume today
            today = datetime.now().strftime("%Y-%m-%d")
            return f"""
                SELECT t1.machine_id,
                       (MAX(t1.kwh) - COALESCE(
                           (SELECT MAX(kwh) FROM {TABLE_NAME}
                            WHERE machine_id = t1.machine_id
                              AND timestamp < '{today} 00:00:00'), 0)
                       ) AS power_consumption
                FROM {TABLE_NAME} t1
                WHERE DATE(t1.timestamp) = '{today}'
                  {machine_filter}
                GROUP BY t1.machine_id
            """.strip()

    # Normal metrics (voltage, current, power, pf, kwh)
    metric_match = re.search(r"(voltage|current|power|pf|kwh)", q_lower)

    # Sum
    if "total" in q_lower or "sum" in q_lower:
        if metric_match:
            metric = metric_match.group(1)
            return f"""
                SELECT machine_id, SUM({metric}) AS total_{metric}
                FROM {TABLE_NAME}
                WHERE 1=1 {machine_filter}
                GROUP BY machine_id
            """.strip()

    # Average
    if "average" in q_lower or "avg" in q_lower or "mean" in q_lower:
        if metric_match:
            metric = metric_match.group(1)
            return f"""
                SELECT machine_id, AVG({metric}) AS avg_{metric}
                FROM {TABLE_NAME}
                WHERE 1=1 {machine_filter}
                GROUP BY machine_id
            """.strip()

    # Between / And — raw values
    date_matches = re.findall(r"\d{4}-\d{2}-\d{2}(?: \d{2}:\d{2}:\d{2})?", question)
    if ("between" in q_lower or " and " in q_lower) and len(date_matches) >= 2:
        if metric_match:
            metric = metric_match.group(1)
            start_date = date_matches[0]
            end_date = date_matches[1]
            return f"""
                SELECT machine_id, {metric}, timestamp
                FROM {TABLE_NAME}
                WHERE timestamp >= '{start_date}'
                  AND timestamp <= '{end_date}'
                  {machine_filter}
                ORDER BY timestamp ASC
            """.strip()

    # Latest
    if "latest" in q_lower:
        if metric_match:
            metric = metric_match.group(1)
            return f"""
                SELECT DISTINCT ON (machine_id) machine_id, {metric} AS latest_{metric}, timestamp
                FROM {TABLE_NAME}
                {machine_filter}
                ORDER BY machine_id, timestamp DESC
            """.strip()

    return None




    # Average
    if "average" in q_lower or "avg" in q_lower or "mean" in q_lower:
        if metric_match:
            metric = metric_match.group(1)
            return f"""
                SELECT machine_id, AVG({metric}) AS avg_{metric}
                FROM {TABLE_NAME}
                WHERE 1=1 {machine_filter}
                GROUP BY machine_id
            """.strip()

    # Between / And — raw values
    date_matches = re.findall(r"\d{4}-\d{2}-\d{2}(?: \d{2}:\d{2}:\d{2})?", question)
    if ("between" in q_lower or " and " in q_lower) and len(date_matches) >= 2:
        if metric_match:
            metric = metric_match.group(1)
            start_date = date_matches[0]
            end_date = date_matches[1]
            return f"""
                SELECT machine_id, {metric}, timestamp
                FROM {TABLE_NAME}
                WHERE timestamp >= '{start_date}'
                  AND timestamp <= '{end_date}'
                  {machine_filter}
                ORDER BY timestamp ASC
            """.strip()

    # Latest
    if "latest" in q_lower:
        if metric_match:
            metric = metric_match.group(1)
            return f"""
                SELECT DISTINCT ON (machine_id) machine_id, {metric} AS latest_{metric}, timestamp
                FROM {TABLE_NAME}
                {machine_filter}
                ORDER BY machine_id, timestamp DESC
            """.strip()

    return None

@app.post("/query/", response_model=QueryResponse)
async def nl_query(req: QueryRequest):
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Empty question")

    try:
        intent = await classify_intent(question)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Intent detection failed: {e}")

    if intent == "greeting":
        return QueryResponse(sql="", rows=[], answer="Hi 😊 Welcome to Zeit's Bot. How can I help you today?")
    
    if intent == "greeting":
        return QueryResponse(sql="", rows=[], answer="Hello 😊 How are you ?")
         
    if intent == "help":
        return QueryResponse(sql="", rows=[], answer="I can query your energy data. Ask me about dates, ranges, totals, etc.")
    if intent == "other":
        return QueryResponse(sql="", rows=[], answer="I’m not sure 🤔. Can you rephrase?")

    manual_sql = detect_manual_sql(question)
    if manual_sql:
        sql = manual_sql
    else:
        try:
            sql = await generate_sql_from_question(question)
            sql = ensure_machine_in_select_for_top_row(sql)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"SQL generation failed: {e}")

    if not is_sql_safe(sql):
        raise HTTPException(status_code=400, detail="Generated SQL failed safety checks")

    async with pool.acquire() as conn:
        try:
            records = await conn.fetch(sql)
            rows = [dict(r) for r in records]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Database error: {e}")

    try:
        answer = await generate_answer_from_rows(question, rows)
    except Exception as e:
        answer = f"(Answer generation failed: {e})"

    return QueryResponse(sql=sql, rows=rows, answer=answer)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("fastapi_gemini_energy_app:app", host="0.0.0.0", port=8000, reload=True)







