import re

import sqlglot
from sqlglot import exp

from config import GEMINI_API_KEY
from google import genai


client = genai.Client(api_key=GEMINI_API_KEY)

MODEL_NAME = "gemini-3.5-flash-lite"


PRODUCT_SCHEMA = """
Table: vet_clinic

Confirmed columns:
- ProductID
- ActiveIngredient
- ProductCategory
- TargetAnimal
- Disease
- Symptoms
- Dosage
- RouteOfAdministration
- Duration
- Precautions

Do not assume any other columns exist.
"""


def generate_sql_query(
    user_request: str,
    conversation_history: str,
    rag_context: str,
) -> str:
    prompt = f"""
You are a MySQL query-generation tool for a veterinary product catalog.

DATABASE SCHEMA:
{PRODUCT_SCHEMA}

USER REQUEST:
{user_request}

CONVERSATION HISTORY:
{conversation_history}

VETERINARY RAG CONTEXT:
{rag_context}

RULES:
1. Generate exactly one MySQL SELECT query.
2. Query only the vet_clinic table.
3. Use only the confirmed database columns listed in the schema.
4. NEVER use SELECT *.
5. Always explicitly list the required columns:
   ProductID,
   ActiveIngredient,
   ProductCategory,
   TargetAnimal,
   Disease,
   Symptoms,
   Dosage,
   RouteOfAdministration,
   Duration,
   Precautions.
6. For ingredient searches, use ActiveIngredient.
7. Use ProductCategory when searching for a product category.
8. Return no more than 20 rows.
9. Generate read-only SQL only.
10. Return only SQL without Markdown.
11. If essential product criteria are unclear, return exactly:
NEED_CLARIFICATION

SQL:
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
    )

    sql = (response.text or "").strip()

    # Remove a Markdown fence if the model unexpectedly adds one.
    sql = re.sub(
        r"^```(?:sql)?\s*",
        "",
        sql,
        flags=re.IGNORECASE,
    )
    sql = re.sub(r"\s*```$", "", sql).strip()

    if sql == "NEED_CLARIFICATION":
        return sql

    return sql


def validate_readonly_sql(sql: str) -> str:
    """Allow only a narrowly scoped, read-only vet_clinic query."""

    if not sql or len(sql) > 5000:
        raise ValueError("Invalid SQL query.")

    sql = sql.strip()

    # Allow one optional trailing semicolon.
    if sql.endswith(";"):
        sql = sql[:-1].rstrip()

    # Reject multiple SQL statements.
    if ";" in sql:
        raise ValueError("Multiple SQL statements are not allowed.")

    try:
        statements = sqlglot.parse(sql, read="mysql")
    except Exception as exc:
        raise ValueError("The generated SQL is invalid.") from exc

    if len(statements) != 1 or statements[0] is None:
        raise ValueError("Exactly one SQL statement is required.")

    tree = statements[0]

    if not isinstance(tree, exp.Select):
        raise ValueError("Only SELECT queries are allowed.")

    # Restrict this agent to one table, without joins or nested queries.
    if tree.args.get("joins"):
        raise ValueError("Joins are not allowed.")

    if (
        tree.find(exp.Subquery)
        or tree.find(exp.CTE)
        or tree.find(exp.Union)
    ):
        raise ValueError(
            "Nested queries, CTEs, and UNION are not allowed."
        )

    from_clause = tree.args.get("from_")

    if (
        not from_clause
        or not isinstance(from_clause.this, exp.Table)
    ):
        raise ValueError("Query must select from the vet_clinic table.")

    table = from_clause.this

    if (
        table.name.lower() != "vet_clinic"
        or table.db
        or table.catalog
    ):
        raise ValueError("Only the vet_clinic table is allowed.")

    allowed_columns = {
        "productid",
        "activeingredient",
        "productcategory",
        "targetanimal",
        "disease",
        "symptoms",
        "dosage",
        "routeofadministration",
        "duration",
        "precautions",
    }

    # Disallow SELECT *.
    for projection in tree.expressions:
        if isinstance(projection, exp.Star):
            raise ValueError("SELECT * is not allowed.")

    # Reject columns not listed in the confirmed schema.
    for column in tree.find_all(exp.Column):
        if column.name.lower() not in allowed_columns:
            raise ValueError(f"Unknown column: {column.name}")

        if (
            column.table
            and column.table.lower() != table.alias_or_name.lower()
        ):
            raise ValueError("Unexpected table reference.")

    # Require a literal LIMIT between 1 and 20.
    limit = tree.args.get("limit")

    if limit is None:
        tree = tree.limit(20)
    else:
        limit_value = limit.expression

        if (
            not isinstance(limit_value, exp.Literal)
            or not limit_value.is_int
        ):
            raise ValueError("LIMIT must be an integer literal.")

        amount = int(limit_value.this)

        if not 1 <= amount <= 20:
            raise ValueError("LIMIT must be between 1 and 20.")

    return tree.sql(dialect="mysql")
