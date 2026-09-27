import re

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

# 3. Update app/schemas/user.py (This is where auth schema is typically kept too, or check if auth.py exists, wait I checked it didn't. Let's see what schemas exist: user.py)
user_schema = r"app\schemas\user.py"
with open(user_schema, "r", encoding="utf-8") as f:
    content = f.read()

# Update UserCreate schema
if "gender: str" not in content:
    content = content.replace(
        "password: str",
        "password: str\n    gender: str = \"unspecified\""
    )
    content = content.replace(
        "role: str",
        "role: str\n    gender: str"
    )
    with open(user_schema, "w", encoding="utf-8") as f:
        f.write(content)
    print("Updated schemas/user.py")

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
    from app.models.user import User
    
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
