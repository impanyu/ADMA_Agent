import requests as refresh_requests
import os

from langchain.tools import BaseTool, StructuredTool, tool
import json
from langchain_community.utilities import Requests
from langchain.pydantic_v1 import BaseModel, Field
import uuid



def refresh_JD_access_token():

    refresh_token = os.getenv("JD_REFRESH_TOKEN")
    client_id = os.getenv("JD_CLIENT_ID")
    
    client_secret = os.getenv("JD_CLIENT_SECRET")
    scope = "org2 files offline_access  ag3  eq2 work2"
    redirect_uri = "https://adma.hopto.org/"



    url = "https://signin.johndeere.com/oauth2/aus78tnlaysMraFhC1t7/v1/token"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "client_id": client_id,
        "client_secret": client_secret
    }
    #refresh_requests = Requests(headers=headers)
    #print(data)

    response = refresh_requests.post(url, headers=headers,data=data)

    return response.json()  # Returns the response in JSON format


@tool
def query_ENREEC() -> str:
    """Get the info of ENREEC. ENREEC is the organization that owns the fields in the JD API."""
    global requests
    response = requests.get("https://sandboxapi.deere.com/platform/organizations/4193081")
    if (not response.status_code == 200): # in case the authorization token is expired, refresh the token and try again
        JD_api_key = refresh_JD_access_token()["access_token"]
        requests = Requests(headers={"Authorization": f"Bearer {JD_api_key}", "User-Agent": "ADMA", "Accept": "application/vnd.deere.axiom.v3+json","Connection": "keep-alive","Accept-Encoding": "gzip, deflate, br"})
        response = requests.get("https://sandboxapi.deere.com/platform/organizations/4193081")
    return json.dumps(response.json())

@tool
def query_ENREEC_fields() -> str:
    """Call this when the user ask for fields in ENREEC. Get the list of all the fields in ENREEC. There are a bunch of fields in ENREEC. When the user ask for any information such as operations, farms, or boundaries of a field, you need first call this function to get the list of all the fields in ENREEC. Then you can use the field_id to get the operations, farms, or boundaries of a field."""
    global requests
    response = requests.get("https://sandboxapi.deere.com/platform/organizations/4193081/fields")
    if (not response.status_code == 200): # in case the authorization token is expired, refresh the token and try again
        JD_api_key = refresh_JD_access_token()["access_token"]
        requests = Requests(headers={"Authorization": f"Bearer {JD_api_key}", "User-Agent": "ADMA", "Accept": "application/vnd.deere.axiom.v3+json","Connection": "keep-alive","Accept-Encoding": "gzip, deflate, br"})
        response = requests.get("https://sandboxapi.deere.com/platform/organizations/4193081/fields")
    return json.dumps(response.json())

def query_ENREEC_fields_file() -> str:
    """Call this when the user ask for fields in ENREEC. Get the list of all the fields in ENREEC. There are a bunch of fields in ENREEC. When the user ask for any information such as operations, farms, or boundaries of a field, you need first call this function to get the list of all the fields in ENREEC. Then you can use the field_id to get the operations, farms, or boundaries of a field."""
    global requests
    response = requests.get("https://sandboxapi.deere.com/platform/organizations/4193081/fields")
    if (not response.status_code == 200): # in case the authorization token is expired, refresh the token and try again
        JD_api_key = refresh_JD_access_token()["access_token"]
        requests = Requests(headers={"Authorization": f"Bearer {JD_api_key}", "User-Agent": "ADMA", "Accept": "application/vnd.deere.axiom.v3+json","Connection": "keep-alive","Accept-Encoding": "gzip, deflate, br"})
        response = requests.get("https://sandboxapi.deere.com/platform/organizations/4193081/fields")
    with open("tmp/JD_fields.json", "w") as f:
        json.dump(response.json(), f)

    return "tmp/JD_fields.json"



class query_ENREEC_farms_in_field_input_schema(BaseModel):
    field_id: str = Field(description="the field_id of the field in ENREEC. The filed_id is a long string such as: 551c3cdd-0000-1000-7fbf-e1e1e12514c8")


@tool("query_ENREEC_farms_in_field", args_schema=query_ENREEC_farms_in_field_input_schema)
def query_ENREEC_farms_in_field(field_id: str) -> str:
    """Only call this when the user ask for farms of a specified field in ENREEC explitly. No need to call this when the user ask for general info of a field. Get the list of all the farms of the specified field in ENREEC. If you do not know field_id, call query_ENREEC_fields() to get the list of all the fields in ENREEC, then you can use the field_id to get the boundary of a field."""
    global requests
    response = requests.get(f"https://sandboxapi.deere.com/platform/organizations/4193081/fields/{field_id}/farms")

    if (not response.status_code == 200):# in case the authorization token is expired, refresh the token and try again
        JD_api_key = refresh_JD_access_token()["access_token"]
        requests = Requests(headers={"Authorization": f"Bearer {JD_api_key}", "User-Agent": "ADMA", "Accept": "application/vnd.deere.axiom.v3+json","Connection": "keep-alive","Accept-Encoding": "gzip, deflate, br"})
        response = requests.get("https://sandboxapi.deere.com/platform/organizations/4193081/fields/{field_id}/farms")
        
    return json.dumps(response.json())

