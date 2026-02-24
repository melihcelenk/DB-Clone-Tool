# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 0.2.x   | :white_check_mark: |
| < 0.2   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

1. **Do NOT open a public issue**
2. Email: **info@melihcelenk.com** with the subject `[SECURITY] DB Clone Tool`
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We will acknowledge your report within **48 hours** and work on a fix.

## Security Considerations

### Password Storage

Connection passwords in `config.local/connections.json` are stored using **base64 encoding only**. This is **not encryption** - it is simple obfuscation to prevent casual reading.

**Recommendations:**
- Keep `config.local/` directory secure with appropriate file permissions
- Do not share `config.local/connections.json` publicly
- For production/shared environments, use environment variables or a proper secret manager
- The `config.local/` directory is excluded from version control by default

### Network Security

- The application listens on all interfaces (`0.0.0.0`) by default
- **No built-in authentication** - do not expose directly to the internet
- For production deployments, use a reverse proxy (nginx/traefik) with:
  - HTTPS/TLS termination
  - Authentication middleware
  - IP whitelisting

### Docker Security

- Container runs as non-root user (`appuser`)
- MySQL binaries are copied from official MySQL image
- No secrets are baked into the Docker image
- Configuration is mounted via volumes at runtime

## Best Practices

1. Run behind a reverse proxy with HTTPS
2. Restrict network access to trusted hosts only
3. Use strong MySQL credentials
4. Regularly update dependencies (`pip install --upgrade`)
5. Monitor application logs for suspicious activity
