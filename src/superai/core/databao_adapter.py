"""
Databao-Agent inspired NL data analytics adapter (Track J).

Repo: https://github.com/realburhanhusain/databao-agent (fork of JetBrains/databao-agent)

Capabilities:
- Register SQLAlchemy / SQLite data sources
- Natural-language questions → table results + text explanation
- Conversational thread context for follow-ups
- Optional real `databao.agent` integration when package is installed
- Offline/mock mode for demos and tests without API keys
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .logger import get_logger
from .model_caller import ModelCaller
from .model_registry import ModelRegistry

logger = get_logger("superai.databao")

try:
    from sqlalchemy import create_engine, text, inspect
    from sqlalchemy.engine import Engine

    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False
    Engine = Any  # type: ignore

try:
    import databao.agent as bao  # type: ignore

    HAS_DATABAO = True
except ImportError:
    HAS_DATABAO = False
    bao = None  # type: ignore


@dataclass
class DataAnswer:
    question: str
    text: str
    sql: Optional[str] = None
    columns: List[str] = field(default_factory=list)
    rows: List[List[Any]] = field(default_factory=list)
    row_count: int = 0
    chart: Optional[Dict[str, Any]] = None  # Vega-Lite-ish spec
    backend: str = "mock"
    error: Optional[str] = None
    thread_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_markdown_table(self, max_rows: int = 20) -> str:
        if not self.columns:
            return self.text or "(no table)"
        header = "| " + " | ".join(str(c) for c in self.columns) + " |"
        sep = "| " + " | ".join("---" for _ in self.columns) + " |"
        lines = [header, sep]
        for row in self.rows[:max_rows]:
            lines.append("| " + " | ".join(str(x) for x in row) + " |")
        if self.row_count > max_rows:
            lines.append(f"\n_… {self.row_count - max_rows} more rows_")
        return "\n".join(lines)


class DataThread:
    """Conversational context for iterative analysis."""

    def __init__(self, adapter: "DatabaoAdapter", thread_id: str):
        self.adapter = adapter
        self.thread_id = thread_id
        self.history: List[Dict[str, Any]] = []

    def ask(self, question: str) -> DataAnswer:
        answer = self.adapter.ask(question, thread=self)
        self.history.append(
            {
                "question": question,
                "sql": answer.sql,
                "row_count": answer.row_count,
                "text": answer.text[:500],
            }
        )
        return answer


class DatabaoAdapter:
    """
    SuperAI supervisor-facing adapter for NL data Q&A.

    Backends (priority):
    1. Real databao-agent if installed and use_databao=True
    2. SQLAlchemy/SQLite with NL→SQL via ModelCaller (or heuristic mock SQL)
    3. Pure mock demo data
    """

    def __init__(
        self,
        dsn: Optional[str] = None,
        use_databao: bool = True,
        use_mock: Optional[bool] = None,
        model_caller: Optional[ModelCaller] = None,
        llm_name: Optional[str] = None,
        demo_sqlite_path: Optional[str] = None,
    ):
        self.dsn = dsn or os.getenv("SUPERAI_DATA_DSN") or os.getenv("DATABASE_URL")
        self.use_databao = use_databao and HAS_DATABAO
        self.llm_name = llm_name or os.getenv("SUPERAI_DATABAO_LLM") or "gpt-4o-mini"
        if use_mock is None:
            use_mock = os.getenv("SUPERAI_MOCK_MODE", "true").lower() in {
                "1",
                "true",
                "yes",
            }
        self.use_mock = use_mock
        self.registry = ModelRegistry()
        self.caller = model_caller or ModelCaller(
            use_mock=self.use_mock, registry=self.registry
        )
        self._engine: Any = None
        self._bao_agent = None
        self._bao_threads: Dict[str, Any] = {}
        self._threads: Dict[str, DataThread] = {}
        self._demo_path = demo_sqlite_path
        self._schema_cache: Optional[str] = None

        if self.use_databao and self.dsn and not self.use_mock:
            self._init_databao()
        elif HAS_SQLALCHEMY and self.dsn:
            self._init_sqlalchemy(self.dsn)
        elif HAS_SQLALCHEMY:
            # Ensure demo SQLite for offline analytics
            path = self._demo_path or str(
                Path.home() / ".superai" / "data" / "demo.sqlite"
            )
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            self._ensure_demo_db(path)
            self._init_sqlalchemy(f"sqlite:///{path}")
        else:
            logger.warning("SQLAlchemy not installed; data-ask uses pure mock tables")

    def _init_databao(self) -> None:
        assert bao is not None
        try:
            if not HAS_SQLALCHEMY:
                raise RuntimeError("SQLAlchemy required for databao backend")
            engine = create_engine(self.dsn)
            domain = bao.domain()
            domain.add_db(engine)
            llm_config = bao.LLMConfig(name=self.llm_name, temperature=0)
            self._bao_agent = bao.agent(domain, name="superai", llm_config=llm_config)
            self._engine = engine
            logger.info("Databao-agent backend initialized")
        except Exception as e:  # noqa: BLE001
            logger.warning("Databao init failed (%s); falling back to SQL path", e)
            self.use_databao = False
            if HAS_SQLALCHEMY and self.dsn:
                self._init_sqlalchemy(self.dsn)

    def _init_sqlalchemy(self, dsn: str) -> None:
        self._engine = create_engine(dsn)
        logger.info("SQLAlchemy engine ready: %s", dsn.split("@")[-1][:80])

    def _ensure_demo_db(self, path: str) -> None:
        """Seed a tiny demo dataset for offline NL analytics."""
        conn = sqlite3.connect(path)
        try:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS customers (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    country TEXT,
                    segment TEXT
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY,
                    customer_id INTEGER,
                    amount REAL,
                    country TEXT,
                    status TEXT
                )
                """
            )
            cur.execute("SELECT COUNT(*) FROM customers")
            if cur.fetchone()[0] == 0:
                cur.executemany(
                    "INSERT INTO customers (id, name, country, segment) VALUES (?,?,?,?)",
                    [
                        (1, "Acme GmbH", "Germany", "enterprise"),
                        (2, "Berlin Tech", "Germany", "smb"),
                        (3, "Paris Foods", "France", "smb"),
                        (4, "NY Media", "USA", "enterprise"),
                        (5, "Munich Soft", "Germany", "startup"),
                    ],
                )
                cur.executemany(
                    "INSERT INTO orders (id, customer_id, amount, country, status) VALUES (?,?,?,?,?)",
                    [
                        (1, 1, 1200.0, "Germany", "paid"),
                        (2, 2, 340.5, "Germany", "paid"),
                        (3, 3, 890.0, "France", "pending"),
                        (4, 4, 2100.0, "USA", "paid"),
                        (5, 5, 150.0, "Germany", "paid"),
                        (6, 1, 500.0, "Germany", "refunded"),
                    ],
                )
            conn.commit()
        finally:
            conn.close()

    def capabilities(self) -> Dict[str, Any]:
        return {
            "has_sqlalchemy": HAS_SQLALCHEMY,
            "has_databao_package": HAS_DATABAO,
            "using_databao": bool(self._bao_agent),
            "dsn_configured": bool(self.dsn),
            "engine_ready": self._engine is not None,
            "use_mock": self.use_mock,
            "llm_name": self.llm_name,
        }

    def thread(self, thread_id: Optional[str] = None) -> DataThread:
        tid = thread_id or f"t{len(self._threads) + 1}"
        if tid not in self._threads:
            self._threads[tid] = DataThread(self, tid)
            if self._bao_agent is not None:
                self._bao_threads[tid] = self._bao_agent.thread()
        return self._threads[tid]

    def schema_summary(self) -> str:
        if self._schema_cache:
            return self._schema_cache
        if self._engine is None or not HAS_SQLALCHEMY:
            self._schema_cache = (
                "Demo schema (logical): customers(id,name,country,segment), "
                "orders(id,customer_id,amount,country,status)"
            )
            return self._schema_cache
        try:
            insp = inspect(self._engine)
            parts = []
            for table in insp.get_table_names():
                cols = [c["name"] for c in insp.get_columns(table)]
                parts.append(f"{table}({', '.join(cols)})")
            self._schema_cache = "; ".join(parts) if parts else "(no tables)"
        except Exception as e:  # noqa: BLE001
            self._schema_cache = f"(schema error: {e})"
        return self._schema_cache

    def ask(self, question: str, thread: Optional[DataThread] = None) -> DataAnswer:
        question = (question or "").strip()
        if not question:
            return DataAnswer(
                question=question,
                text="Empty question.",
                error="Empty question",
                backend="none",
            )

        # Backend 1: real databao
        if self._bao_agent is not None and thread is not None:
            try:
                return self._ask_databao(question, thread.thread_id)
            except Exception as e:  # noqa: BLE001
                logger.warning("Databao ask failed: %s", e)

        # Backend 2: SQLAlchemy + NL→SQL
        if self._engine is not None and HAS_SQLALCHEMY:
            try:
                return self._ask_sqlalchemy(question, thread)
            except Exception as e:  # noqa: BLE001
                logger.warning("SQL path failed: %s", e)
                return DataAnswer(
                    question=question,
                    text=f"Query failed: {e}",
                    error=str(e),
                    backend="sqlalchemy",
                    thread_id=thread.thread_id if thread else None,
                )

        # Backend 3: pure mock
        return self._ask_mock(question, thread)

    def _ask_databao(self, question: str, thread_id: str) -> DataAnswer:
        th = self._bao_threads.get(thread_id) or self._bao_agent.thread()
        self._bao_threads[thread_id] = th
        result = th.ask(question)
        df = None
        try:
            df = result.df()
        except Exception:
            pass
        text_ans = ""
        try:
            text_ans = th.text() if hasattr(th, "text") else str(result)
        except Exception:
            text_ans = "OK"
        columns: List[str] = []
        rows: List[List[Any]] = []
        if df is not None:
            columns = [str(c) for c in df.columns.tolist()]
            rows = df.head(100).values.tolist()
        chart = None
        try:
            plot = th.plot(question) if hasattr(th, "plot") else None
            if plot is not None:
                chart = {"code": getattr(plot, "code", None), "type": "databao_plot"}
        except Exception:
            pass
        return DataAnswer(
            question=question,
            text=str(text_ans),
            columns=columns,
            rows=rows,
            row_count=len(rows),
            chart=chart,
            backend="databao-agent",
            thread_id=thread_id,
        )

    def _ask_sqlalchemy(
        self, question: str, thread: Optional[DataThread]
    ) -> DataAnswer:
        schema = self.schema_summary()
        history = ""
        if thread and thread.history:
            history = "Prior turns:\n" + "\n".join(
                f"- Q: {h['question']} SQL: {h.get('sql')}" for h in thread.history[-3:]
            )
        sql = self._nl_to_sql(question, schema, history)
        sql = self._sanitize_sql(sql)
        columns, rows = self._execute_sql(sql)
        chart = self._maybe_chart_spec(question, columns, rows)
        text = (
            f"Answer for: {question}\n"
            f"Returned {len(rows)} row(s).\n"
            f"SQL: {sql}"
        )
        return DataAnswer(
            question=question,
            text=text,
            sql=sql,
            columns=columns,
            rows=rows,
            row_count=len(rows),
            chart=chart,
            backend="sqlalchemy",
            thread_id=thread.thread_id if thread else None,
        )

    def _nl_to_sql(self, question: str, schema: str, history: str) -> str:
        # Heuristic shortcuts for demo reliability without LLM
        q = question.lower()
        if "german" in q and ("customer" in q or "show" in q or "list" in q):
            return "SELECT id, name, country, segment FROM customers WHERE country = 'Germany'"
        if "revenue" in q or ("amount" in q and "country" in q) or "by country" in q:
            return (
                "SELECT country, SUM(amount) AS total_amount, COUNT(*) AS order_count "
                "FROM orders GROUP BY country ORDER BY total_amount DESC"
            )
        if "pending" in q:
            return "SELECT * FROM orders WHERE status = 'pending'"
        if "paid" in q and "order" in q:
            return "SELECT * FROM orders WHERE status = 'paid'"

        if self.use_mock:
            return "SELECT id, name, country, segment FROM customers LIMIT 20"

        prompt = (
            "You convert natural language to a single SQLite-compatible SQL SELECT.\n"
            "Rules: Only SELECT/WITH; no writes; no multiple statements; no comments.\n"
            f"Schema: {schema}\n"
            f"{history}\n"
            f"Question: {question}\n"
            "Return ONLY the SQL."
        )
        raw = self.caller.call(model="gpt-4o", prompt=prompt)
        text = str(raw.get("response") or "")
        sql = self._extract_sql(text)
        return sql or "SELECT id, name, country, segment FROM customers LIMIT 20"

    def _extract_sql(self, text: str) -> Optional[str]:
        text = text.strip()
        fence = re.search(r"```(?:sql)?\s*([\s\S]*?)```", text, re.I)
        if fence:
            return fence.group(1).strip().rstrip(";")
        if text.lower().startswith("select") or text.lower().startswith("with"):
            return text.split(";")[0].strip()
        m = re.search(r"(SELECT[\s\S]+)", text, re.I)
        if m:
            return m.group(1).split(";")[0].strip()
        return None

    def _sanitize_sql(self, sql: str) -> str:
        s = (sql or "").strip().rstrip(";")
        low = s.lower()
        banned = (
            "insert ",
            "update ",
            "delete ",
            "drop ",
            "alter ",
            "attach ",
            "detach ",
            "pragma ",
            "create ",
            "replace ",
            "truncate ",
        )
        if not (low.startswith("select") or low.startswith("with")):
            raise ValueError("Only SELECT/WITH queries are allowed")
        for b in banned:
            if b in low:
                raise ValueError(f"Forbidden SQL keyword detected: {b.strip()}")
        if ";" in s:
            raise ValueError("Multiple statements not allowed")
        return s

    def _execute_sql(self, sql: str) -> Tuple[List[str], List[List[Any]]]:
        with self._engine.connect() as conn:
            result = conn.execute(text(sql))
            columns = list(result.keys())
            rows = [list(r) for r in result.fetchmany(500)]
        return columns, rows

    def _maybe_chart_spec(
        self, question: str, columns: List[str], rows: List[List[Any]]
    ) -> Optional[Dict[str, Any]]:
        q = question.lower()
        if not columns or not rows:
            return None
        if not any(k in q for k in ("chart", "plot", "bar", "by country", "revenue")):
            # still emit a simple bar if 2 cols numeric-ish aggregate
            if len(columns) >= 2 and len(rows) <= 20:
                pass
            else:
                return None
        # Vega-Lite-ish bar chart from first categorical + first numeric-looking col
        cat = columns[0]
        val = columns[1] if len(columns) > 1 else columns[0]
        values = []
        for r in rows[:50]:
            values.append({cat: r[0], val: r[1] if len(r) > 1 else 1})
        return {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "description": question,
            "data": {"values": values},
            "mark": "bar",
            "encoding": {
                "x": {"field": cat, "type": "nominal"},
                "y": {"field": val, "type": "quantitative"},
            },
        }

    def _ask_mock(self, question: str, thread: Optional[DataThread]) -> DataAnswer:
        columns = ["country", "total_amount", "order_count"]
        rows = [
            ["Germany", 2190.5, 4],
            ["USA", 2100.0, 1],
            ["France", 890.0, 1],
        ]
        return DataAnswer(
            question=question,
            text=f"[Mock data answer] {question}",
            sql="SELECT country, SUM(amount) ... (mock)",
            columns=columns,
            rows=rows,
            row_count=len(rows),
            chart=self._maybe_chart_spec("bar chart by country", columns, rows),
            backend="mock",
            thread_id=thread.thread_id if thread else None,
        )


# Module-level convenience for CLI
_default_adapter: Optional[DatabaoAdapter] = None


def get_adapter(reset: bool = False, **kwargs: Any) -> DatabaoAdapter:
    global _default_adapter
    if reset or _default_adapter is None:
        _default_adapter = DatabaoAdapter(**kwargs)
    return _default_adapter
