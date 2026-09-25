from flask import Flask, render_template, request, redirect, Response
from datetime import date
import sqlite3
import csv
import io

from ml_model import predict_category

app = Flask(__name__)

DATABASE = "expenses.db"
DEFAULT_BUDGET = 10000


# ---------------- DATABASE ----------------

def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    connection = get_db()
    cursor = connection.cursor()

    # Expenses table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            expense_date TEXT
        )
    """)

    # Check expense_date column
    cursor.execute("PRAGMA table_info(expenses)")
    columns = [row["name"] for row in cursor.fetchall()]

    if "expense_date" not in columns:
        cursor.execute(
            "ALTER TABLE expenses ADD COLUMN expense_date TEXT"
        )

    # Add today's date to old expenses
    cursor.execute("""
        UPDATE expenses
        SET expense_date = ?
        WHERE expense_date IS NULL OR expense_date = ''
    """, (date.today().isoformat(),))

    # Settings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY,
            budget REAL NOT NULL
        )
    """)

    cursor.execute(
        "SELECT budget FROM settings WHERE id = 1"
    )

    if cursor.fetchone() is None:
        cursor.execute(
            "INSERT INTO settings (id, budget) VALUES (1, ?)",
            (DEFAULT_BUDGET,)
        )

    connection.commit()
    connection.close()


# ---------------- HOME / DASHBOARD ----------------

@app.route("/")
def home():

    selected_month = request.args.get("month", "").strip()

    connection = get_db()
    cursor = connection.cursor()

    # Month filter
    if selected_month:

        cursor.execute("""
            SELECT *
            FROM expenses
            WHERE expense_date LIKE ?
            ORDER BY expense_date DESC, id DESC
        """, (selected_month + "%",))

    else:

        cursor.execute("""
            SELECT *
            FROM expenses
            ORDER BY expense_date DESC, id DESC
        """)

    expenses = cursor.fetchall()

    # ---------------- TOTAL ----------------

    total = sum(
        float(item["amount"])
        for item in expenses
    )

    # ---------------- CATEGORY TOTALS ----------------

    category_totals = {}

    for item in expenses:

        category = item["category"]

        category_totals[category] = (
            category_totals.get(category, 0)
            + float(item["amount"])
        )

    # ---------------- BUDGET ----------------

    cursor.execute(
        "SELECT budget FROM settings WHERE id = 1"
    )

    budget_row = cursor.fetchone()

    if budget_row:
        budget = float(budget_row["budget"])
    else:
        budget = DEFAULT_BUDGET

    remaining = budget - total

    # ---------------- BUDGET ALERT ----------------

    if total > budget:

        alert = (
            "Budget exceeded by Rs. "
            + str(round(total - budget, 2))
        )

        alert_type = "danger"

    elif budget > 0 and remaining <= budget * 0.20:

        alert = "You are close to your budget limit."

        alert_type = "warning"

    else:

        alert = "You are within your budget."

        alert_type = "success"

    # ---------------- AI INSIGHT ----------------

    if category_totals and total > 0:

        highest_category = max(
            category_totals,
            key=category_totals.get
        )

        highest_amount = category_totals[
            highest_category
        ]

        percentage = (
            highest_amount / total
        ) * 100

        if percentage >= 50:

            advice = (
                "Try to reduce spending in this category."
            )

        elif percentage >= 30:

            advice = (
                "Keep an eye on this category."
            )

        else:

            advice = (
                "Your spending is distributed across categories."
            )

        insight = (
            "Highest spending category: "
            + highest_category
            + " (Rs. "
            + str(round(highest_amount, 2))
            + "), "
            + str(round(percentage, 1))
            + "% of total spending. "
            + advice
        )

    else:

        insight = (
            "Add expenses to receive spending insights."
        )

    # ---------------- STATISTICS ----------------

    expense_count = len(expenses)

    if expense_count > 0:

        average_expense = round(
            total / expense_count,
            2
        )

        highest_expense = max(
            float(item["amount"])
            for item in expenses
        )

    else:

        average_expense = 0
        highest_expense = 0

    connection.close()

    # ---------------- SEND DATA TO HTML ----------------

    return render_template(
        "dashboard.html",

        expenses=expenses,

        total=round(total, 2),

        budget=round(budget, 2),

        remaining=round(remaining, 2),

        category_totals=category_totals,

        alert=alert,

        alert_type=alert_type,

        insight=insight,

        expense_count=expense_count,

        average_expense=average_expense,

        highest_expense=round(
            highest_expense,
            2
        ),

        selected_month=selected_month
    )


