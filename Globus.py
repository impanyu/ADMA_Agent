import requests as refresh_requests
import os
import json
import uuid
import globus_sdk
from globus_sdk.scopes import TransferScopes
from globus_sdk import (
    AuthClient,
    TransferClient,
    ConfidentialAppAuthClient,
    RefreshTokenAuthorizer,
    NativeAppAuthClient
)

# Define the source and destination endpoints
endpoints_ids = {"unl_onedrive":"c10b0a87-02e6-4d3a-bda4-6d10f12820c1", "hcc_swan":"bf57b3a0-ba0f-11ec-ad98-5ddcb36bd5b8"}


# Define your client credentials
CLIENT_ID = "7afd2a98-df9b-4ede-83b9-b8dbd6009be9"
CLIENT_SECRET = "9ade63b2-6cf0-4a06-b4ee-922f3a31ccaa"
TOKEN = "your-access-token"  # Replace with your actual access token if available
auth_client = NativeAppAuthClient(CLIENT_ID)
#auth_client = globus_sdk.ConfidentialAppAuthClient(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)

# we default to using the Transfer "all" scope, but it is settable here
# look at the ConsentRequired handler below for how this is used
def get_authorize_url(*, scopes=TransferScopes.all):  
    additional_scopes = ""
    
    for endpoint in endpoints_ids:
        COLLECTION_UUID = endpoints_ids[endpoint]
        additional_scope = f" *https://auth.globus.org/scopes/{COLLECTION_UUID}/data_access"
        additional_scopes += additional_scope
    additional_scopes = additional_scopes.strip()

    # Define the specific scope including data_access for the collection
    custom_scopes = f"urn:globus:auth:scope:transfer.api.globus.org:all[{additional_scopes}]"
    
    auth_client.oauth2_start_flow(requested_scopes=scopes,redirect_uri="https://adma.hopto.org/")
    authorize_url = auth_client.oauth2_get_authorize_url()
    return authorize_url


def check_for_consent_required(transfer_client):
    consent_required_scopes = []
    for endpoint in endpoints_ids:
        target = endpoints_ids[endpoint]
        try:
            transfer_client.operation_ls(target, path="/")
        # catch all errors and discard those other than ConsentRequired
        # e.g. ignore PermissionDenied errors as not relevant
        except globus_sdk.TransferAPIError as err:
            if err.info.consent_required:
                consent_required_scopes.extend(err.info.consent_required.required_scopes)
    # the block above may or may not populate this list
    # but if it does, handle ConsentRequired with a new login
    if consent_required_scopes:
        print(
            "One of your endpoints requires consent in order to be used.\n"
            "You must login a second time to grant consents.\n\n"
        )


def get_transfer_token(auth_code):
    print(f"auth_code: {auth_code}")
    additional_scopes = ""
    #auth_client = NativeAppAuthClient(CLIENT_ID)
    #auth_client = globus_sdk.ConfidentialAppAuthClient(client_id="your-client-id", client_secret="your-client-secret")

    
    for endpoint in endpoints_ids:
        COLLECTION_UUID = endpoints_ids[endpoint]
        additional_scope = f" *https://auth.globus.org/scopes/{COLLECTION_UUID}/data_access"
        additional_scopes += additional_scope
    additional_scopes = additional_scopes.strip()

    # Define the specific scope including data_access for the collection
    custom_scopes = f"urn:globus:auth:scope:transfer.api.globus.org:all[{additional_scopes}]"
    try:
        #auth_client.oauth2_start_flow(requested_scopes=custom_scopes,redirect_uri="https://adma.hopto.org/")
        tokens = auth_client.oauth2_exchange_code_for_tokens()
        transfer_tokens = tokens.by_resource_server["transfer.api.globus.org"]
    except globus_sdk.AuthAPIError as e:
        print(f"Error: {e.code} - {e.message}")
        print(f"Raw Response: {e.raw_json}")
    return transfer_tokens["access_token"]
    

    # return the TransferClient object, as the result of doing a login
    return transfer_client


# Perform the file transfer
def transfer_file(transfer_token, source_endpoint, target_endpoint, source_path, target_path):
    transfer_client = globus_sdk.TransferClient(
        authorizer=globus_sdk.AccessTokenAuthorizer(transfer_token)
    )
    task_data = globus_sdk.TransferData(source_endpoint=endpoints_ids[source_endpoint], destination_endpoint= endpoints_ids[target_endpoint])
    task_data.add_item(
        source_path,
        target_path,
        recursive=True  # Enable recursive transfer for folders
    )

    task_doc = transfer_client.submit_transfer(task_data)
    task_id = task_doc["task_id"]
    print(f"submitted transfer, task_id={task_id}")


    return task_id

# Check the status of the transfer task
def check_task_status(access_token, task_id):
    tc = globus_sdk.TransferClient(authorizer=globus_sdk.AccessTokenAuthorizer(access_token))
    task = tc.get_task(task_id)
    print(f"Task {task_id} Status: {task['status']}")


# List the folder structure of a collection
def list_folder(access_token, endpoint, path):
    endpoint_id = endpoints_ids[endpoint]
    print(f"Access Token: {access_token}")

    tc = globus_sdk.TransferClient(authorizer=globus_sdk.AccessTokenAuthorizer(access_token))
    results = []
    try:
        # Perform a directory listing on the given endpoint and path
        response = tc.operation_ls(endpoint_id=endpoint_id, path=path)
        #print(f"Contents of {path} on endpoint {endpoint_id}:\n")
        for item in response["DATA"]:
            item_type = "Folder" if item["type"] == "dir" else "File"
            results.append({item_type: item['name']})
    except globus_sdk.TransferAPIError as e:
        print(f"Error listing folder: {e.code} - {e.message}")
