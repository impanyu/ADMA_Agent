import requests as refresh_requests
import os

from langchain.tools import BaseTool, StructuredTool, tool
import json
from langchain_community.utilities import Requests
from langchain.pydantic_v1 import BaseModel, Field
import uuid


token = '7353d23703a37d3a5554e63aa448bbc509b0cec0'
# Headers including the Authorization token (if needed)
headers = {'Authorization': f'Token {token}'}

requests = Requests(headers=headers)
root_url = 'https://adma.hopto.org'

class ADMA_get_meta_data_input_schema(BaseModel):
    path: str = Field(description="The path or name of the file in the ADMA system. The full path is like /username/ag_data/.../file_name, but here the file_path is the relative path after the ag_data directory.")

@tool("ADMA_get_meta_data", args_schema=ADMA_get_meta_data_input_schema)
def ADMA_get_meta_data(path):
  """ Always call this tool when the user want to get the meta data of a file or directory on the ADMA server."""
  api_url = f'{root_url}/api/meta_data/?target_path={path}'

  # Sending the GET request to the meta data of the file
  response = requests.get(api_url)

  # Checking the response from the server
  if response.status_code == 200:
      #print(response.json())
      return response.json()

  else:
      return {}
      #print("Failed to download the meta data:", response.text)


class ADMA_list_directory_contents_input_schema(BaseModel):
    dir_path: str = Field(description="The path or name of the directory in the ADMA system. The full path is like /username/ag_data/.../file_name, but here the dir_path is the relative path after the ag_data directory.")

@tool("ADMA_list_directory_contents", args_schema=ADMA_list_directory_contents_input_schema)
def ADMA_list_directory_contents(dir_path):
    """Always call this tool when the user want to list a directory on the ADMA server."""
    list_url = f"{root_url}/api/list/?target_path={dir_path}"
    response = requests.get(list_url)
    if response.status_code == 200:
        return response.json()  # Assuming the API returns a JSON list of paths
    else:
        return f"Failed to list directory: {dir_path}, Status code: {response.status_code}, {response.text}"
    
def ADMA_list_dir(dir_path):
    """Return the list of paths under the directory dir_path on the ADMA server, the return path is in ADMA API file path format"""
    list_url = f"{root_url}/api/list/?target_path={dir_path}"
    response = requests.get(list_url)
    if response.status_code == 200:
        list_of_paths = response.json()
        result = ["/".join(path.split("/")[3:]) for path in list_of_paths]
        return result
    else:
        return []
       
    

class ADMA_get_running_instance_input_schema(BaseModel):
    dir_path: str = Field(description="The path or name of the directory in the ADMA system. The full path is like /username/ag_data/.../file_name, but here the dir_path is the relative path after the ag_data directory.")

@tool("ADMA_get_running_instance", args_schema=ADMA_get_running_instance_input_schema)
def ADMA_get_running_instance(dir_path):
    """Always call this tool when the user want to check if there is any running instance for dir_path on the ADMA server."""
    instance_url = f"{root_url}/api/get_running_instance/?target_path=ypan12/ag_data/{dir_path}"
    response = requests.get(instance_url)
    print(response.json())
    if response.status_code == 200:
        return response.json()  # Assuming the API returns a JSON list of paths
    else:
        return f"Failed to get running instance: {dir_path}, Status code: {response.status_code}, {response.text}"
        
    

class ADMA_check_file_input_schema(BaseModel):
    dir_path: str = Field(description="The path or name of the directory in the ADMA system. The full path is like /username/ag_data/.../file_name, but here the dir_path is the relative path after the ag_data directory.")

@tool("ADMA_check_file", args_schema=ADMA_check_file_input_schema)
def ADMA_check_file(dir_path):
    """Always call this tool when the user want to check or display the content of dir_path on the ADMA server."""
    download_url = f"{root_url}/api/download/?target_path={dir_path}"
    response = requests.get(download_url)

    if response.status_code == 200:
        rd = uuid.uuid4()
        with open(f"tmp/{rd}_{os.path.basename(dir_path)}", "wb") as f:
            f.write(response.content)
        result = {"type": "file", "path": f"tmp/{rd}_{os.path.basename(dir_path)}"}
        return json.dumps(result)
        #return response.text
    else:
        return f"Failed to download file: {dir_path}, Status code: {response.status_code}, {response.text}"

