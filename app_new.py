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
                            },
                            "args": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {
                                            "type": "string",
                                            "description": "The name of the argument, which should be one of the keys in the meta program graph."
                                        },
                                        "value": {
                                            "type": "string",
                                            "description": "The value of the argument, which should be one of the values in the meta program graph. Set to DEFAULT if you want to use the value in the meta program graph, otherwise set to the value you want to use."
                                        }
                                    },
                                    "required": ["name", "value"],
                                    "additionalProperties": False
                                },
                                "description": "List of argument name-value pairs."
                            }
                        },
                        "required": ["method", "args"],
                        "additionalProperties": False
                    }
                }
            }

output_type = {
                "type": "json_schema",
                "json_schema": {
                    "name": "output_type",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "output_type": {
                                "type": "string",
                                "enum": ["string", "map","url","file","data","object"],
                                "description": "The type of the output."
                            }
                        },
                        "required": ["output_type"],
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
                    "description": "ADMA_menu_name."
                },
                "ADMA_API_file_path": {
                    "type": "string",
                    "description": "ADMA_API_file_path."
                },
                "Date_string": {
                    "type": "string",
                    "description": "Date_string."
                },
                "Field_ID": {
                    "type": "string",
                    "description": "Field_ID."
                },
                "Field_name": {
                    "type": "string",
                    "description": "Field_name."
                },
                "Realm5_variable_name_list": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                }
            },
            "required": ["ADMA_search_string", "ADMA_menu_name", "ADMA_API_file_path", "Date_string", "Field_ID", "Field_name", "Realm5_variable_name_list"],
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
        self.system_prompt += "Try to explore the meta program graph as much as possible, if one execution sequence is not working, start from scratch and try another execution sequence."
        self.system_prompt += "Check each method in the meta program graph, check the value of each variable in the input list of each method, or set the value of some variable based on the instruction of the user. Choose the most appropriate method which once called will move the status towards the goal of user's instruction."
        self.system_prompt += "Given the following meta program graph which contains the information of each method and each variable, you need to decide if you should call any method and if yes, the method to call."
        self.system_prompt += 'If you find enough information in current meta program graph to answer user\'s question, you should make no method call and you should only output a json with the following format: {"method": "None","args": []}, with no other extra word at all.'
        self.system_prompt += 'Else if you do not find enough information in current meta program graph to answer user\'s question, you need to output a json with the following format: {"method": "the name of the method to call","args": [{"name": "the name of the argument", "value": "the value of the argument"},...]}, with no other extra word at all.'
        self.system_prompt += 'The name of the method should match one of the methods in the meta program graph, and the arg_name should match one of the keys in the meta program graph, and also be the element in the "input" field of the method. If you decide to use the values in the meta program graph, you only need to set the values of the arguments as "DEFAULT", otherwise you need to set the values of the arguments as the values you want to use.'
        self.system_prompt += 'Try your best to extract required information from the meta program graph, and reduce the needs to make method calls. But do not fabricate any information.'
        self.system_prompt += 'How to extract required information from the meta program graph? You can check the description of each variable and the correspondingvalue of each variable. Compare this information with user\'s question, and check if you can find the answer.'
        self.system_prompt += 'You can set the value of any variable to whatever you want, but DO NOT make up any information that does not exist in user\'s instruction.'
        self.system_prompt += 'When you decide which method to call, you need to check the whole meta program graph to make sure you do not miss any information.'
        self.system_prompt += "If you want to plot the data, you need to make sure 'tmp/Realm5_formatted_data.json' is the value of Realm5_format_data_for_plot&formatted_data_file_path in the meta program graph. "
    
    def get_next_task(self,user_instruction):
        system_prompt=self.system_prompt + "Current meta program graph is: " + json.dumps(self.meta_program_graph)
        system_prompt += "The methods that have been executed in the previous steps are: " + json.dumps(self.executed_methods)
        #self.meta_program_graph["ADMA_list_directory_contents&output_list"]

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
    

                                


