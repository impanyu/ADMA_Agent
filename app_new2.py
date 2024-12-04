from dotenv import load_dotenv
import streamlit as st
from PyPDF2 import PdfReader

import time
import faiss

load_dotenv(".venv")
from JD_Tools import *
from utils import *
import folium
from streamlit_folium import st_folium, folium_static

from ADMA_Tools import *

from streamlit_echarts import st_echarts
import uuid
from openai import OpenAI
import json
from pydantic import BaseModel, Field
import copy
import os
from Realm5_Tools import *
import pandas as pd
from Soil import *
from Google_Tools import *
import datetime
from Globus import *

temperature = 0.2

controller_output = {
                "type": "json_schema",
                "json_schema": {
                    "name": "controller_output",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "method": {
                                "type": "string",
                                "description": "The name of the method to call."
                            }
                        },
                        "required": ["method"],
                        "additionalProperties": False
                    }
                }
}
            

list_string_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "list_string_format",
                        "strict": True,
                        "schema": {
                            "type": "object",
                            "properties": {
                                "items": {
                                    "type": "array",
                                    "items": {
                                        "type": "string"
                                    },
                                    "description": "A list of string outputs."
                                }
                            },
                            "required": ["items"],
                            "additionalProperties": False
                    }
    }
}

initializer_output = {
    "type": "json_schema",
    "json_schema": {
        "name": "initializer_output",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "ADMA_search_string": {
                    "type": "string",
                    "description": "ADMA_search_string."
                },
                "ADMA_menu_name": {
                    "type": "string",
                    "description": "ADMA_menu_name.",
                    "enum": ["search", "shared_with_me", "files", "data", "models", "tools", "collections", "documentation", "api"]
                },
                "ADMA_API_file_path": {
                    "type": "string",
                    "description": "ADMA_API_file_path."
                },
                "Realm5_date_str": {
                    "type": "string",
                    "description": "Realm5_date_str."
                },
                "JD_ENREEC_field_id": {
                    "type": "string",
                    "description": "Field_ID."
                },
                "JD_ENREEC_field_name": {
                    "type": "string",
                    "description": "Field_name."
                },
                "Realm5_variable_name_list": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "Google_drive_file_path": {
                    "type": "string",
                    "description": "Google_drive_file_path."
                },
                "ADMA_API_token": {
                    "type": "string",
                    "description": "ADMA_API_token."
                },
                "Google_username": {
                    "type": "string",
                    "description": "Google username of the user."
                },

                "Globus_collection": {
                    "type": "string",
                    "description": "Globus_collection."
                },
                "Globus_path": {
                    "type": "string",
                    "description": "Globus_path."
                },
                "Globus_source_collection": {
                    "type": "string",
                    "description": "Globus_source_collection."
                },
                "Globus_target_collection": {
                    "type": "string",
                    "description": "Globus_target_collection."
                },
                "Globus_source_path": {
                    "type": "string",
                    "description": "Globus_source_path."
                },
                "Globus_target_path": {
                    "type": "string",
                    "description": "Globus_target_path."
                },
                "Globus_auth_code": {
                    "type": "string",
                    "description": "Globus_auth_code."
                },



                "Globus_task": {
                    "type": "boolean",
                    "description": "Globus_task."
                }
            },
            "required": [
                "ADMA_search_string", 
                "ADMA_menu_name", 
                "ADMA_API_file_path", 
                "Realm5_date_str", 
                "JD_ENREEC_field_id", 
                "JD_ENREEC_field_name", 
                "Realm5_variable_name_list", 
                "Google_drive_file_path", 
                "ADMA_API_token", 
                "Google_username",
                "Globus_source_collection",
                "Globus_collection",
                "Globus_target_collection",
                "Globus_path",
                "Globus_source_path",
                "Globus_target_path",
                "Globus_auth_code",
          
                "Globus_task"
            ],
            #"required": ["ADMA_search_string", "ADMA_menu_name", "ADMA_API_file_path", "Realm5_date_str", "JD_ENREEC_field_id", "JD_ENREEC_field_name", "Realm5_variable_name_list", "Google_drive_file_path", "ADMA_API_token", "Google_username"],
            "additionalProperties": False   
        }
    }
}