def ADMA_download_file(dir_path):
   
    download_url = f"{root_url}/api/download/?target_path={dir_path}"
    response = requests.get(download_url)

    if response.status_code == 200:
        rd = uuid.uuid4()
        with open(f"tmp/{rd}_{os.path.basename(dir_path)}", "wb") as f:
            f.write(response.content)
        result =  f"tmp/{rd}_{os.path.basename(dir_path)}"
        return result
        #return response.text
    else:
        return ""



class ADMA_plot_option_input_schema(BaseModel):
    dir_path: str = Field(description="The path or name of the realm5 data file in the ADMA system. The full path is like /username/ag_data/.../file_name, but here the dir_path is the relative path after the ag_data directory.")   
    value_name: str = Field(description="the name of the value to be plotted") 
   
@tool("ADMA_plot_option", args_schema=ADMA_plot_option_input_schema)
def ADMA_plot_option(dir_path, value_name="temperature"):
    """Always call this tool when the user want to plot realm5 weather data by specifying the value name and the realm5 data path.  If the user ask to plot the temperature, the value_name should be 'temperature'."""
    download_url = f"{root_url}/api/download/?target_path={dir_path}"
    response = requests.get(download_url)

    if response.status_code == 200:
        data = json.loads(response.content)
    else:
        return f"Failed to download file: {dir_path}, Status code: {response.status_code}, {response.text}"
    x_values = [] 
    y_values = []
    i = 0
    for x in data:
        if not i % 5 == 0:
            i += 1
            continue
        x_values.append(x)
        y_values.append(data[x][value_name])
        i += 1

    options = {
        "tooltip": {
            "trigger": 'axis',  # Can be 'item' for single data points or 'axis' for all items in the category
            "axisPointer": {  # Used in axis trigger to indicate the axis
                "type": 'shadow'  # Options are 'line' or 'shadow'
            }
        },
        "xAxis": {
            "type": "category",
            "data": x_values,
            "rotate": 45,  # Rotate labels by 45 degrees
        },
        "yAxis": {"type": "value"},
        "series": [
            {"data": y_values, "type": "line"}
        ],
    }
    return options

def ADMA_menu_option(menu_name,path=""):
    root_url = "https://adma.hopto.org"
    menu_paths = {
        "search": "/search.html?current_path=ypan12",
        "share_with_me": "/files.html?current_path=public",
        "files": "/files.html?current_path=ypan12/ag_data",
        "data": "/data.html?current_path=ypan12",
        "models": "/models.html?current_path=ypan12",
        "tools": "/tools.html?current_path=ypan12",
        "collections": "/collections.html?current_path=ypan12/collections",
        "documentation": "/documentation.html",
        "api": "/api.html"
    }
    if menu_name not in menu_paths:
        menu_name = "files"
    result = f"{root_url}{menu_paths[menu_name]}"
    if path != "": 
        if menu_name == "files":
            result += f"/{path}"
    return result



# URL of the API endpoiont for listing dir structure
from urllib.parse import urlencode
def ADMA_search(root_dir, search_box, category=["All"], mode=["All"], format=["All"], label=["All"], realtime=["All"], time_range=["start","end"], spatial_range=["southwest","northeast"]):
    """Search the files or folders under root_dir """
    params = {
        'root_dir': root_dir,
        'search_box': search_box,
        'category': category,
        'mode': mode,
        'form': format,
        'label': label,
        'realtime': realtime,
        'time_range': time_range,
        'spatial_range': spatial_range,

    }

    # Remove empty lists to avoid sending empty parameters
    params = {k: v for k, v in params.items() if v}

    # Construct the URL with properly encoded parameters
    list_url = f"{root_url}/api/search/?{urlencode(params, doseq=True)}"
    print(list_url)


    response = requests.get(list_url)
    if response.status_code == 200:
        return response.json()[:5]  # Assuming the API returns a JSON list of meta data, only return 5 results
    else:
        print(f"Failed to search directory: {root_dir}, Status code: {response.status_code}, {response.text}")
        return []


def ADMA_url_extractor(meta_data):
    """Extract the ADMA url from the ADMA meta data"""
    # the abs_path is in the absolute path format of /data/username/ag_data/.../file_name, extract the path starting from the username directory
    # return the url for the path on adma
    abs_path = meta_data["abs_path"]
    root_dir = "https://adma.hopto.org/files.html?current_path="
    adma_web_path = "/".join(abs_path.split("/")[2:])
    return f"{root_dir}{adma_web_path}"