from flask import Flask, request, jsonify, Response
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
)
from flask_cors import CORS
from database import db, migrate
from datetime import timedelta, datetime
from sqlalchemy import func
import os, csv, re, spacy
from io import StringIO
import google.generativeai as generative_ai

app = Flask(__name__)

CORS(app)

# PostgreSQL Configuration
app.config["SQLALCHEMY_DATABASE_URI"] = (
    "postgresql://postgres:root@localhost:5432/finance_tracker"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# JWT Secret Key Configuration
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "super-secret")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=60)
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=7)

db.init_app(app)
migrate.init_app(app, db)
jwt = JWTManager(app)


from models import User, Expense, Category, Budget


@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not username or not email or not password:
        return jsonify({"error": "Missing required fields"}), 400

    email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    if not re.match(email_regex, email):
        return jsonify({"error": "Invalid email format"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already exists"}), 400

    new_user = User(username=username, email=email)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User registered successfully"}), 201


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid email or password"}), 401

    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))
    return (
        jsonify(
            {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "message": "Login successful",
            }
        ),
        200,
    )


@app.route("/profile", methods=["PUT"])
@jwt_required()
def update_profile():
    user_id = get_jwt_identity()
    data = request.get_json()

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    if "username" in data:
        user.username = data["username"]

    if "email" in data:
        existing_user = User.query.filter(
            User.email == data["email"], User.id != user_id
        ).first()
        if existing_user:
            return jsonify({"error": "Email already in use"}), 400
        user.email = data["email"]

    db.session.commit()
    return jsonify({"message": "Profile updated successfully!"})


@app.route("/change-password", methods=["POST"])
@jwt_required()
def change_password():
    user_id = get_jwt_identity()
    data = request.get_json()

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    current_password = data.get("current_password")
    new_password = data.get("new_password")

    if not user.check_password(current_password):
        return jsonify({"error": "Current password is incorrect"}), 400

    user.set_password(new_password)
    db.session.commit()

    return jsonify({"message": "Password updated successfully!"})


@app.route("/protected", methods=["GET"])
@jwt_required()
def protected():
    user_id = get_jwt_identity()
    return (
        jsonify({"message": f"This is a protected route accessed by user {user_id}!"}),
        200,
    )


@app.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    user_id = get_jwt_identity()
    new_access_token = create_access_token(identity=str(user_id))

    return jsonify({"access_token": new_access_token}), 200


@app.route("/expenses", methods=["POST"])
@jwt_required()
def add_expense():
    user_id = int(get_jwt_identity())
    data = request.get_json()

    amount = data.get("amount")
    category = data.get("category")
    description = data.get("description", "")
    payment_method = data.get("payment_method")
    date_str = data.get("date", datetime.utcnow().strftime("%Y-%m-%d"))
    recurrence = data.get("recurrence")

    if not amount or not category or not payment_method:
        return (
            jsonify(
                {"error": "Missing required fields (amount, category, payment_method)"}
            ),
            400,
        )

    try:
        amount = float(amount)
        if amount <= 0:
            return jsonify({"error": "Amount must be greater than zero"}), 400
    except ValueError:
        return jsonify({"error": "Invalid amount format"}), 400

    try:
        date = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    if recurrence and recurrence not in ["daily", "weekly", "monthly", "yearly"]:
        return (
            jsonify(
                {
                    "error": "Invalid recurrence type. Use daily, weekly, monthly, or yearly"
                }
            ),
            400,
        )

    new_expense = Expense(
        user_id=user_id,
        amount=amount,
        category=category,
        description=description,
        payment_method=payment_method,
        date=date,
        recurrence=recurrence,
    )
    db.session.add(new_expense)
    db.session.commit()

    return (
        jsonify({"message": "Expense added successfully!", "recurrence": recurrence}),
        201,
    )


@app.route("/expenses", methods=["GET"])
@jwt_required()
def get_expenses():
    user_id = int(get_jwt_identity())
    today = datetime.utcnow().date()

    expenses = Expense.query.filter_by(user_id=user_id).all()

    new_expenses = []
    for expense in expenses:
        if expense.recurrence:
            last_expense_date = expense.date.date()

            if expense.recurrence == "daily":
                next_date = last_expense_date + timedelta(days=1)
            elif expense.recurrence == "weekly":
                next_date = last_expense_date + timedelta(weeks=1)
            elif expense.recurrence == "monthly":
                next_date = last_expense_date.replace(day=1) + timedelta(days=32)
                next_date = next_date.replace(day=1)
            elif expense.recurrence == "yearly":
                next_date = last_expense_date.replace(year=last_expense_date.year + 1)
            else:
                continue

            if next_date <= today:
                new_expense = Expense(
                    user_id=expense.user_id,
                    amount=expense.amount,
                    category=expense.category,
                    description=expense.description,
                    date=next_date,
                    payment_method=expense.payment_method,
                    recurrence=expense.recurrence,
                )
                db.session.add(new_expense)
                new_expenses.append(new_expense)

    if new_expenses:
        db.session.commit()

    expenses = Expense.query.filter_by(user_id=user_id).all()

    expenses_list = [
        {
            "id": exp.id,
            "amount": exp.amount,
            "category": exp.category,
            "description": exp.description,
            "date": exp.date.strftime("%Y-%m-%d"),
            "payment_method": exp.payment_method,
            "recurrence": exp.recurrence,
        }
        for exp in expenses
    ]

    return jsonify({"expenses": expenses_list}), 200