@tool
def query_crop_types() -> str:
    """Call this when the user ask for crop types available in the John Deere system. Get the list of all the crop types available in John Deere."""
    global requests
    response = requests.get(f"https://sandboxapi.deere.com/platform/cropTypes")
    if (not response.status_code == 200):# in case the authorization token is expired, refresh the token and try again
        JD_api_key = refresh_JD_access_token()["access_token"]
        requests = Requests(headers={"Authorization": f"Bearer {JD_api_key}", "User-Agent": "ADMA", "Accept": "application/vnd.deere.axiom.v3+json","Connection": "keep-alive","Accept-Encoding": "gzip, deflate, br"})
        response = requests.get(f"https://sandboxapi.deere.com/platform/cropTypes")
    return json.dumps(response.json())


class query_ENREEC_operation_in_field_input_schema(BaseModel):
    field_id: str = Field(description="the field_id within ENREEC. The filed_id is a long string such as: 551c3cdd-0000-1000-7fbf-e1e1e12514c8")

@tool("query_ENREEC_operation_in_field", args_schema=query_ENREEC_operation_in_field_input_schema)
def query_ENREEC_operation_in_field(field_id: str) -> str:
    """Call this when the user ask for the info of a field operation in a specified field in ENREEC. Get the info of the field operation in ENREEC. If you do not know field_id, call query_ENREEC_fields() to get the list of all the fields in ENREEC, then you can use the field_id to get the boundary of a field."""
    global requests
    response = requests.get(f"https://sandboxapi.deere.com/platform/organizations/4193081/fields/{field_id}/fieldOperations")
    if (not response.status_code == 200):# in case the authorization token is expired, refresh the token and try again
        JD_api_key = refresh_JD_access_token()["access_token"]
        requests = Requests(headers={"Authorization": f"Bearer {JD_api_key}", "User-Agent": "ADMA", "Accept": "application/vnd.deere.axiom.v3+json","Connection": "keep-alive","Accept-Encoding": "gzip, deflate, br"})
        response = requests.get(f"https://sandboxapi.deere.com/platform/organizations/4193081/fields/{field_id}/fieldOperations")
    return json.dumps(response.json())


class query_ENREEC_boundary_in_field_input_schema(BaseModel):
    field_id: str = Field(description="the field_id within ENREEC. The field_id is a long string such as: 551c3cdd-0000-1000-7fbf-e1e1e12514c8.")

@tool("query_ENREEC_boundary_in_field", args_schema=query_ENREEC_boundary_in_field_input_schema)
def query_ENREEC_boundary_in_field(field_id: str) -> str:
    """Do not be lazy, make sure to call this function each time the user ask for the boundary or map of a specified field in ENREEC. Somethimes you only know field name, which is a short string less than 6 letters, in this case, call query_ENREEC_fields() to get the list of all the fields in ENREEC, then you can know field_id"""
    global requests
    response = requests.get(f"https://sandboxapi.deere.com/platform/organizations/4193081/fields/{field_id}/boundaries")
    if (not response.status_code == 200):# in case the authorization token is expired, refresh the token and try again
        JD_api_key = refresh_JD_access_token()["access_token"]
        requests = Requests(headers={"Authorization": f"Bearer {JD_api_key}", "User-Agent": "ADMA", "Accept": "application/vnd.deere.axiom.v3+json","Connection": "keep-alive","Accept-Encoding": "gzip, deflate, br"})
        response = requests.get(f"https://sandboxapi.deere.com/platform/organizations/4193081/fields/{field_id}/boundaries")
    rd = uuid.uuid4()
    with open(f"tmp/boundary_{rd}.json", "w") as f:
        json.dump(response.json(),f)
    result = {"type": "boundary", "path": f"tmp/boundary_{rd}.json"}
    return json.dumps(result)
    #json.dumps(response.json()["values"][0]["multipolygons"][0]["rings"])


class file_existence_check_input_schema(BaseModel):
    path: str = Field(description="the path of the file to check if it exists or not")

@tool("file_existence_check", args_schema=file_existence_check_input_schema)
def file_existence_check(path: str) -> str:
    """Always call this function each time if there's a local file path in the messages of ai and user. Check if the file exists or not."""
    if os.path.exists(path):
        return True
    else:
        return False

def field_id_from_name(field_name: str) -> str:
    if not os.path.exists("tmp/JD_fields.json"):
        query_ENREEC_fields_file()
    with open("tmp/JD_fields.json", "r") as f:
        fields = json.load(f)
    for field in fields["values"]:
        print(field["name"])
        if field["name"] == field_name:
            return field["id"]
    return ""




#print(refresh_JD_access_token())
JD_api_key = refresh_JD_access_token()["access_token"]
requests = Requests(headers={"Authorization": f"Bearer {JD_api_key}", "User-Agent": "ADMA", "Accept": "application/vnd.deere.axiom.v3+json","Connection": "keep-alive","Accept-Encoding": "gzip, deflate, br"})
print(f"JD_api_key={JD_api_key}")

