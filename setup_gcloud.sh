#!/usr/bin/env zsh

set -euo pipefail
set -x

# source staging-env.sh

# gcloud config list
# gcloud config configurations list
gcloud config configurations create staging || gcloud config configurations activate staging

gcloud config set project "${PROJECT_ID}"
gcloud config set account "$(whoami)@google.com"

# [api_client_overrides]
gcloud config set api_client_overrides/compute staging_v1
# gcloud config set api_client_overrides/compute staging_alpha

# [api_endpoint_overrides]
# gcloud meta apis list --filter name=compute
gcloud config set api_endpoint_overrides/compute "https://www.googleapis.com/compute/staging_v1/"
# gcloud config set api_endpoint_overrides/container "https://${DEV_SANDBOX}.sandbox.googleapis.com/"
gcloud config set api_endpoint_overrides/networksecurity "https://staging-networksecurity.sandbox.googleapis.com/"
gcloud config set api_endpoint_overrides/networkservices https://staging-networkservices.sandbox.googleapis.com/
gcloud config set api_endpoint_overrides/run https://staging-run.sandbox.googleapis.com/

# [container]
gcloud config set container/use_application_default_credentials true

# [compute]
gcloud config set compute/zone "us-central1a"

# [privateca]
# gcloud config set privateca/location "${ROOT_CA_POOL_LOCATION}"

set +x
echo
echo "To return to non-staging config:"
echo "gcloud config configurations activate default"
echo
echo "To authorize on GKE cluster:"
echo "gcloud auth application-default login"
echo "gcloud container clusters get-credentials ${CLUSTER_NAME} --zone ${ZONE_PRIMARY}"