class controller:
    def __init__(self,meta_program_graph,executed_methods):

        self.meta_program_graph = meta_program_graph
        self.executed_methods = executed_methods
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.system_prompt = "You are a program controller. The user will tell you what they want to do."
        self.system_prompt += "You'll be given a sequence of methods, which has been executed in the previous steps. Try to find the method that should be executed in next step."
        self.system_prompt += "The meta program graph is a directed graph, which has two types of nodes, method nodes and variable nodes. Each node may have incoming edges and outgoing edges."

        #self.system_prompt += "Try to explore the meta program graph in a depth-first manner, if there's no method in current exploration path, try to find a new method to call."
        self.system_prompt += "Check each method in the meta program graph, check the value and description of each variable in the input list of each method. Choose the most appropriate method which can use these variables as input, and which once called will move the status towards the goal of user's instruction."
        #self.system_prompt += "You only need to observe the value and description of these variables: ADMA_url and local_file_path"
        #self.system_prompt += 'If you are confident you can answer user\'s instruction, based on these variables, you should make no further method call and you should only output a json with the following format: {"method": "None"}, with no other extra word at all.'
        #self.system_prompt += "Try your best to explore every possible path to approach the goal of user's instruction, do not be lazy!"
        self.system_prompt += 'Try to find a method which may lead you to the answer of user\'s instruction, you need to output a json with the following format: {"method": "the name of the method to call"}, with no other extra word at all.'
        self.system_prompt += 'If you feel confident that you can answer user\'s instruction, especially one variable contains what the user want, you can call one of the method whose name begins with "output". Note: once you call these output methods, you indicate the program ends with no further method calls.'
        self.system_prompt += 'If you feel you further information is needed, you can call one of the method whose name begins with "input".'
        self.system_prompt += 'If you feel you further information is needed, you can also call variable_initializer.'

        self.system_prompt += 'The name of the method should match one of the methods in the meta program graph. '
        self.system_prompt += 'Try your best to extract required information from the meta program graph, and reduce the needs to make method calls. But do not fabricate any information.'
        self.system_prompt += 'How to extract required information from the meta program graph? You can check the description of each variable and the correspondingvalue of each variable. Compare this information with user\'s instruction, and check if you can find the answer.'
        self.system_prompt += 'When you decide which method to call, you need to check the whole meta program graph to make sure you do not miss any information.'
        #self.system_prompt += "If you want to plot the data, you need to make sure 'tmp/Realm5_formatted_data.json' is the value of local_file_path in the meta program graph. "
        self.system_prompt += "When user request go to somewhere, try your best to find ways to get the adma url. "
        self.system_prompt += "If you see Chinese, first translate it to English."
        self.system_prompt += "You can only call the methods which exist in the meta program graph. "
        #self.system_prompt += "Note: only call a method, if all the variables in the input list of this method have value. "
        self.system_prompt += "Also, when it is needed, you need to call variable_initializer multiple times to modify the value of some variable, based on user's instruction, execution history and current status of meta program graph."
        self.system_prompt += "Note: timing is important, you need to understand what the user want you to do. For example, you can call variable_initializer after having executed some methods, and then call variable_initialzer again to modify the values of some of the variables and continue to call the subsequent methods."
        self.system_prompt += "Try your best to analyze user's intent, if user's instruction contains several steps, you need to arrange the best time to call variable_initializer, because some variable may need to initialize after you have executed some other methods." 
    def get_next_task(self):
        system_prompt = self.system_prompt + "Current meta program graph is: " + json.dumps(self.meta_program_graph)
        system_prompt += "The methods that have been executed in the previous steps are: " + json.dumps(self.executed_methods)
        #self.meta_program_graph["ADMA_list_directory_contents&output_list"]
        user_instruction = self.meta_program_graph["user_instruction"]["value"]

        response = self.client.beta.chat.completions.parse(
            model="gpt-4o-2024-08-06",
           
            messages=[{"role": "system", "content": system_prompt},
                      {"role": "user", "content": user_instruction}],
            response_format= controller_output,
            temperature=temperature,
        )
        #print(response.choices[0].message.content)
        result = json.loads(response.choices[0].message.content)
        if result["method"] != "None":
            self.executed_methods.append(result["method"])
        return json.loads(response.choices[0].message.content)#response.choices[0].message.parsed
    

                                
class meta_program_graph_initializer:
    def __init__(self,meta_program_graph,executed_methods):
        
        self.meta_program_graph = meta_program_graph
        self.executed_methods = executed_methods
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.system_prompt = "Given the user's instruction, you need to initialize the variables in meta program graph."
        
        #self.system_prompt += "Note: only initialize the variables purely based on the user's instruction, and do not fabricate any information or check the value in meta program graph."
        self.system_prompt += "Only initialize the variables purely based on the user's instruction, and do not fabricate any information."
        self.system_prompt += "For Realm5_variable_name_list, you need to initialize it as a list of realm5 variable names, which introduced in the description of Realm5_variable_name_list in the meta program graph."
        self.system_prompt += "For ADMA_menu_name, it should be one of the following: search, shared_with_me, files, data, models, tools, collections, documentation, api. When user asked for going to public data, you should set this to 'shared_with_me', when the user ask for all the data on ADMA, you should set this to 'data',when the user want to know how to use ADMA, you should set this to documentation, when user asked to go to file or folder followed by a path, you should set this menu name to 'files'. If the user asked root folder, you should set the path to empty string."
        #self.system_prompt += "If you see a file name or a path, you should set the value of ADMA_API_file_path to the file name or the path."
        self.system_prompt += "If you see Chinese, first translate it to English."
        self.system_prompt += "If the user ask for token on adma, you should set ADMA_menu_name to 'api'."
        self.system_prompt += "Note: If the user's instruction contains required information, you can set the value of the variable based on the information. "
        self.system_prompt += "Note: If you can not find the value of a variable from the user's instruction, you must set the value to 'NA'."
        #self.system_prompt += "Timing is important. Sometimes even you can find the value from user's instruction, but based on user's intent,  If it is not appropriate to set the value now, you should postpone and set the value to 'NA' now."
   

        

    def initialize_meta_program_graph(self):
        user_instruction = self.meta_program_graph["user_instruction"]["value"]

        system_prompt = self.system_prompt + "Current meta program graph is: " + json.dumps(self.meta_program_graph)
        system_prompt += "The methods that have been executed in the previous steps are: " + json.dumps(self.executed_methods)


        response = self.client.beta.chat.completions.parse(
            model="gpt-4o-2024-08-06",
            messages=[{"role": "system", "content": system_prompt},
                      {"role": "user", "content": user_instruction}],
            response_format= initializer_output,
            temperature=temperature,
        )
        return json.loads(response.choices[0].message.content)
    

    
