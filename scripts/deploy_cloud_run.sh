#!/usr/bin/env bash
set -euo pipefail

# Script to deploy ip-matchmaker backend to Google Cloud Run
# Usage: ./scripts/deploy_cloud_run.sh [PROJECT_ID] [REGION]

PROJECT_ID="${1:-${GOOGLE_CLOUD_PROJECT:-ip-matchmaker}}"
REGION="${2:-us-central1}"
SERVICE_NAME="patent-agent"

echo "=== Deploying ${SERVICE_NAME} to Google Cloud Run ==="
echo "Project ID: ${PROJECT_ID}"
echo "Region:     ${REGION}"

if ! command -v gcloud &> /dev/null; then
    echo "ERROR: gcloud CLI is not installed or not in PATH."
    exit 1
fi

if [ -z "${GEMINI_API_KEY:-}" ]; then
    echo "WARNING: GEMINI_API_KEY environment variable is not set locally."
    echo "Ensure it is provided or set in Secret Manager / Cloud Run environment."
fi

gcloud config set project "${PROJECT_ID}"

echo "1. Enabling required Google Cloud APIs..."
gcloud services enable \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    bigquery.googleapis.com

echo "2. Deploying to Cloud Run..."
cd backend
gcloud run deploy "${SERVICE_NAME}" \
    --source . \
    --region "${REGION}" \
    --allow-unauthenticated \
    --max-instances 1 \
    --memory 1Gi \
    --cpu 1 \
    --set-env-vars "GEMINI_MODEL=gemini-3.5-flash,USE_MOCK_BIGQUERY=false,GOOGLE_CLOUD_PROJECT=${PROJECT_ID}"

SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" --region "${REGION}" --format 'value(status.url)')

echo "=== Deployment Complete ==="
echo "Service URL: ${SERVICE_URL}"
echo "Health Check: ${SERVICE_URL}/health"

echo "Testing /health..."
curl -s "${SERVICE_URL}/health" | jq . || curl -s "${SERVICE_URL}/health"