@app.route("/expenses/<int:expense_id>", methods=["PUT"])
@jwt_required()
def update_expense(expense_id):
    user_id = int(get_jwt_identity())
    expense = Expense.query.get(expense_id)

    if not expense:
        return jsonify({"error": "Expense not found"}), 404

    if expense.user_id != user_id:
        return jsonify({"error": "Unauthorized to update this expense"}), 403

    data = request.get_json()

    if "amount" in data:
        try:
            amount = float(data["amount"])
            if amount <= 0:
                return jsonify({"error": "Amount must be greater than zero"}), 400
            expense.amount = amount
        except ValueError:
            return jsonify({"error": "Invalid amount format"}), 400

    if "category" in data:
        expense.category = data["category"]

    if "description" in data:
        expense.description = data["description"]

    if "payment_method" in data:
        expense.payment_method = data["payment_method"]

    db.session.commit()

    return jsonify({"message": "Expense updated successfully!"}), 200


@app.route("/expenses/<int:expense_id>", methods=["DELETE"])
@jwt_required()
def delete_expense(expense_id):
    user_id = int(get_jwt_identity())
    expense = Expense.query.get(expense_id)

    if not expense:
        return jsonify({"error": "Expense not found"}), 404

    if expense.user_id != user_id:
        return jsonify({"error": "Unauthorized to delete this expense"}), 403

    db.session.delete(expense)
    db.session.commit()

    return jsonify({"message": "Expense deleted successfully!"}), 200


@app.route("/expenses/summary", methods=["GET"])
@jwt_required()
def get_summary():
    user_id = int(get_jwt_identity())

    # Total Expenses
    total_expenses = (
        db.session.query(func.sum(Expense.amount)).filter_by(user_id=user_id).scalar()
        or 0
    )

    # Monthly Breakdown
    monthly_expenses = (
        db.session.query(
            func.to_char(Expense.date, "YYYY-MM").label("month"),
            func.sum(Expense.amount),
        )
        .filter_by(user_id=user_id)
        .group_by("month")
        .all()
    )

    monthly_breakdown = {month: float(total) for month, total in monthly_expenses}

    # Top 3 Spending Categories
    top_categories = (
        db.session.query(Expense.category, func.sum(Expense.amount))
        .filter_by(user_id=user_id)
        .group_by(Expense.category)
        .order_by(func.sum(Expense.amount).desc())
        .limit(3)
        .all()
    )

    top_categories_list = [
        {"category": cat, "total_spent": float(total)} for cat, total in top_categories
    ]

    return (
        jsonify(
            {
                "total_expenses": float(total_expenses),
                "monthly_breakdown": monthly_breakdown,
                "top_spending_categories": top_categories_list,
            }
        ),
        200,
    )


@app.route("/budget", methods=["POST"])
@jwt_required()
def set_budget():
    user_id = int(get_jwt_identity())
    data = request.get_json()

    amount = data.get("amount")
    month = data.get("month")

    if not amount or not month:
        return jsonify({"error": "Missing required fields (amount, month)"}), 400

    try:
        amount = float(amount)
        if amount <= 0:
            return jsonify({"error": "Budget must be greater than zero"}), 400
    except ValueError:
        return jsonify({"error": "Invalid budget amount"}), 400

    existing_budget = Budget.query.filter_by(user_id=user_id, month=month).first()
    if existing_budget:
        existing_budget.amount = amount
    else:
        new_budget = Budget(user_id=user_id, amount=amount, month=month)
        db.session.add(new_budget)

    db.session.commit()
    return (
        jsonify(
            {"message": "Budget set successfully!", "month": month, "amount": amount}
        ),
        201,
    )


