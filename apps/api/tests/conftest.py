import os

# The production application intentionally requires RAEBURN_API_KEY. Tests provide
# an explicit non-production value so importing the app never depends on a
# developer machine's environment or an unsafe runtime default.
os.environ.setdefault("RAEBURN_API_KEY", "test-only-api-key")