class variable_value_setter:
    def __init__(self,meta_program_graph,executed_methods):
        
        self.meta_program_graph = meta_program_graph
        self.executed_methods = executed_methods
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.system_prompt = "Given the user's instruction, you need to return the value of ADMA_API_file_path."
        

        

    def get_value(self):
        user_instruction = self.meta_program_graph["user_instruction"]["value"]

        system_prompt = self.system_prompt + "Current meta program graph is: " + json.dumps(self.meta_program_graph)
        system_prompt += "The methods that have been executed in the previous steps are: " + json.dumps(self.executed_methods)


        response = self.client.beta.chat.completions.parse(
            model="gpt-4o-2024-08-06",
            messages=[{"role": "system", "content": system_prompt},
                      {"role": "user", "content": user_instruction}],

            temperature=temperature,
        )
        return json.loads(response.choices[0].message.content)
    




def stream_data(stream):
    for word in stream.split(" "):
        yield word + " "
        time.sleep(0.01)

def create_map(lat,lng):
    # Create the map with Google Maps
    map_obj = folium.Map(tiles=None,location=[lat,lng], zoom_start=15)
    folium.TileLayer("https://{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}", 
                     attr="google", 
                     name="Google Maps", 
                     overlay=True, 
                     control=True, 
                     subdomains=["mt0", "mt1", "mt2", "mt3"]).add_to(map_obj)
    return map_obj

def get_next_task(program_controller):
    if program_controller.executed_methods == []:
        next_task = {"method":"variable_initializer"}
        program_controller.executed_methods.append("variable_initializer")
    elif program_controller.executed_methods[-1][:5] == "input":
        next_task = {"method":"variable_initializer"}
        program_controller.executed_methods.append("variable_initializer")
    elif program_controller.executed_methods[-1] == "Google_drive_connect":
        next_task = {"method":"Google_drive_generate_credentials"}
        program_controller.executed_methods.append("Google_drive_generate_credentials")
    #elif program_controller.executed_methods[-1] == "Get_Globus_auth_url":
    #    next_task = {"method":"Get_Globus_token"}
    #    program_controller.executed_methods.append("Get_Globus_token")

    else:
        next_task = program_controller.get_next_task()

    result = {"type": "middle_instruction","output": f"{next_task['method']}"}
    ai_reply(result)
    bot_message = {"role": "assistant","content": result}
    st.session_state['chat_history'].append(bot_message)

    return next_task

