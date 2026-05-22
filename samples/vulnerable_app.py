"""Sample vulnerable Python code for ReleaseGuard demo.

WARNING: This code contains INTENTIONAL security vulnerabilities.
DO NOT use in production.
"""

import hashlib
import os
import subprocess
import sqlite3


# SQL Injection — string formatting in query
def get_user(username):
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    return cursor.fetchone()


# Command Injection — unsanitized input in shell command
def run_report(report_name):
    os.system(f"generate_report {report_name}")


# Hardcoded secret
API_KEY = "sk-live-abcdef1234567890abcdef1234567890"
DATABASE_PASSWORD = "super_secret_password_123"


# Weak hashing — MD5 for passwords
def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()


# Path traversal — user input in file path
def read_file(filename):
    with open(f"/data/uploads/{filename}", "r") as f:
        return f.read()


# Subprocess with shell=True
def ping_host(host):
    result = subprocess.run(f"ping -c 1 {host}", shell=True, capture_output=True)
    return result.stdout


# Insecure deserialization
import pickle

def load_data(data_bytes):
    return pickle.loads(data_bytes)


# SSRF — unvalidated URL
import urllib.request

def fetch_url(url):
    return urllib.request.urlopen(url).read()


# Eval with user input
def calculate(expression):
    return eval(expression)


# Hardcoded JWT secret
JWT_SECRET = "my-super-secret-jwt-key"

def create_token(payload):
    import jwt
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")
