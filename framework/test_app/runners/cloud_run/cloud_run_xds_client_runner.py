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
"""
Run xDS Test Client on Cloud Run.
"""
import dataclasses
import logging
from typing import List, Optional
from typing_extensions import override
from framework.infrastructure import gcp
from framework.test_app.runners.cloud_run import cloud_run_base_runner
from framework.test_app.client_app import XdsTestClient

logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class CloudRunDeploymentArgs:
    """Arguments for deploying a server to Cloud Run."""

    env_vars: dict = dataclasses.field(default_factory=dict)
    max_instances: int = 10  # Example: Maximum number of instances
    min_instances: int = 0  # Example: Minimum number of instances
    service_account_email: str = ""  # Email address of the service account
    timeout_seconds: int = 300  # Timeout for requests
    revision_suffix: Optional[str] = None
    mesh_name: Optional[str] = None
    server_target: Optional[str] = None

    def as_dict(self):
        return {
            "env_vars": self.env_vars,
            "max_instances": self.max_instances,
            "min_instances": self.min_instances,
            "service_account_email": self.service_account_email,
            "timeout_seconds": self.timeout_seconds,
            "mesh_name": self.mesh_name,
            "server_target": self.server_target
        }


class CloudRunClientRunner(cloud_run_base_runner.CloudRunBaseRunner):
    """Manages xDS Test Clients running on Cloud Run."""

    def __init__(
        self,
        project: str,
        service_name: str,
        image_name: str,
        network: str,
        region: str,
        debug_use_port_forwarding: bool,
        gcp_api_manager:gcp.api.GcpApiManager,
        *,
        mesh:str,
        server_target:str,
        is_client:bool=True,
    ):
        super().__init__(
            project,
            service_name,
            image_name,
            network=network,
            region=region,
            gcp_ui_url=gcp_api_manager.gcp_ui_url,
            mesh=mesh,
            server_target=server_target,
            is_client=is_client,
        )
        # Mutable state associated with each run.
        self._reset_state()
        self.debug_use_port_forwarding = debug_use_port_forwarding


    @override
    def _reset_state(self):
        super()._reset_state()
        self.service = None
        self.pods_to_servers = {}
        self.replica_count = 0

    @override
    def run(self, **kwargs) -> XdsTestClient:
        """Deploys and manages the xDS Test Client on Cloud Run."""
        logger.info(
            "Starting cloud run Client with service %s and image %s",
            self.service_name,
            self.image_name,
        )

        super().run(**kwargs)
        logger.info("eshita %s",self.current_revision)

        # return client_app.XdsTestClient(
        #     ip=pod.status.pod_ip,
        #     rpc_port=rpc_port,
        #     server_target=server_target,
        #     hostname=pod.metadata.name,
        #     rpc_host=rpc_host,
        #     monitoring_port=monitoring_port,
        # )
        client = XdsTestClient(
                ip=self.current_revision[8:], rpc_port=443,rpc_host=self.current_revision[8:], server_target=self.server_target,hostname=self.current_revision[8:],maintenance_port=443
            )
        self._start_completed()
        return client

    def get_service_url(self):
        return self.cloud_run_api_manager.get_service_uri(self.service_name)

    @override
    def cleanup(self, *, force=False):
        try:
            if self.service:
                self.stop()
        finally:
            self._stop()