class final_output_typer:
    def __init__(self,meta_program_graph):
        self.meta_program_graph = meta_program_graph
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.system_prompt = "You are a output typer. The user will tell you what they want to do. Given the following meta program graph which contains the information of each variable, you need to output the type of the output."
        self.system_prompt += "The type should be one of the following: string, map,  url, file, data,object."
        self.system_prompt += "In meta program graph, if you see local_file_path contains a file path and you are asked to draw a map, you should output the type as map."
        self.system_prompt += "In meta program graph, if you see local_file_path contains some path, you should output the type as file."
        self.system_prompt += "In meta program graph, if you see local_file_path contains a file path of the realm5 data and asked to plot the data, you should output the type as data."
        self.system_prompt += "In meta program graph, if you see local_file_path contains a file path of the soil data, you should output the type as data."
        self.system_prompt += "In meta program graph, if you see a ADMA_url contains a url, you should output the type as url."
        self.system_prompt += "In meta program graph, if you see a meta data, you should output the type as object."

    def output_type(self, user_instruction):
        system_prompt=self.system_prompt + "Current meta program graph is: " + json.dumps(self.meta_program_graph)


        response = self.client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system_prompt},
                      {"role": "user", "content": user_instruction}],
            response_format= output_type,
            temperature=temperature,
        )
        return json.loads(response.choices[0].message.content)
    

class meta_program_graph_initializer:
    def __init__(self,meta_program_graph):
        self.meta_program_graph = meta_program_graph
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.system_prompt = "Given the user's instruction, you need to initialize the variables in meta program graph."
        self.system_prompt += "Note: you can only initialize some of these variables: ADMA_search_string,ADMA_menu_name, ADMA_API_file_path, Date_string, Field_ID, Field_name, Realm5_variable_name_list. You do not need to initialize all of above variables, only those you feel necessary."
        self.system_prompt += "You can initialize the variables to DEFAULT, or to any value based on the user's instruction. If you are not sure what value to set, just set it to DEFAULT."
        self.system_prompt += "Only initialize the variables purely based on the user's instruction, and do not fabricate information."
        self.system_prompt += "For Realm5_variable_name_list, you need to initialize it as a list of realm5 variable names, which introduced in the description of Realm5_variable_name_list in the meta program graph."
        self.system_prompt += "Current meta program graph is: " + json.dumps(self.meta_program_graph)

        


    def initialize_meta_program_graph(self, user_instruction):


        response = self.client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": self.system_prompt},
                      {"role": "user", "content": user_instruction}],
            response_format= initializer_output,
            temperature=temperature,
        )
        return json.loads(response.choices[0].message.content)
    



class ADMA_recommender:
    def __init__(self):

        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.system_prompt = "Given the user's instruction and a json string of list of meta data, you need to recommend top 1 meta data that best match the user's instruction."
        self.system_prompt += " Note: only output the best meta data json string, starting with { and ending with }, with no other word or information."


    def recommend(self, user_instruction, meta_data_list):
        meta_data_list_string = json.dumps(meta_data_list)
        system_prompt = self.system_prompt + "The meta data list is: " + meta_data_list_string


        response = self.client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system_prompt},
                      {"role": "user", "content": user_instruction}],
            temperature=temperature,
        )
        return json.loads(response.choices[0].message.content)    