def get_answer(prompt,max_iter=10):

    

    if 'program_controller' not in st.session_state:
        with open("meta_program_graph_new2.json") as f:
            meta_program_graph = json.load(f)
        executed_methods = []
        st.session_state.program_controller = controller(meta_program_graph,executed_methods)
        st.session_state.initializer = meta_program_graph_initializer(meta_program_graph,executed_methods)
        st.session_state.value_setter = variable_value_setter(meta_program_graph,executed_methods)
    

    program_controller = st.session_state.program_controller
    initializer = st.session_state.initializer

    value_setter = st.session_state.value_setter

    # start a new instruction
    if len(program_controller.executed_methods) == 0:

        program_controller.meta_program_graph["user_instruction"]["value"] = prompt
    # continue with the former instruction
    else:
        program_controller.meta_program_graph["user_instruction"]["value"] += program_controller.meta_program_graph["next_prompt"]["value"]+prompt


    meta_program_graph = program_controller.meta_program_graph
    


    result = {}
    #print(meta_program_graph["Realm5_date_str"]["value"])
    



    while max_iter >= 0:
        #print(meta_program_graph["local_file_path"]["value"])
        max_iter -= 1
        #next_task = program_controller.get_next_task()
        next_task = get_next_task(program_controller)
        
        variables = {}
        variables["Realm5_variable_name_list"] = meta_program_graph["Realm5_variable_name_list"]["value"]
        variables["Google_username"] = meta_program_graph["Google_username"]["value"]
        variables["Google_drive_redirect_url"] = meta_program_graph["Google_drive_redirect_url"]["value"]
        variables["Google_drive_credentials"] = meta_program_graph["Google_drive_credentials"]["value"]
        variables["Google_drive_file_path"] = meta_program_graph["Google_drive_file_path"]["value"]
        variables["local_file_path"] = meta_program_graph["local_file_path"]["value"]
        variables["ADMA_API_token"] = meta_program_graph["ADMA_API_token"]["value"]
        variables["ADMA_API_file_path"] = meta_program_graph["ADMA_API_file_path"]["value"]
        variables["ADMA_API_file_path_list"] = meta_program_graph["ADMA_API_file_path_list"]["value"]
        variables["ADMA_API_file_path_list_index"] = meta_program_graph["ADMA_API_file_path_list_index"]["value"]
        variables["ADMA_menu_name"] =  meta_program_graph["ADMA_menu_name"]["value"]

        variables["Globus_path"] = meta_program_graph["Globus_path"]["value"]
        variables["Globus_collection"] = meta_program_graph["Globus_collection"]["value"]
        variables["Globus_auth_url"] = meta_program_graph["Globus_auth_url"]["value"]
        variables["Globus_auth_code"] = meta_program_graph["Globus_auth_code"]["value"]

        print(variables)
        print(next_task)
        #print(program_controller.executed_methods)


        if next_task["method"] == "variable_initializer":
            # initialize the meta program graph
            initialized_variables = initializer.initialize_meta_program_graph()
            #print(initialized_variables)
            for variable in initialized_variables:
                if initialized_variables[variable] != "NA" :
                    meta_program_graph[variable]["value"] = initialized_variables[variable]

        elif next_task["method"] == "Get_Globus_auth_url":
            program_controller.meta_program_graph["Globus_auth_url"]["value"] = get_authorize_url()

        elif next_task["method"] == "input_Globus_auth_code":
            globus_auth_url = program_controller.meta_program_graph["Globus_auth_url"]["value"]
            result = {"type": "message","output": f"Click this link: {globus_auth_url}, and input the auth code:"} 
            program_controller.meta_program_graph["next_prompt"]["value"] = "The Globus auth code is: "
            break

        elif next_task["method"] == "Get_Globus_token":
            auth_code = program_controller.meta_program_graph["Globus_auth_code"]["value"]
            if auth_code == "":
                continue
            program_controller.meta_program_graph["Globus_token"]["value"] = get_transfer_token(auth_code)

        elif next_task["method"] == "Get_Globus_token2":

            program_controller.meta_program_graph["Globus_token"]["value"] = get_transfer_token2()

        elif next_task["method"] == "Globus_list":
            globus_token = program_controller.meta_program_graph["Globus_token"]["value"]
            endpoint = program_controller.meta_program_graph["Globus_collection"]["value"]
            path = program_controller.meta_program_graph["Globus_path"]["value"]
            program_controller.meta_program_graph["Globus_path_list"]["value"] = list_folder(globus_token, endpoint, path)

        elif next_task["method"] == "Globus_transfer":
            globus_token = program_controller.meta_program_graph["Globus_token"]["value"]
            source_endpoint = program_controller.meta_program_graph["Globus_source_collection"]["value"]
            target_endpoint = program_controller.meta_program_graph["Globus_target_collection"]["value"]
            source_path = program_controller.meta_program_graph["Globus_source_path"]["value"]
            target_path = program_controller.meta_program_graph["Globus_target_path"]["value"]
            program_controller.meta_program_graph["Globus_path_list"]["value"] =  transfer_file(globus_token, source_endpoint, target_endpoint, source_path, target_path)

        elif next_task["method"] == "output_Globus_path_list":
            result = {"type": "Globus_path_list","output": meta_program_graph["Globus_path_list"]["value"]}
            break

        elif next_task["method"] == "output_Globus_task_id":
            result = {"type": "message","output": f"The file transfer task is submitted to Globus with the task id: {meta_program_graph["Globus_task_id"]["value"]}"}
            break
        


        #elif next_task["method"]== "ADMA_API_file_path_setter":
        #    meta_program_graph["ADMA_API_file_path"] = value_setter.get_value()

        elif next_task["method"] == "input_date_string":
            result = {"type": "message","output": "Please input a date string for Realm5."} 
            program_controller.meta_program_graph["next_prompt"]["value"] = "The data string for Realm5 is: "
            break

        elif next_task["method"] == "input_ADMA_API_token":
            result = {"type": "message","output": "Please input your token for ADMA API."}
            program_controller.meta_program_graph["next_prompt"]["value"] = "The token for ADMA API is: "
            break
        elif next_task["method"] == "input_Google_username":
            result = {"type": "message","output": "Please input your username."}
            program_controller.meta_program_graph["next_prompt"]["value"] = "The username is: "
            break

        elif next_task["method"] == "Google_drive_connect":
            if program_controller.meta_program_graph["Google_drive_redirect_url"]["value"] != "":
                continue
            username = program_controller.meta_program_graph["Google_username"]["value"]
            print(f"username: {username}")
            if not username:
                continue

            credential_file = f"tmp/google_drive_credential_{username}.json"
            if os.path.exists(credential_file):
                credentials = Credentials.from_authorized_user_file(credential_file,SCOPES)
                if credentials:
                    continue

            

            meta_program_graph["Google_drive_redirect_url"]["value"] = google_drive_auth(username)
            result = {"type": "google_drive_url","output": meta_program_graph["Google_drive_redirect_url"]["value"]}
            ai_reply(result)
            bot_message = {"role": "assistant","content": result}
            st.session_state['chat_history'].append(bot_message)
            

        elif next_task["method"] == "Google_drive_generate_credentials":
            username = meta_program_graph["Google_username"]["value"]
            if not username:
                continue
            meta_program_graph["Google_drive_credentials"]["value"] = google_drive_generate_credentials(meta_program_graph["Google_drive_redirect_url"]["value"],username)

        elif next_task["method"] == "Google_drive_list_directory":
            meta_program_graph["Google_drive_file_path_list"]["value"] = google_drive_list(meta_program_graph["Google_drive_credentials"]["value"],meta_program_graph["Google_drive_file_path"]["value"])

        elif next_task["method"] == "output_Google_drive_file_path_list_printer":
            result = {"type": "google_drive_file_list","output": meta_program_graph["Google_drive_file_path_list"]["value"]}
            break

        elif next_task["method"] == "Google_drive_download_file":
            
            meta_program_graph["local_file_path"]["value"] = google_drive_download_file(meta_program_graph["Google_drive_credentials"]["value"],meta_program_graph["Google_drive_file_path"]["value"])
            meta_program_graph["local_file_path"]["description"] = f"local_file_path is the downloaded local file path of {meta_program_graph['Google_drive_file_path']['value']} from Google Drive."
        
        elif next_task["method"] == "ADMA_upload_file":
            if not meta_program_graph["local_file_path"]["value"] or not meta_program_graph["ADMA_API_token"]["value"]:
                continue
            if not os.path.exists(meta_program_graph["local_file_path"]["value"]):
                continue
            meta_program_graph["ADMA_API_file_path"]["value"] = ADMA_upload_file(meta_program_graph["local_file_path"]["value"],meta_program_graph["ADMA_API_file_path"]["value"],meta_program_graph["ADMA_API_token"]["value"])
            meta_program_graph["ADMA_API_file_path"]["description"] = f"ADMA_API_file_path is the path of the already uploaded file {meta_program_graph['local_file_path']['value']} on the ADMA server."
            print(meta_program_graph["ADMA_API_file_path"]["value"])


        # process different methods
        elif next_task["method"] == "output_download_file":
            result = {"type": "download","output": meta_program_graph["local_file_path"]["value"]}
            break
        elif next_task["method"] == "output_plot_weather_data":
            result = {"type": "plot_Realm5_data","output": meta_program_graph["local_file_path"]["value"]}
            break
        elif next_task["method"] == "output_field_boundary_map":
            result = {"type": "map","output": meta_program_graph["local_file_path"]["value"]}
            break
        elif next_task["method"] == "output_JD_ENREEC_field_list_printer":
            result = {"type": "JD_field_list","output": meta_program_graph["local_file_path"]["value"]}
            break
        elif next_task["method"] == "output_ADMA_url_browser":
            result = {"type": "url","output": meta_program_graph["ADMA_url"]["value"]}
            break
        elif next_task["method"] == "output_ADMA_meta_data_list_printer":
            result = {"type": "object","output": meta_program_graph["ADMA_meta_data_list"]["value"]}
            break
        elif next_task["method"] == "output_ADMA_meta_data_printer":
            result = {"type": "object","output": meta_program_graph["ADMA_meta_data"]["value"]}
            break
        elif next_task["method"] == "output_ADMA_API_file_path_list_printer":
            result = {"type": "object","output": meta_program_graph["ADMA_API_file_path_list"]["value"]}
            break

        
        elif next_task["method"] == "ADMA_list_directory":

            dir_path = meta_program_graph["ADMA_API_file_path"]["value"]
            token = meta_program_graph["ADMA_API_token"]["value"]
            if not token:
                continue
            
            # update the value of the output list
            meta_program_graph["ADMA_API_file_path_list"]["value"] = ADMA_list_dir(dir_path,token)

            # update the description of the output list
            #meta_program_graph["ADMA_API_file_path_list"]["description"] = meta_program_graph["ADMA_API_file_path"]["description"]+"\n"
            meta_program_graph["ADMA_API_file_path_list"]["description"] = f"ADMA_API_file_path_list is a list of paths under the directory {dir_path} in the ADMA system."

        elif next_task["method"] == "ADMA_get_meta_data":

            path = meta_program_graph["ADMA_API_file_path"]["value"]
            token = meta_program_graph["ADMA_API_token"]["value"]
            if not token:
                continue
            # update the value of the meta data
            #print(f"ADMA_API_file_path: {path}")
            meta_program_graph["ADMA_meta_data"]["value"] = ADMA_get_meta_data(path,token)
            # update the description of the meta data
            #meta_program_graph["ADMA_meta_data"]["description"] = meta_program_graph["ADMA_API_file_path"]["description"]+"\n"
            meta_program_graph["ADMA_meta_data"]["description"] = f"ADMA_meta_data is the meta data of the file or directory {path} in the ADMA system."


        elif next_task["method"] == "ADMA_API_file_path_list_iterator":

            index = meta_program_graph["ADMA_API_file_path_list_index"]["value"]

            output_list = meta_program_graph["ADMA_API_file_path_list"]["value"]

            

            if index < len(output_list):
                # update the value of the path
                meta_program_graph["ADMA_API_file_path"]["value"] = output_list[index]
                meta_program_graph["ADMA_API_file_path_list_index"]["value"] = index + 1
                #print(meta_program_graph["ADMA_API_file_path_list_index"]["value"])

                # update the description of the path
                #meta_program_graph["ADMA_API_file_path"]["description"] = meta_program_graph["ADMA_API_file_path_list"]["description"]+"\n"
                meta_program_graph["ADMA_API_file_path"]["description"] = f"ADMA_API_file_path is path of the file or directory at the index {index} of ADMA_API_file_path_list."

                meta_program_graph["ADMA_API_file_path_list_index"]["description"] = f"ADMA_API_file_path_list_iterator should be called several times until the value of ADMA_API_file_path_list_index is equal to {len(meta_program_graph['ADMA_API_file_path_list']['value'])}."

       
        elif next_task["method"] == "ADMA_push_to_meta_data_list":
            
            meta_data = meta_program_graph["ADMA_meta_data"]["value"]
            #push the meta data to the list
            #meta_program_graph["ADMA_push_to_meta_data_list&output_list"]["value"].append(meta_data)
            # append a deep copy of the meta data
            meta_program_graph["ADMA_meta_data_list"]["value"].append(copy.deepcopy(meta_data))
            #meta_program_graph["ADMA_meta_data_list"]["description"] = meta_program_graph["ADMA_meta_data"]["description"]+"\n"
            #api_path = "/".join(meta_data["abs_path"].split("/")[3:])
            #meta_program_graph["ADMA_meta_data_list"]["description"] += f"The meta data of {api_path} on the ADMA server was just added to the list."
            meta_program_graph["ADMA_meta_data_list"]["description"] = f"Now the length of the list is {len(meta_program_graph['ADMA_meta_data_list']['value'])}. Normally, the length of the list should be equal to {len(meta_program_graph['ADMA_API_file_path_list']['value'])}."
            


        elif next_task["method"] == "ADMA_menu_option":
      
            menu_name = meta_program_graph["ADMA_menu_name"]["value"]

            path = meta_program_graph["ADMA_API_file_path"]["value"]

            meta_program_graph["ADMA_url"]["value"] = ADMA_menu_option(menu_name,path)
            print(meta_program_graph["ADMA_url"]["value"])
            #meta_program_graph["ADMA_url"]["description"] = meta_program_graph["ADMA_menu_name"]["description"]+"\n"
            #meta_program_graph["ADMA_url"]["description"] += meta_program_graph["ADMA_API_file_path"]["description"]+"\n"
            if menu_name == "files":
                meta_program_graph["ADMA_url"]["description"] = f"ADMA_url is a url for the directory {path} under the root folder on the ADMA server."
            else:
                meta_program_graph["ADMA_url"]["description"] = f"ADMA_url is a url for the page: {menu_name} on the ADMA server."
                
        
        elif next_task["method"] == "JD_ENREEC_boundary_in_field":

            field_id = meta_program_graph["JD_ENREEC_field_id"]["value"]
            
            meta_program_graph["local_file_path"]["value"] = json.loads(query_ENREEC_boundary_in_field(field_id))["path"]

            #meta_program_graph["local_file_path"]["description"] = meta_program_graph["JD_ENREEC_field_id"]["description"]+"\n"
            meta_program_graph["local_file_path"]["description"] = f"local_file_path is the boundary file for the field with field id {field_id} in ENREEC."
        
        elif next_task["method"] == "JD_ENREEC_fields":
            fields_file_path = query_ENREEC_fields_file()
            meta_program_graph["local_file_path"]["value"] = fields_file_path
            meta_program_graph["local_file_path"]["description"] = f"local_file_path is the json file path containing all the fields in ENREEC from John Deere."

        elif next_task["method"] == "JD_ENREEC_field_id_from_name":
 
            field_name = meta_program_graph["JD_ENREEC_field_name"]["value"]
                
            meta_program_graph["JD_ENREEC_field_id"]["value"] = field_id_from_name(field_name)
            #meta_program_graph["JD_ENREEC_field_id"]["description"] = meta_program_graph["JD_ENREEC_field_name"]["description"]+"\n"
            meta_program_graph["JD_ENREEC_field_id"]["description"] = f"JD_ENREEC_field_id is the field id of the field {field_name} in ENREEC from John Deere."

            
        elif next_task["method"] == "Realm5_generate_file_url":

            date_str = meta_program_graph["Realm5_date_str"]["value"]

            meta_program_graph["ADMA_API_file_path"]["value"] = Realm5_generate_file_url(date_str)
            
            #print(meta_program_graph["ADMA_API_file_path"]["value"])
            #meta_program_graph["ADMA_API_file_path"]["description"] = meta_program_graph["Realm5_date_str"]["description"]+"\n"
            meta_program_graph["ADMA_API_file_path"]["description"] = f"ADMA_API_file_path is the url of the Reaml5 file on ADMA for {date_str} to be downloaded."

        elif next_task["method"] == "ADMA_download_file":
  
            file_url = meta_program_graph["ADMA_API_file_path"]["value"]
            token = meta_program_graph["ADMA_API_token"]["value"]
            if not token:
                continue
            
            meta_program_graph["local_file_path"]["value"] = ADMA_download_file(file_url,token)
            #print(meta_program_graph["local_file_path"]["value"])
            #meta_program_graph["local_file_path"]["description"] = meta_program_graph["ADMA_API_file_path"]["description"]+"\n"
            meta_program_graph["local_file_path"]["description"] = f"local_file_path is the downloaded local file path of {file_url} from ADMA."


        elif next_task["method"] == "Realm5_format_data_for_plot":
  
            variable_names = meta_program_graph["Realm5_variable_name_list"]["value"]
            
            old_path = meta_program_graph["local_file_path"]["value"]
            meta_program_graph["local_file_path"]["value"] = Realm5_format_data_for_plot(meta_program_graph["local_file_path"]["value"],variable_names)
            if not meta_program_graph["local_file_path"]["value"] == old_path:

                #print(meta_program_graph["local_file_path"]["value"])
                #meta_program_graph["local_file_path"]["description"] = meta_program_graph["local_file_path"]["description"]+"\n"
                #meta_program_graph["local_file_path"]["description"] += meta_program_graph["Realm5_variable_name_list"]["description"]+"\n"
                meta_program_graph["local_file_path"]["description"] = f"local_file_path is the file path of the formatted Realm5 data for variables {variable_names}."

        elif next_task["method"] == "ADMA_search":
       
            search_string = meta_program_graph["ADMA_search_string"]["value"]
            token = meta_program_graph["ADMA_API_token"]["value"]
            if not token:
                continue
            
   
            path = meta_program_graph["ADMA_API_file_path"]["value"]
            
            meta_program_graph["ADMA_meta_data"]["value"] = ADMA_search(token,path,search_string)
            #print(meta_program_graph["ADMA_meta_data"]["value"])
            #meta_program_graph["ADMA_meta_data"]["description"] = meta_program_graph["ADMA_search_string"]["description"]+"\n"
            meta_program_graph["ADMA_meta_data"]["description"] = f"ADMA_meta_data is the meta data of the file or folder on the ADMA system searched by {search_string}."

       
        elif next_task["method"] == "ADMA_url_extractor":
            
            meta_program_graph["ADMA_url"]["value"] = ADMA_url_extractor(meta_program_graph["ADMA_meta_data"]["value"])
            #meta_program_graph["ADMA_url"]["description"] = meta_program_graph["ADMA_meta_data"]["description"]+"\n"
            #api_path = "/".join(meta_program_graph["ADMA_meta_data"]["value"]["abs_path"].split("/")[3:])
            meta_program_graph["ADMA_url"]["description"] = f"ADMA_url is the url of the file or directory on ADMA."


        #print(f"ADMA_url: {meta_program_graph['ADMA_url']['value']}, local_file_path: {meta_program_graph['local_file_path']['value']}")
                
                
                
    
    if max_iter <0:
        result = {"type": "error","output": "I cannot find the answer to your question. Please try again."}
    # if there's an output, clear the executed methods, the meta program graph and the user_instruction, which means current instruction is finished
    if next_task["method"][:6] == "output" or max_iter < 0:
        print("clear")
        program_controller.executed_methods = []
        initializer.executed_methods = program_controller.executed_methods

        value_setter.executed_methods = program_controller.executed_methods

        with open("meta_program_graph_new2.json") as f:
            meta_program_graph = json.load(f)
        # keep the google drive redirect url for this session
        google_drive_redirect_url = program_controller.meta_program_graph["Google_drive_redirect_url"]
        username = program_controller.meta_program_graph["Google_username"]["value"]
        ADMA_API_token = program_controller.meta_program_graph["ADMA_API_token"]["value"]

        program_controller.meta_program_graph = meta_program_graph
        initializer.meta_program_graph = meta_program_graph
        value_setter.meta_program_graph = meta_program_graph

        program_controller.meta_program_graph["Google_drive_redirect_url"] = google_drive_redirect_url
        program_controller.meta_program_graph["Google_username"]["value"] = username
        program_controller.meta_program_graph["ADMA_API_token"]["value"] = ADMA_API_token



   




    return result

