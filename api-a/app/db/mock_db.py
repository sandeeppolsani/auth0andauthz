_users: list[dict] = [
    {"email": "alice@example.com", "name": "Alice Liddell", "department": "Engineering", "employee_number": "EMP001"},
    {"email": "admin@example.com", "name": "Admin User", "department": "IT", "employee_number": "EMP002"},
    {"email": "bob@example.com", "name": "Bob Smith", "department": "Sales", "employee_number": "EMP003"},
]


def get_all_users() -> list[dict]:
    """Return all user records."""
    return list(_users)


def get_user_by_email(email: str) -> dict | None:
    """Return the user record with matching email, or None if not found."""
    for user in _users:
        if user["email"] == email:
            return user
    return None


def create_user(user: dict) -> dict:
    """Append user dict to _users. Return the created record."""
    if get_user_by_email(user["email"]) is not None:
        raise ValueError(f"User with email {user['email']} already exists.")
    _users.append(user)
    return user


def update_user(email: str, updates: dict) -> dict | None:
    """Find user by email, apply updates, return updated record. Return None if not found."""
    safe_updates = {k: v for k, v in updates.items() if k != "email"}
    for user in _users:
        if user["email"] == email:
            user.update(safe_updates)
            return user
    return None
