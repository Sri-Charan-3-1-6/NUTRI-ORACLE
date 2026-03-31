#!/bin/bash
set -e

echo "Deploying NUTRI-ORACLE to Google Cloud Run..."

export PROJECT_ID=$(gcloud config get-value project)
if [ -z "$PROJECT_ID" ]; then
    echo "Error: Google Cloud project ID not found. Please set it using 'gcloud config set project [PROJECT_ID]'"
    exit 1
fi
echo "Using Project ID: $PROJECT_ID"

echo "Enabling necessary APIs..."
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com

echo "Submitting build to Cloud Build..."
gcloud builds submit --config cloudbuild.yaml .

echo "Deployment complete! Fetching service URL..."
gcloud run services describe nutri-oracle --region asia-south1 --format 'value(status.url)'
