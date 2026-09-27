import sqlite3
import re

# 1. Update Database
try:
    conn = sqlite3.connect('quranflow.db')
    conn.execute("ALTER TABLE users ADD COLUMN gender VARCHAR(20) DEFAULT 'unspecified';")
    conn.commit()
    print("Altered users table successfully.")
except Exception as e:
    print(f"DB Note: {e}")
finally:
    conn.close()

# 2. Update app/models/user.py
user_py = r"app\models\user.py"
with open(user_py, "r", encoding="utf-8") as f:
    content = f.read()

if "gender:" not in content:
    content = content.replace(
        "role: Mapped[str] = mapped_column(String(20), nullable=False, default=\"user\")",
        "role: Mapped[str] = mapped_column(String(20), nullable=False, default=\"user\")\n    gender: Mapped[str] = mapped_column(String(20), nullable=False, default=\"unspecified\")"
    )
    with open(user_py, "w", encoding="utf-8") as f:
        f.write(content)
    print("Updated user.py")

# 3. Update app/schemas/auth.py
auth_py = r"app\schemas\auth.py"
with open(auth_py, "r", encoding="utf-8") as f:
    content = f.read()

if "gender:" not in content:
    content = content.replace(
        "password: str",
        "password: str\n    gender: str = \"unspecified\""
    )
    with open(auth_py, "w", encoding="utf-8") as f:
        f.write(content)
    print("Updated auth.py")

# 4. Update app/routes/auth.py to include gender on creation
auth_route = r"app\routes\auth.py"
with open(auth_route, "r", encoding="utf-8") as f:
    content = f.read()

if "gender=" not in content:
    content = content.replace(
        "password_hash=hashed_password,",
        "password_hash=hashed_password,\n        gender=req.gender,"
    )
    with open(auth_route, "w", encoding="utf-8") as f:
        f.write(content)
    print("Updated routes/auth.py")

# 5. Update app/schemas/user.py to expose gender in response
user_schema = r"app\schemas\user.py"
with open(user_schema, "r", encoding="utf-8") as f:
    content = f.read()

if "gender:" not in content:
    content = content.replace(
        "role: str",
        "role: str\n    gender: str"
    )
    with open(user_schema, "w", encoding="utf-8") as f:
        f.write(content)
    print("Updated schemas/user.py")

# 6. Update app/routes/admin.py for CSV Download
admin_py = r"app\routes\admin.py"
with open(admin_py, "r", encoding="utf-8") as f:
    content = f.read()

if "/users/csv" not in content:
    csv_route = """
@router.get("/users/csv")
def download_users_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    import csv
    import io
    from fastapi.responses import StreamingResponse
    
    users = db.query(User).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Name", "Email", "Phone", "Role", "Gender", "Created At"])
    for u in users:
        writer.writerow([
            u.id, u.full_name, u.email, u.phone or "", u.role, u.gender, u.created_at.strftime("%Y-%m-%d %H:%M:%S")
        ])
    
    output.seek(0)
    headers = {
        "Content-Disposition": 'attachment; filename="users_export.csv"'
    }
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers=headers)
"""
    content += "\n" + csv_route
    with open(admin_py, "w", encoding="utf-8") as f:
        f.write(content)
    print("Updated routes/admin.py")