# ---------------- ADD EXPENSE ----------------

@app.route("/add", methods=["POST"])
def add_expense():

    description = request.form.get(
        "description",
        ""
    ).strip()

    amount_text = request.form.get(
        "amount",
        ""
    ).strip()

    expense_date = request.form.get(
        "expense_date",
        ""
    ).strip()

    # If date is empty
    if not expense_date:

        expense_date = date.today().isoformat()

    # Check amount
    try:

        amount = float(amount_text)

    except ValueError:

        return redirect("/")

    # Check valid data
    if not description or amount <= 0:

        return redirect("/")

    # AI category prediction
    category = predict_category(description)

    connection = get_db()

    connection.execute("""
        INSERT INTO expenses
        (description, amount, category, expense_date)
        VALUES (?, ?, ?, ?)
    """, (
        description,
        amount,
        category,
        expense_date
    ))

    connection.commit()
    connection.close()

    return redirect("/")


# ---------------- EDIT EXPENSE ----------------

@app.route("/edit/<int:expense_id>", methods=["POST"])
def edit_expense(expense_id):

    description = request.form.get(
        "description",
        ""
    ).strip()

    amount_text = request.form.get(
        "amount",
        ""
    ).strip()

    expense_date = request.form.get(
        "expense_date",
        ""
    ).strip()

    # Check amount
    try:

        amount = float(amount_text)

    except ValueError:

        return redirect("/")

    if not description or amount <= 0:

        return redirect("/")

    if not expense_date:

        expense_date = date.today().isoformat()

    # Predict category again
    category = predict_category(description)

    connection = get_db()

    connection.execute("""
        UPDATE expenses

        SET description = ?,
            amount = ?,
            category = ?,
            expense_date = ?

        WHERE id = ?
    """, (
        description,
        amount,
        category,
        expense_date,
        expense_id
    ))

    connection.commit()
    connection.close()

    return redirect("/")


# ---------------- DELETE ONE EXPENSE ----------------

@app.route("/delete/<int:expense_id>", methods=["POST"])
def delete_expense(expense_id):

    connection = get_db()

    connection.execute(
        "DELETE FROM expenses WHERE id = ?",
        (expense_id,)
    )

    connection.commit()
    connection.close()

    return redirect("/")


# ---------------- UPDATE BUDGET ----------------

@app.route("/budget", methods=["POST"])
def update_budget():

    budget_text = request.form.get(
        "budget",
        ""
    ).strip()

    try:

        budget = max(
            0,
            float(budget_text)
        )

    except ValueError:

        return redirect("/")

    connection = get_db()

    connection.execute("""
        UPDATE settings
        SET budget = ?
        WHERE id = 1
    """, (budget,))

    connection.commit()
    connection.close()

    return redirect("/")


# ---------------- RESET ALL EXPENSES ----------------

@app.route("/reset", methods=["POST"])
def reset_expenses():

    connection = get_db()

    connection.execute(
        "DELETE FROM expenses"
    )

    connection.commit()
    connection.close()

    return redirect("/")


# ---------------- EXPORT CSV ----------------

@app.route("/export")
def export_csv():

    connection = get_db()

    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            description,
            amount,
            category,
            expense_date

        FROM expenses

        ORDER BY expense_date DESC, id DESC
    """)

    expenses = cursor.fetchall()

    connection.close()

    # Create CSV in memory
    output = io.StringIO()

    writer = csv.writer(output)

    writer.writerow([
        "ID",
        "Description",
        "Amount",
        "Category",
        "Date"
    ])

    for item in expenses:

        writer.writerow([
            item["id"],
            item["description"],
            item["amount"],
            item["category"],
            item["expense_date"]
        ])

    response = Response(
        output.getvalue(),
        mimetype="text/csv"
    )

    response.headers["Content-Disposition"] = (
        "attachment; filename=expenses.csv"
    )

    return response


# ---------------- RUN APP ----------------

if __name__ == "__main__":

    init_db()

    app.run(
        debug=True,
        use_reloader=False
    )