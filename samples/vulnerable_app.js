/**
 * Sample vulnerable JavaScript code for ReleaseGuard demo.
 *
 * WARNING: This code contains INTENTIONAL security vulnerabilities.
 * DO NOT use in production.
 */

const express = require('express');
const app = express();

// XSS — unsanitized user input in response
app.get('/search', (req, res) => {
    const query = req.query.q;
    res.send(`<h1>Results for: ${query}</h1>`);
});

// SQL Injection — string concatenation in query
app.get('/user/:id', (req, res) => {
    const query = "SELECT * FROM users WHERE id = '" + req.params.id + "'";
    db.query(query);
});

// Hardcoded credentials
const DB_PASSWORD = "admin123";
const API_SECRET = "sk-prod-very-secret-key-do-not-share";

// Eval with user input
app.post('/calc', (req, res) => {
    const result = eval(req.body.expression);
    res.json({ result });
});

// Command injection
const { exec } = require('child_process');
app.get('/ping', (req, res) => {
    exec('ping -c 1 ' + req.query.host, (err, stdout) => {
        res.send(stdout);
    });
});

// Insecure cookie — no httpOnly, no secure flag
app.get('/login', (req, res) => {
    res.cookie('session', 'abc123', { httpOnly: false, secure: false });
    res.send('logged in');
});

// Open redirect
app.get('/redirect', (req, res) => {
    res.redirect(req.query.url);
});

// Path traversal
const fs = require('fs');
app.get('/file', (req, res) => {
    const content = fs.readFileSync('/uploads/' + req.query.name);
    res.send(content);
});