def ai_reply(response, if_history=False):
    if response["type"] == "middle_instruction":
        st.markdown(f"###### :green[Call method:] :gray[{response['output']}]")
        return
    elif response["type"] == "Globus_path_list":
        st.json(response["output"],expanded=True)

    elif response["type"] == "message":
        st.chat_message("assistant", avatar="🤖").write(response["output"])
        return
    elif response["type"] == "google_drive_url":
        with st.chat_message("assistant", avatar="🤖"):
            st.write("Please click the following link to connect to Google Drive:")
            st.markdown(f"{response['output']}")
        return


    elif response["type"] == "error":
        st.chat_message("assistant", avatar="🤖").write(response["output"])
        return
    elif response["type"] == "download":
        if not response["output"]:
            st.chat_message("assistant", avatar="🤖").write("No data found.")
            return
        elif not os.path.exists(response["output"]):
            st.chat_message("assistant", avatar="🤖").write("No data found for the field")
            return
  
        with open(response["output"],"rb") as f:
            data = f.read()
          
        st.download_button(label="Download",data=data,file_name=os.path.basename(response["output"]),key=uuid.uuid4())
        return
    elif response["type"] == "plot_Realm5_data":
        if not os.path.exists(response["output"]):
            st.chat_message("assistant", avatar="🤖").write("No data found for the field")
            return
        with open(response["output"]) as f:        
            data = json.load(f)
        df = pd.DataFrame(data)
    
        st.line_chart(df,width=1200,height=600)
    elif response["type"] == "JD_field_list":
        if not os.path.exists(response["output"]):
            st.chat_message("assistant", avatar="🤖").write("No data found for the field")
            return
        with open(response["output"]) as f:
            output = f.read()
        
        st.json(json.loads(output),expanded=False)
    elif response["type"] == "object":

        st.json(response["output"],expanded=False)

    elif response["type"] == "google_drive_file_list":
        
        if not response["output"]:
            st.write("No files found.")
        else:
            st.markdown("#### The files in your Google Drive are:")
            st.markdown("<style>table{width:100%;border-collapse:collapse;background-color:white}th{text-align:left;padding:8px;}td{padding:8px;vertical-align:top;}tr{border-bottom:1px solid grey;}tr:last-child{border-bottom:none;}</style>", unsafe_allow_html=True)
            
            #for file in response["output"]:
                #st.markdown(f"<a href={file['webViewLink']}>{file['name']}</a>",unsafe_allow_html=True)
            #    st.write(f"[{file['name']}]({file['webViewLink']})")
            col1, col2, col3, col4, col5 = st.columns([3,2,2,2,1])
            with col1:
                st.markdown(f"{'Name'} ")
            with col2:
                st.markdown(f"{'Owner'}")
            with col3:
                st.markdown(f"{'Created Time'}")
            with col4:
                st.markdown(f"{'Last Modified'}")
            with col5:
                st.markdown(f"{'Size'}")
 
            
            #html_code = ' <!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Styled Table</title><style>table{width:100%;border-collapse:collapse;background-color:white}th{text-align:left;padding:8px;}td{padding:8px;vertical-align:top;}tr{border-bottom:1px solid grey;}tr:last-child{border-bottom:none;}</style></head><body><table><thead><tr><th>Name</th><th>Owner</th><th>Created Time</th><th>Last Modified</th><th>Size</th></tr></thead>'
            #html_code += '<tbody>'
            for file in response["output"]:
                if  "Untitled" in file["name"]:
                    continue
                if "size" in file:
                    size = str(int(int(file["size"])/1000)) +"KB"
                else:
                    size = ""

                # Set up two columns: one for text and one for the button
                col1, col2, col3, col4, col5 = st.columns([3,2,2,2,1])
                with col1:
                    st.markdown(f"[{file['name'].ljust(30)}]({file['webViewLink']})  ")
                with col2:
                    st.markdown(f"{file['owners'][0]['displayName']}")
                with col3:
                    st.markdown(f"{file['createdTime']}")
                with col4:
                    st.markdown(f"{file['modifiedTime']}")
                with col5:
                    st.markdown(f"{size}")

   
                        

        
   

                
                
                
                #html_code += f'<tr><td><a href="{file["webViewLink"]}" target="_blank">{file["name"]}</a></td><td>{file["owners"][0]["displayName"]}</td><td>{file["createdTime"]}</td><td>{file["modifiedTime"]}</td><td>{size}</td></tr><tr>'
            #html_code +='</tbody></table></body></html>'
            #st.components.v1.html(html_code, width=1240)




  

    elif response["type"] == "url":
        html_code = f"""
            <iframe src={response["output"]} width="1250" height="800" frameborder="0"></iframe>
            """
        print(response["output"])

        st.components.v1.html(html_code, width=1240, height=790)
    elif response["type"] == "map":
        path = response["output"]
        if not os.path.exists(path):
            if if_history:
                st.chat_message("assistant", avatar="🤖").write("No boundary found for the field")
            else:
                st.chat_message("assistant", avatar="🤖").write(stream_data("No boundary found for the field"))

        else:
            with open(path) as f:
                boundary = json.load(f)
            #print(boundary)
            if not "values" in boundary:
                st.chat_message("assistant", avatar="🤖").write("No boundary found for the field")
                return
            if len(boundary["values"]) == 0:
                if if_history:
                    st.chat_message("assistant", avatar="🤖").write("No boundary found for the field")
                else:
                    st.chat_message("assistant", avatar="🤖").write(stream_data("No boundary found for the field"))

                return
            else:
                print(path)
                rings = boundary["values"][0]["multipolygons"][0]["rings"]
            
            all_ring_coordinates = []
            for ring in rings:
                ring_coordinates = []
                for point in ring["points"]:
                    ring_coordinates.append([float(point["lat"]),float(point["lon"])])
                all_ring_coordinates.append(ring_coordinates)

            m = create_map(all_ring_coordinates[0][0][0],all_ring_coordinates[0][0][1])

            #m = folium.Map(location=[all_ring_coordinates[0][0][0],all_ring_coordinates[0][0][1]], zoom_start=16)
            for ring_coordinates in all_ring_coordinates:
                folium.PolyLine(ring_coordinates, tooltip="Field Boundaries").add_to(m)
            
            for ring_coordinates in all_ring_coordinates:
                folium.Polygon(
                    locations=ring_coordinates,
                    color='blue',  # Color of the polygon border
                    weight=0,  # Width of the border
                    fill=True,
                    fill_color='#3388ff',  # Fill color of the polygon
                    fill_opacity=0.8,  # Opacity of the fill (0-1)
                    tooltip="Field Boundaries"
                ).add_to(m)
            
            folium_static(m,height=600,width=1200)



