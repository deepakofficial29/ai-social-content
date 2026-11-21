# Production Operations Checklist

- [ ] Set `APP_ENV=production` and `DEBUG=false`.
- [ ] Set explicit CORS origins.
- [ ] Configure provider credentials through the deployment secret manager.
- [ ] Back up database and media volumes.
- [ ] Confirm `/api/v1/health` and `/api/v1/ready`.
- [ ] Confirm FFmpeg/FFprobe availability.
- [ ] Confirm upload size and media duration limits.
- [ ] Review request and provider logs for sensitive content.
- [ ] Restrict network access because authentication is not implemented.
- [ ] Restore from a backup in a controlled test.
- [ ] Run automated tests before deployment.
