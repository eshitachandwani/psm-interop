import grpc
from envoy.service.status.v3 import csds_pb2_grpc
from envoy.service.status.v3.csds_pb2 import ClientStatusRequest
from envoy.service.status.v3.csds_pb2 import ClientStatusResponse
from typing import cast

channel = grpc.secure_channel(
    "emchandwani-psm-client-20250325-1141-zfwjm-921384807982.us-east7.run.app:443",
    grpc.ssl_channel_credentials(),
)


stub = csds_pb2_grpc.ClientStatusDiscoveryServiceStub(channel)
request = ClientStatusRequest()  # Ensure this is empty
response = stub.FetchClientStatus(request)
response = cast(ClientStatusResponse, response)
if len(response.config) != 1:
    print("eshita Unexpected number of client configs: %s", len(response.config))
print("eshita response corrcet",response.config[0])
# print(response)
