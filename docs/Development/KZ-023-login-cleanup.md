# KZ-023 Login Cleanup

The login page must not display default credentials in production.

Current behavior:
- Username field is empty.
- Password field is empty.
- No default credential hint is rendered below the login form.
- Login still posts `{ username, password }` to `/auth/login`.