# return a string
class final_output_formatter:
    def __init__(self,meta_program_graph):
        self.meta_program_graph = meta_program_graph
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.system_prompt = "You are a output formatter. The user will tell you what they want to do. Given the following meta program graph which contains the information of each variable, you need to output the final answer or result, as closed as possible to user's instruction."
        self.system_prompt += "Your output should be 100 percent based on the information extracted from current meta program graph, do not fabricate any information!!"

    def format_output(self, user_instruction,output_type):
        system_prompt=self.system_prompt + "Current meta program graph is: " + json.dumps(self.meta_program_graph)


        if output_type == "string":
            response = self.client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_instruction}],
                response_format= {"type": "text"},
                temperature=temperature,
            )
            return response.choices[0].message.content
        elif output_type == "list":
            system_prompt += "Return a formatted json list with no extra word."

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_instruction}],
                temperature=temperature,
            )
            #(response.choices[0].message.content)
            #print(self.meta_program_graph["ADMA_push_to_meta_data_list&output_list"])

            return response.choices[0].message.content
        elif output_type == "object":
            system_prompt += "Return a formatted json string with no extra word."
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_instruction}],
                temperature=temperature,
            )
            print(response.choices[0].message.content)
            
            return response.choices[0].message.content
        elif output_type == "url":
            system_prompt += "Return a url that can be opened in a web browser. Note: only return the url starting with http or https, with no other word or information."
            response = self.client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_instruction}],
                response_format= {"type": "text"},
                temperature=temperature,
            )
            return response.choices[0].message.content
        elif output_type == "map":
            system_prompt += "Return the file path of the boundary file, in the format of tmp/boundary_xxxx.json. Note: only return the file path, with no other word or information."
            response = self.client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_instruction}],
                response_format= {"type": "text"},
                temperature=temperature,
            )
            return response.choices[0].message.content
        elif output_type == "file":
            system_prompt += "Return the file path of the json file, in the format of tmp/file.suffix. Note: only return the file path, with no other word or information."
            response = self.client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_instruction}],
                response_format= {"type": "text"},
                temperature=temperature,
            )
            return response.choices[0].message.content
        elif output_type == "data":
            system_prompt += "Return the file path of the json file to be plotted. Note: only return the file path, with no other word or information."
            response = self.client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_instruction}],
                response_format= {"type": "text"},
                temperature=temperature,
            )
            return response.choices[0].message.content
        else:
            return "I don't know how to complete this task."
        #return response.choices[0].message.parsed


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


