# Auth Testing Playbook (SewaKontrak Pro)

## Step 1: MongoDB Verification
```
mongosh
use test_database
db.users.find({role: "admin"}).pretty()
db.users.findOne({role: "admin"}, {password_hash: 1})
```
Verify: bcrypt hash starts with `$2b$`, and indexes exist on users.email (unique), login_attempts.identifier, login_attempts.email, password_reset_tokens.expires_at (TTL), password_reset_tokens.token_hash (unique), password_reset_requests.email, password_reset_requests.created_at (TTL).

## Step 2: API Testing
```
curl -c cookies.txt -X POST http://localhost:8001/api/auth/login -H "Content-Type: application/json" -d '{"email":"dikhawilham77@gmail.com","password":"SewaKontrak123!"}'
cat cookies.txt
curl -b cookies.txt http://localhost:8001/api/auth/me
```
Login should return the user object and set `access_token` + `refresh_token` cookies. The `/me` call should return the same user using those cookies.

## Step 3: Password Reset
**Do this first, before any request below.** Set `FRONTEND_URL="http://localhost:3000"` in `/app/backend/.env` and `sudo supervisorctl restart backend`. That loopback origin makes `send_password_reset_email` take the documented fallback and write the full reset link to the backend log — the only way to obtain a test token. **Restore the real https origin and restart again when Step 3 is finished.**

1. Register the test account:
```
curl -X POST http://localhost:8001/api/auth/register -H "Content-Type: application/json" -d '{"email":"resettest@example.org","password":"Reset123!","name":"Reset Test"}'
```

2. Enumeration parity — one registered address against one that is not:
```
curl -i -X POST http://localhost:8001/api/auth/forgot-password -H "Content-Type: application/json" -d '{"email":"resettest@example.org"}'
curl -i -X POST http://localhost:8001/api/auth/forgot-password -H "Content-Type: application/json" -d '{"email":"nobody@nowhere.test"}'
```
Both responses must be byte-identical in status line and body. In mongosh confirm the registered address created exactly one `password_reset_tokens` document and the unregistered one created none, and that it holds a 64-character `token_hash` with the raw token nowhere in it:
```
db.password_reset_tokens.find({}, {token_hash: 1, email: 1, used: 1}).pretty()
```

3. Complete the reset using the link the step-2 request wrote to the backend log. Verify all three: the new password logs in, the old one does not, and reusing the same link fails.

4. Throttle — register a **fresh** address for this, e.g. `throttle@example.org`. Issue six forgot-password requests for the fresh address and confirm only the first five create a `password_reset_tokens` document — all six HTTP responses must still be the identical generic 200.

5. Lockout clearance: fail login 5 times to trigger the 15-minute lockout, complete a reset, then log in immediately with the new password — it must succeed rather than report a lockout.
