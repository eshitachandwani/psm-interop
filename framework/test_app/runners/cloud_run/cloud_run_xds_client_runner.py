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

from framework.test_app.runners.cloud_run import cloud_run_base_runner
from framework.test_app.client_app import XdsTestClient

logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class CloudRunClientDeploymentArgs:
    """Arguments for deploying a client to Cloud Run."""

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
        *,
        mesh_name: str,
        server_target: str
    ):
        super().__init__(
            project,
            service_name,
            image_name,
            network=network,
            region=region,
            is_client=True,
            mesh_name=mesh_name,
            server_target=server_target
        )
        # Mutable state associated with each run.
        self._reset_state()

    @override
    def _reset_state(self):
        super()._reset_state()
        self.service = None
        self.pods_to_clients = {}
        self.replica_count = 0

    @override
    def run(self, **kwargs) -> XdsTestClient:
        """Deploys and manages the xDS Test Client on Cloud Run."""
        logger.info(
            "Starting cloud run client with service %s and image %s",
            self.service_name,
            self.image_name,
        )
        if not self.mesh_name or not self.server_target:
            raise ValueError("mesh_name and server_target must be provided for client deployment.")

        super().run(**kwargs)
        clients = [
            XdsTestClient(
                ip="0.0.0.0", rpc_port=0, hostname=self.current_revision,server_target=self.server_target
            )
        ]
        self.clients = clients  # Add clients to the list
        self._start_completed()
        return clients[0]

    def get_service_url(self):
        return self.cloudrun_api_manager.get_service_url()

    @override
    def cleanup(self, *, force=False):
        try:
            if self.service:
                self.stop()
                self.service_name = None
                self.service = None
        finally:
            self._stop()
