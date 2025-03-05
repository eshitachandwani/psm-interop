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
import subprocess
import os

from google.cloud import run_v2
from google.api import launch_stage_pb2

from typing import Optional
from framework.infrastructure.gcp.api import GcpProjectApiResource

logger = logging.getLogger(__name__)

DEFAULT_TEST_PORT = 8080
DEFAULT_TIMEOUT = 600


class CloudRunApiManager(GcpProjectApiResource, metaclass=abc.ABCMeta):
    project: str
    region: str
    _connector: str
    _connector_name: str
    _parent: str
    _client: run_v2.ServicesClient
    _service: run_v2.Service

    def __init__(self, project: str, region: str):
        if not project:
            raise ValueError("Project ID cannot be empty or None.")
        if not region:
            raise ValueError("Region cannot be empty or None.")

        self.project = project
        self.region = region
        client_options = {"api_endpoint": f"{self.region}-staging-run.sandbox.googleapis.com"}
        self._client = run_v2.ServicesClient(client_options=client_options)
        self._parent = f"projects/{self.project}/locations/{self.region}"
        self._service = None

    def deploy_service(
        self,
        service_name: str,
        image_name: str,
        *,
        test_port: int = DEFAULT_TEST_PORT,
        mesh_name: Optional[str] = None,
        server_target: Optional[str] = None,
        is_client: bool = False
    ):
        if not service_name:
            raise ValueError("service_name cannot be empty or None")
        if not image_name:
            raise ValueError("image_name cannot be empty or None")
        service_name = service_name[:49]

        containers = [
            run_v2.Container(
                image=image_name,
                ports=[
                    run_v2.ContainerPort(
                        name="h2c",
                        container_port=test_port , # conditional port setting
                    ),
                ],
            )
        ]

        revision_template_args = {}
        if is_client:
            containers = [
            run_v2.Container(
                image=image_name,
                ports=[
                    run_v2.ContainerPort(
                        name="h2c",
                        container_port=8079 , # conditional port setting
                    ),
                ],
            )
        ]
            if not mesh_name or not server_target:
                raise ValueError("mesh_name and server_target are required for client deployment.")

            revision_template_args["vpc_access"] = run_v2.VpcAccess(
                network_interfaces=[run_v2.VpcAccess.NetworkInterface(
                    network="default",
                    subnetwork="default",
                )]
            )
            revision_template_args["service_mesh"] = run_v2.ServiceMesh(
                    mesh=mesh_name,
                )
            containers[0].args = [f"--server={server_target}", "--secure_mode=false"]
            containers[0].env = [run_v2.EnvVar(name="GRPC_EXPERIMENTAL_XDS_AUTHORITY_REWRITE",value="true"),run_v2.EnvVar(name="GRPC_EXPERIMENTAL_XDS_SYSTEM_ROOT_CERTS",value="true"),run_v2.EnvVar(name="GRPC_EXPERIMENTAL_XDS_GCP_AUTHENTICATION_FILTER",value="true"),run_v2.EnvVar(name="is-trusted-xds-server-experimental",value="true")]
            
        revision_template = run_v2.RevisionTemplate(
            containers=containers, **revision_template_args
        )

        service = run_v2.Service(launch_stage=launch_stage_pb2.ALPHA,template=revision_template)

        request = run_v2.CreateServiceRequest(
            parent=self._parent, service=service, service_id=service_name
        )

        try:
            operation = self._client.create_service(request=request)
            self._service = operation.result(timeout=DEFAULT_TIMEOUT)
            logger.info("Deployed service: %s", self._service.uri)
            return self._service.uri
        except Exception as e:
            logger.exception("Error deploying service: %s", e)
            raise

    def get_service_url(self):
        if self._service is None:
            raise RuntimeError("Cloud Run service not deployed yet.")
        return self._service.uri

    def delete_service(self, service_name: str):
        try:
            request = run_v2.DeleteServiceRequest(
                name=f"{self._parent}/services/{service_name}"
            )
            operation = self._client.delete_service(request=request)
            operation.result(timeout=DEFAULT_TIMEOUT)
            logger.info("Deleted service: %s", service_name)
        except Exception as e:
            logger.exception("Error deleting service: %s", e)
            raise
