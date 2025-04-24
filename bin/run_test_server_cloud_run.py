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
Run test xds server.

Typical usage examples:

    # Help.
    ./run.sh ./bin/run_test_server_cloud_run.py --help

"""
import logging

from absl import app
from absl import flags

from bin.lib import common
from framework import xds_flags
from framework import xds_k8s_flags

logger = logging.getLogger(__name__)

flags.adopt_module_key_flags(xds_flags)
flags.adopt_module_key_flags(xds_k8s_flags)
flags.adopt_module_key_flags(common)


def main(argv):
    if len(argv) > 1:
        raise app.UsageError("Too many command-line arguments.")

    xds_flags.set_socket_default_timeout_from_flag()

    server_runner = common.make_cloud_run_server_runner()
    server_runner.run()


if __name__ == "__main__":
    app.run(main)
