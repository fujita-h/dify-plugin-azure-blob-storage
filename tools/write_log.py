import uuid
from collections.abc import Generator
from datetime import UTC, datetime
from typing import Any

from azure.core.exceptions import ResourceExistsError
from azure.storage.blob import BlobServiceClient, ContentSettings
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage


class WriteLogTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        # Ensure runtime and credentials
        if not self.runtime or not self.runtime.credentials:
            raise Exception("Tool runtime or credentials are missing")

        # Get account name
        account_name = self.runtime.credentials.get("azure_blob_storage_account_name")
        if not account_name:
            raise ValueError("Azure Blob Storage connection string is required")

        # Get API key
        api_key = self.runtime.credentials.get("azure_blob_storage_api_key")
        if not api_key:
            raise ValueError("Azure Blob Storage API Key is required")

        # get container name
        container_name = tool_parameters.get("container_name")
        if not container_name:
            raise ValueError("Container name is required")

        # get log string
        log_string = tool_parameters.get("log_string")
        if not log_string:
            raise ValueError("Log file is required")

        # get resouce name
        resource_name = tool_parameters.get("resource_name", "default")

        # get file suffix
        file_suffix = tool_parameters.get("file_suffix")
        file_suffix_str = f"-{file_suffix}" if file_suffix else ""

        # get current time
        current_time = datetime.now(UTC)
        blob = (
            f"{resource_name}/"
            f"{current_time.strftime('%Y/%m/%d/%H-%M-%S.%f')}-{uuid.uuid4().hex}"
            f"{file_suffix_str}.log"
        )

        # create a blob client using the connection string
        blob_service_client = BlobServiceClient(
            account_url=f"https://{account_name}.blob.core.windows.net", credential=api_key
        )

        # create container
        try:
            blob_service_client.create_container(name=container_name)
        except ResourceExistsError:
            pass
        except Exception as e:
            raise Exception("Failed to create container") from e

        # content setting
        content_settings = ContentSettings(content_type="text/plain")

        # upload file to blob storage
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob)
        try:
            blob_client.upload_blob(log_string, content_settings=content_settings)
        except Exception as e:
            raise Exception("Failed to write log") from e

        # return blob and container name
        yield self.create_text_message(f'Log file "{blob}" has been written to container "{container_name}"')
        yield self.create_json_message({"blob": blob, "container": container_name})
