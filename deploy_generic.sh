#!/bin/sh

gcloud_account=mediainnovationhub@gmail.com
gcloud_project=notifynow-app-405611
image_tag=us.gcr.io/${gcloud_project}/notifynow-app-front-${tenant}
git_hash=$(git rev-parse --short HEAD)
cloud_run_service_name=notifynow-app-front-${tenant}

export DOCKER_BUILDKIT=0
export COMPOSE_DOCKER_CLI_BUILD=0
echo "🛠 Building image..."
echo "  🏷 tag:      ${image_tag}"
echo "  🏷 git hash: ${git_hash}"
echo "  📄 config:   ${config}"
docker build --platform linux/amd64 -t ${image_tag} --build-arg CONFIG_ARG=${config} --quiet .

gcloud_account_to_restore=$(gcloud config get-value account)
gcloud_project_to_restore=$(gcloud config get-value project)

echo "💾 Setting temporary values..."
echo "  📤 gcloud account=${gcloud_account}"
echo "  📤 gcloud project=${gcloud_project}"
gcloud config set account ${gcloud_account}
gcloud config set project ${gcloud_project}

echo "🚀 Pushing image..."

echo "  🏷 tag:      ${image_tag}"
echo "  🏷 git hash: ${git_hash}"
docker push ${image_tag} --quiet
docker push ${image_tag}:${git_hash} --quiet

echo "🚀 Deploying image..."
echo "  💻 instance: ${cloud_run_service_name}"

services_list=$(gcloud run services list)
found_existing=false
while IFS= read -r line; do
  existing_service_name="$(echo ${line} | tr -s ' ' | cut -d' ' -f2)"
  if [ "$existing_service_name" = "$cloud_run_service_name" ]; then
    found_existing=true
    break
  fi
done <<< "$services_list"

if $found_existing; then
  echo "  🟩 Existing service detected, keeping env variables"
  gcloud run services update ${cloud_run_service_name} --image=${image_tag}:latest --region=us-central1 --labels="tenant=${tenant}"
else
  echo "  🟦 New service detected, setting empty env variables"
  gcloud run deploy ${cloud_run_service_name} --allow-unauthenticated --image=${image_tag}:latest --max-instances=1 --labels="tenant=${tenant}" --region=us-central1 --set-env-vars="DB_NAME=<SET_DB_NAME_HERE>,DB_PASSWORD=<SET_DB_PASSWORD_HERE>,DB_USERNAME=<SET_DB_USERNAME_HERE>,FLASK_SECRET_KEY=<SET_FLASK_SECRET_KEY_HERE>,DB_SECRETS_KEY=<SET_DB_SECRETS_KEY_HERE>,APP_SECRET_KEY=<APP_SECRET_KEY_HERE>"
fi

echo "💾 Restoring previous values..."
echo "  📥 gcloud account=${gcloud_account_to_restore}"
echo "  📥 gcloud project=${gcloud_project_to_restore}"
gcloud config set account ${gcloud_account_to_restore}
gcloud config set project ${gcloud_project_to_restore}
