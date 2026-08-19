FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY bridge.py entrypoint.sh .
RUN chmod +x entrypoint.sh

# uid/gid 10001 matches the "openhands" host user so the process can read
# the bind-mounted api-key.txt (mode 600, owned by uid/gid 10001) without
# widening that file's permissions. Container itself starts as root --
# entrypoint.sh fixes up /data ownership then drops to this user before
# exec'ing the bridge.
RUN groupadd -g 10001 openhands && useradd -u 10001 -g 10001 -M openhands

ENTRYPOINT ["./entrypoint.sh"]
