# Expense Tracker API

This is a **Flask-based Expense Tracker API** that allows users to **manage their expenses, track spending, set budgets, and export data** securely.

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