@app.route("/budget/status", methods=["GET"])
@jwt_required()
def check_budget_status():
    user_id = int(get_jwt_identity())
    requested_month = request.args.get("month", datetime.utcnow().strftime("%Y-%m"))

    # print(f"DEBUG: Checking budget for user {user_id}, month {requested_month}")

    budget = Budget.query.filter(
        Budget.user_id == user_id, Budget.month == requested_month
    ).first()

    if not budget:
        return jsonify({"message": "No budget set for this month."}), 200

    # print(f"DEBUG: Found budget of {budget.amount}")

    total_expenses = (
        db.session.query(func.sum(Expense.amount))
        .filter(
            Expense.user_id == user_id,
            func.to_char(Expense.date, "YYYY-MM") == requested_month,
        )
        .scalar()
        or 0
    )

    remaining_budget = budget.amount - total_expenses
    exceeded = total_expenses > budget.amount

    return (
        jsonify(
            {
                "month": requested_month,
                "budget": budget.amount,
                "total_expenses": total_expenses,
                "remaining_budget": remaining_budget,
                "exceeded": exceeded,
            }
        ),
        200,
    )


@app.route("/export", methods=["GET"])
@jwt_required()
def export_expenses():
    user_id = get_jwt_identity()
    expenses = Expense.query.filter_by(user_id=user_id).all()

    if not expenses:
        return jsonify({"message": "No expenses found!"}), 404

    output = StringIO()
    writer = csv.writer(output)

    writer.writerow(
        ["ID", "Amount", "Category", "Description", "Date", "Payment Method"]
    )

    for expense in expenses:
        writer.writerow(
            [
                expense.id,
                expense.amount,
                expense.category,
                expense.description,
                expense.date,
                expense.payment_method,
            ]
        )

    output.seek(0)

    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=expenses.csv"},
    )


# Loading NLP model (spaCy)
nlp = spacy.load("en_core_web_sm")

# Gemini API Key
generative_ai.configure(api_key="AIzaSyA6zW-XyYl8n4LLMR0aN3U565AJX1UFZgQ")


@app.route("/chatbot", methods=["POST"])
@jwt_required()
def chatbot():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    user_query = data.get("query", "").lower()

    if not user_query:
        return jsonify({"error": "No query provided"}), 400

    doc = nlp(user_query)

    if "expense" in user_query or "spending" in user_query or "budget" in user_query:
        model = generative_ai.GenerativeModel(model_name="gemini-pro")
        prompt = f"Interpret this expense-related query: {user_query}"

        response = model.generate_content(prompt)

        ai_response = response.text.strip()
        # print(f"DEBUG: AI Response: {ai_response}")

        if "total expenses for" in ai_response:
            month = re.findall(r"\d{4}-\d{2}", ai_response)
            query_month = month[0] if month else datetime.utcnow().strftime("%Y-%m")

            total_expenses = (
                db.session.query(func.sum(Expense.amount))
                .filter(func.to_char(Expense.date, "YYYY-MM") == query_month)
                .filter(Expense.user_id == user_id)
                .scalar()
                or 0
            )
            return jsonify(
                {
                    "message": f"Your total expenses for {query_month} are {total_expenses}."
                }
            )

        elif "highest expense this month" in ai_response:
            highest_expense = (
                db.session.query(Expense.category, func.max(Expense.amount))
                .filter(Expense.user_id == user_id)
                .filter(
                    func.date_trunc("month", Expense.date)
                    == func.date_trunc("month", func.current_date())
                )
                .group_by(Expense.category)
                .first()
            )
            category, amount = highest_expense or ("None", 0)
            return jsonify(
                {
                    "message": f"Your highest expense this month is {amount} in {category}."
                }
            )

        elif "list all expenses in category" in ai_response:
            category_match = re.search(r"in the (\w+) category", ai_response)
            category = category_match.group(1) if category_match else None

            if category:
                expenses = Expense.query.filter_by(
                    user_id=user_id, category=category
                ).all()
                expense_list = [
                    {"amount": exp.amount, "date": exp.date.strftime("%Y-%m-%d")}
                    for exp in expenses
                ]

                return jsonify({"category": category, "expenses": expense_list})
            return jsonify({"error": "Could not determine category."}), 400

    if "set" in user_query and "budget" in user_query:
        amount = re.findall(r"\d+", user_query)
        if amount:
            budget_amount = float(amount[0])
            current_month = datetime.utcnow().strftime("%Y-%m")

            existing_budget = Budget.query.filter(Budget.user_id == user_id).first()

            if existing_budget:
                existing_budget.amount = budget_amount
                existing_budget.month = current_month
                db.session.commit()
                return jsonify(
                    {
                        "message": f"Budget updated to {budget_amount} for {current_month}!"
                    }
                )
            else:
                new_budget = Budget(
                    user_id=user_id, amount=budget_amount, month=current_month
                )
                db.session.add(new_budget)
                db.session.commit()
                return jsonify(
                    {"message": f"Budget set to {budget_amount} for {current_month}!"}
                )

        return jsonify({"error": "Could not understand budget amount."}), 400

    return jsonify(
        {
            "message": "I'm not sure how to answer that. Try asking about budget or expenses."
        }
    )


if __name__ == "__main__":
    app.run(debug=True, port=5001)
