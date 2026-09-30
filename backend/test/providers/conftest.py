import os

# These tests exercise the hackathon agent's API, which the product disables by default.
os.environ["NEXUS_LEGACY_API_ENABLED"] = "1"
