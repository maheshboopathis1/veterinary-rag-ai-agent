import logging
import mysql.connector
from fastapi import HTTPException
from services.sql_agent import validate_readonly_sql

from config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME

logger = logging.getLogger(__name__)


import mysql.connector
from fastapi import HTTPException

from config import (
    DB_HOST,
    DB_PORT,
    DB_USER,
    DB_PASSWORD,
    DB_NAME,
)

from services.sql_agent import validate_readonly_sql

logger = logging.getLogger(__name__)


def get_db_connection():
    try:
        return mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            connection_timeout=10,
        )
    except mysql.connector.Error as exc:
        logger.exception("MySQL connection failed")
        raise HTTPException(
            status_code=503,
            detail="Unable to connect to the product database.",
        ) from exc


def get_products_by_ids(product_ids: list[str]) -> list[dict]:
    if not product_ids:
        return []

    connection = get_db_connection()
    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)
        placeholders = ", ".join(["%s"] * len(product_ids))

        query = f"""
            SELECT
                ProductID,
                ActiveIngredient,
                ProductCategory,
                TargetAnimal,
                Disease,
                Symptoms,
                Dosage,
                RouteOfAdministration,
                Duration,
                Precautions
            FROM vet_clinic
            WHERE ProductID IN ({placeholders})
        """

        cursor.execute(query, tuple(product_ids))
        rows = cursor.fetchall()

        product_map = {
            str(row["ProductID"]).strip(): row
            for row in rows
        }

        missing = set(product_ids) - set(product_map)

        if missing:
            raise HTTPException(
                status_code=404,
                detail=f"Products not found: {sorted(missing)}",
            )

        return [product_map[pid] for pid in product_ids]

    except HTTPException:
        raise
    except mysql.connector.Error:
        logger.exception("Product lookup failed")
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve product information.",
        )
    finally:
        if cursor:
            cursor.close()
        connection.close()

def execute_readonly_sql(sql: str) -> list[dict]:
    connection = None
    cursor = None

    try:
        print("sqlll",sql)
        # Validate again at the database boundary.
        safe_sql = validate_readonly_sql(sql)

        print("coming safe sql",safe_sql)

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(safe_sql)

        rows = cursor.fetchall()
        print("coming rows from sql",rows)

        # Return only actual records from MySQL.
        return [
            {key: value for key, value in row.items()}
            for row in rows
        ]

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except mysql.connector.Error as exc:
        logger.exception("Read-only product query failed")
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve matching products.",
        ) from exc

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()