def display_chat_history():
    # Display chat history
    for message in st.session_state['chat_history']:
      if message['role'] == "user":
          # avatar is a emoji
          st.chat_message("user",avatar="👨‍🎓").write(message['content'])
      elif message['role'] == "assistant":
          ai_reply(message['content'],if_history=True)
          #st.chat_message("assistant", avatar="🤖").write(message['content'])  

def main():
 
    #set the page title and icon
    #the icon is a green leaf
    st.set_page_config(page_title="ADMA Copilot", page_icon="🍃")
    st.header("ADMA Copilot",divider="green")

    # Custom CSS to align iframe and chat messages to the left
    st.markdown(
        """
        <style>
        .left-align {
            display: flex;
            justify-content: flex-start;
            align-items: flex-start;
        }
        .iframe-container {
            width: 100%;
            max-width: 1200px;
            height: 800px;
            border: 1px solid #ddd;
        }
        .chat-container {
            width: 100%;
            max-width: 800px;
        }
        .st-emotion-cache-1eo1tir{
        max-width: 80rem;
        }
        .st-emotion-cache-arzcut{
        max-width: 80rem;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    



    #st.sidebar.title("Control Panel")



    # Load meta program graph
    
    #with open("meta_program_graph_new.json") as f:
    #    meta_program_graph = json.load(f)



    #upload file
    #files = st.sidebar.file_uploader("Upload Your File",accept_multiple_files=True)
    #for file in files:
    #    st.write(file.name)

    # Initialize the session state for chat history if it does not exist
    if 'chat_history' not in st.session_state:
        st.session_state['chat_history'] = []

    if 'buttons' not in st.session_state:
        st.session_state['button_prompt'] = ""

    display_chat_history()

    prompt = st.chat_input("Ask Me Anything About Your AgData")
 

    print(prompt)

    
    



    
    if prompt:
  
        # Update chat history with user message
        user_message = {"role": "user",  "content": f"{prompt}"}
        st.session_state['chat_history'].append(user_message)
        st.chat_message("user",avatar="👨‍🎓").write(prompt)

        # response is a json object with the following format: {"type": "the type of the output", "output": "the json string"}
        response = get_answer(prompt,max_iter=30)

        ai_reply(response)

        
        bot_message = {"role": "assistant","content": response}
        st.session_state['chat_history'].append(bot_message)



   



if __name__ == '__main__':
    main()

