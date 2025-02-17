# Finance Tracker API

This is a **Flask-based Finance Tracker API** that allows users to **manage their expenses, track spending, set budgets, and export data** securely.

### API Documentation: https://documenter.getpostman.com/view/38806896/2sAYXEFdr7

## 📌 API Endpoints Overview

| Endpoint            | Method   | Description                                      | Auth Required |
|---------------------|---------|--------------------------------------------------|--------------|
| `/register`        | `POST`  | Register a new user                              | ❌ No |
| `/login`           | `POST`  | Login and get JWT token                          | ❌ No |
| `/expenses`        | `POST`  | Add a new expense                                | ✅ Yes |
| `/expenses`        | `GET`   | Retrieve expenses (filter by category/date)      | ✅ Yes |
| `/expenses/<id>`   | `PUT`   | Update an expense                               | ✅ Yes |
| `/expenses/<id>`   | `DELETE`| Delete an expense                               | ✅ Yes |
| `/expenses/summary`| `GET`   | Get total expenses, breakdown & top categories   | ✅ Yes |
| `/budget`          | `POST`  | Set a monthly budget                             | ✅ Yes |
| `/budget/status`   | `GET`   | Check if budget is exceeded                     | ✅ Yes |
| `/export`          | `GET`   | Download expenses as CSV                        | ✅ Yes |
| `/chatbot`         | `POST`  | Chatbot to interact with expenses/budget queries | ✅ Yes |

## 🚀 Features Implemented

### 1. **User Authentication**
- User registration & login
- JWT-based authentication
- Password hashing & validation
- Secure token expiration & refresh tokens

### 2. **Expense Management**
- Add, update, and delete expenses
- Retrieve expenses with filters:
  - By **category**
  - By **date range**
- Only **owners** can modify or delete their expenses

### 3. **Expense Statistics & Budgeting**
- **Summary Statistics**
  - Total expenses
  - Monthly breakdown
  - Top 3 spending categories
- **Budgeting System**
  - Users can set a **monthly budget**
  - API **warns if expenses exceed the budget**

### 4. **Recurring Expenses**
- Store **recurrence details** (daily, weekly, monthly, yearly)
- Automate the creation of recurring expenses

### 5. **Export Expenses**
- Download expenses in **CSV format**

### 6. **User Profile Management**
- Update profile information (username, email)
- Change password securely

### 7. **Error Handling & Security**
- **Proper error handling**:
  - Invalid authentication token
  - Missing/invalid request fields
  - Unauthorized access to expenses
- **Security Enhancements**:
  - Strong password hashing
  - CORS support for frontend integration
  - Input validation 

### 8. **Chatbot for Expense/Budget Queries**
- The `/chatbot` endpoint allows users to interact with an **AI-powered assistant** for expense-related inquiries.
  - **Expenses-related queries** can include:
    - Total expenses for a month
    - Highest expense category for the current month
    - Listing expenses by category
  - **Budget-related queries** include setting or updating a monthly budget.
