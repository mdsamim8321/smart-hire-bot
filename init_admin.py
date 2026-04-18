import mysql.connector

def init_db():
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="mdsamim9128",
            database="ai_interview"
        )
        cursor = db.cursor()

        # 1. Add 'role' column if not exists
        print("Checking for 'role' column...")
        cursor.execute("SHOW COLUMNS FROM users LIKE 'role'")
        if not cursor.fetchone():
            print("Adding 'role' column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'user'")
            db.commit()
        
        # 2. Check if admin exists, if not create, if yes update
        admin_email = "admin@smarthire.ai"
        admin_pass = "admin123"
        
        cursor.execute("SELECT * FROM users WHERE email=%s", (admin_email,))
        if cursor.fetchone():
            print(f"Updating existing user {admin_email} to admin...")
            cursor.execute("UPDATE users SET role='admin', password=%s WHERE email=%s", (admin_pass, admin_email))
        else:
            print(f"Creating new admin user {admin_email}...")
            cursor.execute(
                "INSERT INTO users (full_name, email, password, role, field) VALUES (%s, %s, %s, %s, %s)",
                ("System Admin", admin_email, admin_pass, "admin", "Management")
            )
        
        db.commit()
        print("Database initialization successful!")
        print(f"\nAdmin Credentials:")
        print(f"Email: {admin_email}")
        print(f"Password: {admin_pass}")

        cursor.close()
        db.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    init_db()