def get_answer(prompt,meta_program_graph,program_controller,output_formatter,output_typer,initializer,adma_recommender,max_iter=10):
    initialized_variables = initializer.initialize_meta_program_graph(prompt)
    print(initialized_variables)


    while max_iter > 0:
        max_iter -= 1
        next_task = program_controller.get_next_task(prompt)
        print(next_task)
        # format next_task["args"] to dict
        args_dict = {}
        for arg in next_task["args"]:
            args_dict[arg["name"]] = arg["value"]
        # process different methods
        if next_task["method"] == "None":
            break
        
        elif next_task["method"] == "ADMA_list_directory":
            # this should be changed to use an agent to set the value based on user's instruction
            if "ADMA_API_file_path" in args_dict and not args_dict["ADMA_API_file_path"] == "DEFAULT":
                dir_path = args_dict["ADMA_API_file_path"]
                meta_program_graph["ADMA_API_file_path"]["value"] = dir_path
                meta_program_graph["ADMA_API_file_path"]["description"] += f"ADMA_API_file_path is a path of the directory on the ADMA system. Current value set by controller."
            else:
                dir_path = meta_program_graph["ADMA_API_file_path"]["value"]
            # update the value of the output list
            meta_program_graph["ADMA_API_file_path_list"]["value"] = ADMA_list_dir(dir_path)

            # update the description of the output list
            meta_program_graph["ADMA_API_file_path_list"]["description"] = meta_program_graph["ADMA_API_file_path"]["description"]+"\n"
            meta_program_graph["ADMA_API_file_path_list"]["description"] += f"ADMA_API_file_path_list is a list of paths under the directory {dir_path} in the ADMA system."

        elif next_task["method"] == "ADMA_get_meta_data":
            # this should be changed to use an agent to set the value based on user's instruction

            if "ADMA_API_file_path" in args_dict and not args_dict["ADMA_API_file_path"] == "DEFAULT":
                path = args_dict["ADMA_API_file_path"] 
                meta_program_graph["ADMA_API_file_path"]["value"] = path
                meta_program_graph["ADMA_API_file_path"]["description"] = f"ADMA_API_file_path is the path of the file or directory on the ADMA system. Current value set by controller."
            else:
                path = meta_program_graph["ADMA_API_file_path"]["value"]
            # update the value of the meta data
            print(f"ADMA_API_file_path: {path}")
            meta_program_graph["ADMA_meta_data"]["value"] = ADMA_get_meta_data(path)
            # update the description of the meta data
            meta_program_graph["ADMA_meta_data"]["description"] = meta_program_graph["ADMA_API_file_path"]["description"]+"\n"
            meta_program_graph["ADMA_meta_data"]["description"] += f"ADMA_meta_data is the meta data of the file or directory {path} in the ADMA system."


        elif next_task["method"] == "ADMA_API_file_path_list_iterator":
            # this should be changed to use an agent to set the value based on user's instruction


            if "ADMA_API_file_path_list_index" in args_dict and not args_dict["ADMA_API_file_path_list_index"] == "DEFAULT":
                index = args_dict["ADMA_API_file_path_list_index"]
                meta_program_graph["ADMA_API_file_path_list_index"]["value"] = index
                meta_program_graph["ADMA_API_file_path_list_index"]["description"] = f"ADMA_API_file_path_list_index is the index for the ADMA_API_file_path_list, and current value set by controller."
            else:
                index = meta_program_graph["ADMA_API_file_path_list_index"]["value"]

            output_list = meta_program_graph["ADMA_API_file_path_list"]["value"]

            

            if index < len(output_list):
                # update the value of the path
                meta_program_graph["ADMA_API_file_path"]["value"] = output_list[index]
                meta_program_graph["ADMA_API_file_path_list_index"]["value"] = index + 1
                #print(meta_program_graph["ADMA_API_file_path_list_index"]["value"])

                # update the description of the path
                meta_program_graph["ADMA_API_file_path"]["description"] = meta_program_graph["ADMA_API_file_path_list"]["description"]+"\n"
                meta_program_graph["ADMA_API_file_path"]["description"] += f"ADMA_API_file_path is path of the file or directory at the index {index} of ADMA_API_file_path_list."

       
        elif next_task["method"] == "ADMA_push_to_meta_data_list":
            
            meta_data = meta_program_graph["ADMA_meta_data"]["value"]
            #push the meta data to the list
            #meta_program_graph["ADMA_push_to_meta_data_list&output_list"]["value"].append(meta_data)
            # append a deep copy of the meta data
            meta_program_graph["ADMA_meta_data_list"]["value"].append(copy.deepcopy(meta_data))
            meta_program_graph["ADMA_meta_data_list"]["description"] = meta_program_graph["ADMA_meta_data"]["description"]+"\n"
            meta_program_graph["ADMA_meta_data_list"]["description"] += f"ADMA_meta_data_list is a list of meta data of the file or folder on the ADMA server."

        elif next_task["method"] == "ADMA_menu_option":
            # this should be changed to use an agent to set the value based on user's instruction

            if "ADMA_menu_name" in args_dict and not args_dict["ADMA_menu_name"] == "DEFAULT":
                menu_name = args_dict["ADMA_menu_name"]
                meta_program_graph["ADMA_menu_name"]["value"] = menu_name
                meta_program_graph["ADMA_menu_name"]["description"] = f"ADMA_menu_name is the name of the menu on the ADMA server, and current value set by the controller."
            else:
                menu_name = meta_program_graph["ADMA_menu_name"]["value"]

            if "ADMA_API_file_path" in args_dict and not args_dict["ADMA_API_file_path"] == "DEFAULT":
                path = args_dict["ADMA_API_file_path"]
                meta_program_graph["ADMA_API_file_path"]["value"] = path
                meta_program_graph["ADMA_API_file_path"]["description"] = f"ADMA_API_file_path is the path of the file or directory on the ADMA server, and current value set by controller."
            else:
                path = meta_program_graph["ADMA_API_file_path"]["value"]

            meta_program_graph["ADMA_url"]["value"] = ADMA_menu_option(menu_name,path)
            print(meta_program_graph["ADMA_url"]["value"])
            meta_program_graph["ADMA_url"]["description"] = meta_program_graph["ADMA_menu_name"]["description"]+"\n"
            meta_program_graph["ADMA_url"]["description"] += meta_program_graph["ADMA_API_file_path"]["description"]+"\n"
            meta_program_graph["ADMA_url"]["description"] += f"ADMA_url is a url on the ADMA server."
        
        elif next_task["method"] == "JD_ENREEC_boundary_in_field":
            # this should be changed to use an agent to set the value based on user's instruction
            if "JD_ENREEC_field_id" in args_dict and not args_dict["JD_ENREEC_field_id"] == "DEFAULT":
                field_id = args_dict["JD_ENREEC_field_id"]
                meta_program_graph["JD_ENREEC_field_id"]["value"] = field_id
                meta_program_graph["JD_ENREEC_field_id"]["description"] = f"JD_ENREEC_field_id is the id of the field in ENREEC, and current value set by controller."
            else:
                field_id = meta_program_graph["JD_ENREEC_field_id"]["value"]
            
            meta_program_graph["local_file_path"]["value"] = json.loads(query_ENREEC_boundary_in_field(field_id))["path"]

            meta_program_graph["local_file_path"]["description"] = meta_program_graph["JD_ENREEC_field_id"]["description"]+"\n"
            meta_program_graph["local_file_path"]["description"] += f"local_file_path is the boundary of the field {field_id} in ENREEC."
        
        elif next_task["method"] == "JD_ENREEC_fields":
            fields_file_path = query_ENREEC_fields_file()
            meta_program_graph["local_file_path"]["value"] = fields_file_path
            meta_program_graph["local_file_path"]["description"] = f"local_file_path is the json file path containing all the fields in ENREEC from John Deere."

        elif next_task["method"] == "JD_ENREEC_field_id_from_name":
            # this should be changed to use an agent to set the value based on user's instruction
            if "JD_ENREEC_field_name" in args_dict and not args_dict["JD_ENREEC_field_name"] == "DEFAULT":
                field_name = args_dict["JD_ENREEC_field_name"]
                meta_program_graph["JD_ENREEC_field_name"]["value"] = field_name
                meta_program_graph["JD_ENREEC_field_name"]["description"] = f"JD_ENREEC_field_name is the name of the field in ENREEC from John Deere, and current value set by controller."
            else:
                field_name = meta_program_graph["JD_ENREEC_field_name"]["value"]
                
            meta_program_graph["JD_ENREEC_field_id"]["value"] = field_id_from_name(field_name)
            meta_program_graph["JD_ENREEC_field_id"]["description"] = meta_program_graph["JD_ENREEC_field_name"]["description"]+"\n"
            meta_program_graph["JD_ENREEC_field_id"]["description"] += f"JD_ENREEC_field_id is the id of the field {field_name} in ENREEC from John Deere."

            
        elif next_task["method"] == "Realm5_generate_file_url":
            # this should be changed to use an agent to set the value based on user's instruction
            if "Realm5_date_str" in args_dict and not args_dict["Realm5_date_str"] == "DEFAULT":
                date_str = args_dict["Realm5_date_str"]
                meta_program_graph["Realm5_date_str"]["value"] = date_str
                meta_program_graph["Realm5_date_str"]["description"] = f"Realm5_date_str is the date string of the file to be generated in Realm5, and current value set by controller."
            else:
                date_str = meta_program_graph["Realm5_date_str"]["value"]

            meta_program_graph["ADMA_API_file_path"]["value"] = Realm5_generate_file_url(date_str)
            
            print(meta_program_graph["ADMA_API_file_path"]["value"])
            meta_program_graph["ADMA_API_file_path"]["description"] = meta_program_graph["Realm5_date_str"]["description"]+"\n"
            meta_program_graph["ADMA_API_file_path"]["description"] += f"ADMA_API_file_path is the url of the Reaml5 file on ADMA for {date_str} to be downloaded."

        elif next_task["method"] == "ADMA_download_file":
            # this should be changed to use an agent to set the value based on user's instruction
            if "ADMA_API_file_path" in args_dict and not args_dict["ADMA_API_file_path"] == "DEFAULT":
                file_url = args_dict["ADMA_API_file_path"]
                meta_program_graph["ADMA_API_file_path"]["value"] = file_url
                meta_program_graph["ADMA_API_file_path"]["description"] = f"ADMA_API_file_path is the url of the file to be downloaded on ADMA, and current value set by controller."
            else:
                file_url = meta_program_graph["ADMA_API_file_path"]["value"]
            
            meta_program_graph["local_file_path"]["value"] = ADMA_download_file(file_url)
            print(meta_program_graph["local_file_path"]["value"])
            meta_program_graph["local_file_path"]["description"] = meta_program_graph["ADMA_API_file_path"]["description"]+"\n"
            meta_program_graph["local_file_path"]["description"] += f"local_file_path is the downloaded local file path of {file_url} from ADMA."


        elif next_task["method"] == "Realm5_format_data_for_plot":
            # this should be changed to use an agent to set the value based on user's instruction

            if "Realm5_variable_name_list" in args_dict and not args_dict["Realm5_variable_name_list"] == "DEFAULT":
                variable_names = args_dict["Realm5_variable_name_list"]
                variable_names = json.loads(variable_names.replace("'",'"'))
                meta_program_graph["Realm5_variable_name_list"]["value"] = variable_names
                meta_program_graph["Realm5_variable_name_list"]["description"] = f"Realm5_variable_name_list is a list of variable names, which must be from [ 'wind_direction','wind_speed','temperature', 'humidity','pressure']."
            else:
                variable_names = meta_program_graph["Realm5_variable_name_list"]["value"]
            
            old_path = meta_program_graph["local_file_path"]["value"]
            meta_program_graph["local_file_path"]["value"] = Realm5_format_data_for_plot(meta_program_graph["local_file_path"]["value"],variable_names)
            if not meta_program_graph["local_file_path"]["value"] == old_path:

                print(meta_program_graph["local_file_path"]["value"])
                meta_program_graph["local_file_path"]["description"] = meta_program_graph["local_file_path"]["description"]+"\n"
                meta_program_graph["local_file_path"]["description"] += meta_program_graph["Realm5_variable_name_list"]["description"]+"\n"
                meta_program_graph["local_file_path"]["description"] += f"local_file_path is the file path of the formatted Realm5 data for plot."

        elif next_task["method"] == "ADMA_search":
            # this should be changed to use an agent to set the value based on user's instruction
            if "ADMA_search_string" in args_dict and not args_dict["ADMA_search_string"] == "DEFAULT":
                search_string = args_dict["ADMA_search_string"]
                meta_program_graph["ADMA_search_string"]["value"] = search_string
                meta_program_graph["ADMA_search_string"]["description"] = f"ADMA_search_string is the search string of the search on ADMA, and current value set by controller."
            else:
                search_string = meta_program_graph["ADMA_search_string"]["value"]
            
            if "ADMA_API_file_path" in args_dict and not args_dict["ADMA_API_file_path"] == "DEFAULT":
                path = args_dict["ADMA_API_file_path"]
                meta_program_graph["ADMA_API_file_path"]["value"] = path
                meta_program_graph["ADMA_API_file_path"]["description"] = f"ADMA_API_file_path is the path of the directory on the ADMA system, and current value set by controller."
            else:
                path = meta_program_graph["ADMA_API_file_path"]["value"]
            
            meta_program_graph["ADMA_meta_data_list"]["value"] = ADMA_search(path,search_string)
            print(meta_program_graph["ADMA_meta_data_list"]["value"])
            meta_program_graph["ADMA_meta_data_list"]["description"] = meta_program_graph["ADMA_search_string"]["description"]+"\n"
            meta_program_graph["ADMA_meta_data_list"]["description"] += f"ADMA_meta_data_list is a list of meta data of the file or folder on the ADMA system under the directory {path}."

       
        elif next_task["method"] == "ADMA_recommender":
            recommended_meta_data = adma_recommender.recommend(prompt,meta_program_graph["ADMA_meta_data_list"]["value"])
            meta_program_graph["ADMA_meta_data"]["value"] = recommended_meta_data
            meta_program_graph["ADMA_meta_data"]["description"] = meta_program_graph["ADMA_meta_data_list"]["description"]+"\n"
            meta_program_graph["ADMA_meta_data"]["description"] += f"ADMA_meta_data is the meta data of the file or folder on the ADMA system."

        elif next_task["method"] == "ADMA_url_extractor":
            
            meta_program_graph["ADMA_url"]["value"] = ADMA_url_extractor(meta_program_graph["ADMA_meta_data"]["value"])
            meta_program_graph["ADMA_url"]["description"] = meta_program_graph["ADMA_meta_data"]["description"]+"\n"
            meta_program_graph["ADMA_url"]["description"] += f"ADMA_url is the url of the file or directory on ADMA."
                
                
                
    final_output_type = output_typer.output_type(prompt)
    print(final_output_type)
    output = output_formatter.format_output(prompt,final_output_type["output_type"])
    print(f"output: {output}")

    return {"type": final_output_type["output_type"],"output": output}

