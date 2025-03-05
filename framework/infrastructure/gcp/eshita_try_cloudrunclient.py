import google.auth
import time
from googleapiclient import discovery
from googleapiclient.discovery import build
from googleapiclient.discovery import Resource
import os
from google.api_core.client_options import ClientOptions


def deploy_cloud_run_from_discovery(
    project_id: str,
    location: str,
    service_name: str,
    server_target: str,
    mesh: str,
    image_uri: str,
    service_account: str,
    grpc_target_port: int,
    discovery_url: str,
    max_instances: int = 10,
    min_instances: int = 0,
    cpu_limit: str = "1000m",
    memory_limit: str = "256Mi",
    timeout: str = "300s"
):
    """
    Deploys a Cloud Run service using a custom discovery document.

    Args:
        project_id: The ID of the Google Cloud project.
        location: The region or location where the service should be deployed.
        service_name: The name of the Cloud Run service.
        image_uri: The URI of the container image to deploy.
        service_account: The service account to use for the Cloud Run service.
        grpc_target_port: The port that the gRPC server inside the container listens on.
        discovery_url: The URL of the discovery document.
        max_instances: The maximum number of instances for the service.
        min_instances: the minimum number of instances for the service.
        cpu_limit: The CPU limit for each instance.
        memory_limit: The memory limit for each instance.
        timeout: The timeout for the service.
    """
    try:
        credentials, _ = google.auth.default()
        client_options = {"api_endpoint": "https://us-central1-staging-run.sandbox.googleapis.com"}
        service:Resource = build('run', 'v2', discoveryServiceUrl=discovery_url,developerKey="AIzaSyDp_H904U0np3Zt_OGqeAg_O9KtLD9z5Sg",credentials=credentials,client_options=client_options)
        # developerKey="AIzaSyAV2c0JJI1II7_nlVzBhmgWtxXQWX4e71A"
        service_body = {}

        service_body={
            "launch_stage":"ALPHA",
            "template":
                      {
                        "containers": [
                            {
                                "image": image_uri,
                                "ports": [{"containerPort": grpc_target_port, "name": "h2c"}],
                                # "resources": {
                                #     "limits": {
                                #         "cpu": cpu_limit,
                                #         "memory": memory_limit
                                #     }
                                # },
                                "args": [f"--server={server_target}", "--secure_mode=true",],
                                "env":[
                                    {
                                        "name":"GRPC_EXPERIMENTAL_XDS_AUTHORITY_REWRITE",
                                        "value":"true"
                                    },
                                    {
                                        "name":"GRPC_EXPERIMENTAL_XDS_SYSTEM_ROOT_CERTS",
                                        "value":"true"
                                    },
                                    {
                                        "name":"GRPC_EXPERIMENTAL_XDS_GCP_AUTHENTICATION_FILTER",
                                        "value":"true"
                                    },
                                    {
                                        "name":"is-trusted-xds-server-experimental",
                                        "value":"true"
                                    },
                                    {
                                        "name":"GRPC_XDS_BOOTSTRAP_CONFIG",
                                        "value":"/tmp/grpc-xds/td-grpc-bootstrap.json"
                                    }
                                ]
                            }
                        ],
                        "vpcAccess": {
                            "networkInterfaces": [
                                {
                                 "network": "default",
                               "subnetwork": "default",
                                 }
                              ]
                           },
                    "service_mesh":{
                        "mesh":mesh,
                        "dataplaneMode":"proxyless-grpc"
                    }
                },
                "ingress": "INGRESS_TRAFFIC_ALL",
                "traffic": [{"type": "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST", "percent": 100}],
        }
                # "traffic": [{"percent": 100},],
        # e_projects=service.projects().locations().services()
        # print("emchandwani request locations %T",e_projects)
        # request = e_projects.create(parent=f"projects/{project_id}/locations/{location}", body=service_body)
        request = service.projects().locations().services().create(parent=f"projects/{project_id}/locations/{location}", serviceId=service_name, body=service_body)
        print("emchandwani request executed , %T",request)
        response = request.execute()
        print("emchandwani rresponse received",response)

        print(f"Deploying Cloud Run service '{service_name}'...")
        while True:
            get_request = service.projects().locations().services().get(
                name=f"projects/{project_id}/locations/{location}/services/{service_name}"
            )
            get_response = get_request.execute()

            if not get_response.get("reconciling", False):  # Wait until reconciling is False
                print(f"Cloud Run service '{service_name}' is ready.")
                print(f"Service URL: {get_response.get('urls', ['No URL found'])[0]}")
                break

            print("Waiting for Cloud Run service to become ready...")
            time.sleep(5)  # Wait before polling again

    except Exception as e:
        print(f"Error deploying Cloud Run service: {e}")

# Example usage:
project_id = "895271681097"
location = "us-central1"  # e.g., "us-central1"
service_name = "cloudrun-client-test4"
image_uri = "us-docker.pkg.dev/grpc-testing/psm-interop/cpp-client:v1.70.x"
service_account = "xds-k8s-interop-tests@emchandwani-default.iam.gserviceaccount.com"
grpc_target_port = 8079  # Replace with your gRPC server's port
discovery_url = "https://staging-run.sandbox.googleapis.com" # Replace with your discovery url and API key.
mesh="projects/emchandwani-default/locations/global/meshes/grpc-mesh"
server_target="https://emchandwani-psm-server-20250303-0945-6cffe-te45d2q5za-uc.a.run.app"

deploy_cloud_run_from_discovery(
    project_id,
    location,
    service_name,
    server_target,
    mesh,
    image_uri,
    service_account,
    grpc_target_port,
    discovery_url,
)
