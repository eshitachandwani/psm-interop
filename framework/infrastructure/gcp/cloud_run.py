# Copyright 2025 gRPC authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import abc
import logging

from googleapiclient import discovery

from framework.infrastructure import gcp

logger = logging.getLogger(__name__)

DEFAULT_TEST_PORT = 8080
DEFAULT_TIMEOUT = 600


class CloudRunApiManager(
    gcp.api.GcpStandardCloudApiResource, metaclass=abc.ABCMeta
):
    project: str
    region: str
    _parent: str
    service: discovery.Resource
    api_manager: gcp.api.GcpApiManager

    def __init__(self, project: str, region: str):
        if not project:
            raise ValueError("Project ID cannot be empty or None.")
        if not region:
            raise ValueError("Region cannot be empty or None.")
        self.api_manager = gcp.api.GcpApiManager(
            v2_discovery_uri="https://run.googleapis.com/$discovery/rest?"
        )
        self.project = project
        self.region = region
        service: discovery.Resource = self.api_manager.cloudrun("v2")
        self.service = service
        self._parent = f"projects/{self.project}/locations/{self.region}"
        super().__init__(self.service, project)

    @property
    def api_name(self) -> str:
        """Returns the API name for Cloud Run."""
        return "run"

    @property
    def api_version(self) -> str:
        """Returns the API version for Cloud Run."""
        return "v2"

    def create_cloud_run_resource(
        self, service: discovery.Resource, service_name: str, body: dict
    ):
        service.projects().locations().services().create(
            parent=self._parent, serviceId=service_name, body=body
        ).execute()

    def get_cloud_run_resource(
        self, service: discovery.Resource, service_name: str
    ):
        return self._get_resource(
            collection=service.projects().locations().services(),
            full_name=self.resource_full_name(
                service_name, "services", self.region
            ),
        )

    def get_service_uri(self, service_name: str) -> str:
        response = self.get_cloud_run_resource(self.service, service_name)
        return response.get("urls")[0]

    def delete_cloud_run_resource(
        self, service: discovery.Resource, service_name: str
    ):
        service.projects().locations().services().delete(
            name=self.resource_full_name(service_name, "services", self.region)
        ).execute()

    def deploy_service(
        self,
        service_name: str,
        image_name: str,
        *,
        test_port: int = DEFAULT_TEST_PORT,
        is_client: bool = False,
        test_port_client: int = 8079,
        server_target: str = "",
        mesh: str = ""
    ):
        if not service_name:
            raise ValueError("service_name cannot be empty or None")
        if not image_name:
            raise ValueError("image_name cannot be empty or None")
        
        try:
            service_body = {}
            service_body={
              "launch_stage":"alpha",
             "template":
                       {
                            "containers": [
                               {
                                  "image": image_name,
                                    "ports": [{"containerPort": test_port, "name": "h2c"}],            
                                }
                             ],
                        },
                    }
            
            if is_client:
                service_body={
                    "launch_stage":"alpha",
                    "template":
                        {
                            "containers": [
                               {
                                  "image": image_name,
                                  "ports": [{"containerPort": 50052, "name": "h2c"}],  
                                  "args": [f"--server={server_target}", "--secure_mode=true",],
                                  "env":[
                                    {
                                        "name":"GRPC_EXPERIMENTAL_XDS_AUTHORITY_REWRITE",
                                        "value":"true"
                                    },
                                    # {
                                    #     "name":"GRPC_TRACE",
                                    #     "value":"all,-timer,-timer_check"
                                    # },
                                    # {
                                    #     "name":"GRPC_VERBOSITY",
                                    #     "value":"DEBUG"
                                    # },
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
                            "service_mesh":{
                                "mesh":mesh,
                                "dataplaneMode":"PROXYLESS_GRPC"
                                }
                        },
                        "ingress": "INGRESS_TRAFFIC_ALL",
                        "traffic": [{"type": "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST", "percent": 100}],
                    }


            self.create_cloud_run_resource(self.service,service_name,service_body)
            if is_client:
                policy_body={}
                policy_body={
                    "policy": {
                        "bindings": [
                            {
                                "role": "roles/run.invoker",
                                "members": ["allUsers"]
                            }
                        ],
                    },
                }
                self.service.projects().locations().services().setIamPolicy(resource=self.resource_full_name(service_name, "services", self.region), body=policy_body).execute() # pylint: disable=no-member
            logger.info("Deploying Cloud Run service '%s'", service_name)
            return self.get_service_uri(service_name)

        except Exception as e:  # noqa pylint: disable=broad-except
            logger.exception("Error deploying Cloud Run service: %s", e)
            raise

    def delete_service(self, service_name: str):
        try:
            self.delete_cloud_run_resource(self.service, service_name)
        except Exception as e:
            logger.exception("Error deleting service: %s", e)
            raise