def ai_reply(response, if_history=False):
    if response["type"] == "string":
        if if_history:
            st.chat_message("assistant", avatar="🤖").write(response["output"])
        else:
            st.chat_message("assistant", avatar="🤖").write(stream_data(response["output"]))
    elif response["type"] == "list":
        if if_history:
            st.chat_message("assistant", avatar="🤖").write(response["output"])
        else:
            st.chat_message("assistant", avatar="🤖").write(stream_data(response["output"]))
    elif response["type"] == "object":
        if if_history:
            #with st.chat_message("assistant", avatar="🤖"):
            #    st.json(json.loads(response["output"]))
            st.chat_message("assistant", avatar="🤖").write(response["output"])
        else:
            #with st.chat_message("assistant", avatar="🤖"):
            #    st.json(json.loads(response["output"]))
            st.chat_message("assistant", avatar="🤖").write(stream_data(response["output"]))
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
    elif response["type"] == "file":
        with open(response["output"]) as f:
            output = f.read()
        
        st.json(json.loads(output),expanded=False)
    elif response["type"] == "data":
        if not os.path.exists(response["output"]):
            st.chat_message("assistant", avatar="🤖").write("No data found for the field")
            return
        with open(response["output"]) as f:        
            data = json.load(f)
        df = pd.DataFrame(data)
    
        st.line_chart(df,width=1200,height=600)



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
    
    with open("meta_program_graph_new.json") as f:
        meta_program_graph = json.load(f)

    executed_methods = []
    
    
    if 'program_controller' not in st.session_state:
        st.session_state.program_controller = controller(meta_program_graph,executed_methods)
    if 'output_formatter' not in st.session_state:
        st.session_state.output_formatter = final_output_formatter(meta_program_graph)
    if 'output_typer' not in st.session_state:
        st.session_state.output_typer = final_output_typer(meta_program_graph)
    if 'initializer' not in st.session_state:
        st.session_state.initializer = meta_program_graph_initializer(meta_program_graph)
    if 'adma_recommender' not in st.session_state:
        st.session_state.adma_recommender = ADMA_recommender()

 
    program_controller = st.session_state.program_controller
    output_formatter = st.session_state.output_formatter
    output_typer = st.session_state.output_typer
    initializer = st.session_state.initializer
    adma_recommender = st.session_state.adma_recommender

    program_controller.executed_methods = []
    program_controller.meta_program_graph = meta_program_graph
    output_formatter.meta_program_graph = meta_program_graph
    output_typer.meta_program_graph = meta_program_graph
    initializer.meta_program_graph = meta_program_graph



    #upload file
    #files = st.sidebar.file_uploader("Upload Your File",accept_multiple_files=True)
    #for file in files:
    #    st.write(file.name)

    # Initialize the session state for chat history if it does not exist
    if 'chat_history' not in st.session_state:
      st.session_state['chat_history'] = []

    # Display chat history
    for message in st.session_state['chat_history']:
      if message['role'] == "user":
          # avatar is a emoji
          st.chat_message("user",avatar="👨‍🎓").write(message['content'])
      elif message['role'] == "assistant":
          ai_reply(message['content'],if_history=True)
          #st.chat_message("assistant", avatar="🤖").write(message['content'])


    if prompt := st.chat_input("Ask Me Anything About Your AgData"):
      # Update chat history with user message
      user_message = {"role": "user",  "content": f"{prompt}"}
      st.session_state['chat_history'].append(user_message)
      st.chat_message("user",avatar="👨‍🎓").write(prompt)

      # response is a json object with the following format: {"type": "the type of the output", "output": "the json string"}
      response = get_answer(prompt,meta_program_graph,program_controller,output_formatter,output_typer,initializer,adma_recommender,max_iter=20)

      ai_reply(response)

      
      bot_message = {"role": "assistant","content": response}
      st.session_state['chat_history'].append(bot_message)



if __name__ == '__main__':
    main()

