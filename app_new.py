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



class controller:
    def __init__(self,meta_program_graph):
        self.meta_program_graph = meta_program_graph
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.system_prompt = "You are a program controller. The user will tell you what they want to do. Given the following meta program graph which contains the information of each method and each variable, you need to decide if you should call any method and if yes, the method to call."
        self.system_prompt += 'If you find enough information in current meta program graph to answer user\'s question, you should make no method call and you should only output a json with the following format: {"method": "None","args": []}, with no other extra word at all.'
        self.system_prompt += 'Else if you do not find enough information in current meta program graph to answer user\'s question, you need to output a json with the following format: {"method": "the name of the method to call","args": [{"name": "the name of the argument", "value": "the value of the argument"},...]}, with no other extra word at all.'
        self.system_prompt += 'The name of the method should match one of the methods in the meta program graph, and the arg_name should match one of the keys in the meta program graph, and also be the element in the "input" field of the method. If you decide to use the values in the meta program graph, you only need to set the values of the arguments as "DEFAULT", otherwise you need to set the values of the arguments as the values you want to use.'
        self.system_prompt += 'Try your best to extract required information from the meta program graph, and reduce the needs to make method calls. But do not fabricate any information.'
        self.system_prompt += 'How to extract required information from the meta program graph? You can check the description of each variable and the correspondingvalue of each variable. Compare this information with user\'s question, and check if you can find the answer.'

    
    def get_next_task(self,user_instruction):
        system_prompt=self.system_prompt + "Current meta program graph is: " + json.dumps(self.meta_program_graph)
        self.meta_program_graph["ADMA_list_directory_contents&output_list"]

        response = self.client.beta.chat.completions.parse(
            model="gpt-4o-mini",
           
            messages=[{"role": "system", "content": system_prompt},
                      {"role": "user", "content": user_instruction}],
            response_format= controller_output,
            temperature=0.5,
        )
        #print(response.choices[0].message.content)
        return json.loads(response.choices[0].message.content)#response.choices[0].message.parsed
    
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
                                "enum": ["string", "list", "map","number","UI"],
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

class final_output_typer:
    def __init__(self,meta_program_graph):
        self.meta_program_graph = meta_program_graph
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.system_prompt = "You are a output typer. The user will tell you what they want to do. Given the following meta program graph which contains the information of each variable, you need to output the type of the output."
        self.system_prompt += "The type should be one of the following: string, list, map, number, UI."

    def output_type(self, user_instruction):
        system_prompt=self.system_prompt + "Current meta program graph is: " + json.dumps(self.meta_program_graph)


        response = self.client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system_prompt},
                      {"role": "user", "content": user_instruction}],
            response_format= output_type,
            temperature=0.5,
        )
        return json.loads(response.choices[0].message.content)

class final_output_formatter:
    def __init__(self,meta_program_graph):
        self.meta_program_graph = meta_program_graph
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.system_prompt = "You are a output formatter. The user will tell you what they want to do. Given the following meta program graph which contains the information of each variable, you need to output the final answer or result, as closed as possible to user's instruction."
        self.system_prompt += "The meta program graph is: " + json.dumps(self.meta_program_graph)

    def format_output(self, user_instruction,output_type):
        system_prompt=self.system_prompt + "Current meta program graph is: " + json.dumps(self.meta_program_graph)

        if output_type == "string":
            response = self.client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_instruction}],
                response_format= {"type": "text"},
                temperature=0.5,
            )
            return response.choices[0].message.content
        elif output_type == "list":
            response = self.client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_instruction}],
                response_format= list_string_format,
                temperature=0.5,
            )
            return json.dumps(json.loads(response.choices[0].message.content)["items"])
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


def get_answer(prompt,meta_program_graph,program_controller,output_formatter,output_typer,max_iter=10):

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
        
        elif next_task["method"] == "ADMA_list_directory_contents":
            if "ADMA_list_directory_contents&dir_path" in args_dict and not args_dict["ADMA_list_directory_contents&dir_path"] == "DEFAULT":
                dir_path = args_dict["ADMA_list_directory_contents&dir_path"]
                meta_program_graph["ADMA_list_directory_contents&dir_path"]["value"] = dir_path
                meta_program_graph["ADMA_list_directory_contents&dir_path"]["description"] = f"ADMA_list_directory_contents&dir_path is the path of the directory on the ADMA system, and set to {dir_path}."
            else:
                dir_path = meta_program_graph["ADMA_list_directory_contents&dir_path"]["value"]
            # update the value of the output list
            meta_program_graph["ADMA_list_directory_contents&output_list"]["value"] = ADMA_list_directory_contents(dir_path)

            # update the description of the output list
            meta_program_graph["ADMA_list_directory_contents&output_list"]["description"] = meta_program_graph["ADMA_list_directory_contents&dir_path"]["description"]+"\n"
            meta_program_graph["ADMA_list_directory_contents&output_list"]["description"] += f"ADMA_list_directory_contents&output_list is a list of paths under the directory {dir_path} in the ADMA system."

        elif next_task["method"] == "ADMA_get_meta_data":
            if "ADMA_get_meta_data&path" in args_dict and not args_dict["ADMA_get_meta_data&path"] == "DEFAULT":
                path = args_dict["ADMA_get_meta_data&path"] 
                meta_program_graph["ADMA_get_meta_data&path"]["value"] = path
                meta_program_graph["ADMA_get_meta_data&path"]["description"] = f"ADMA_get_meta_data&path is the path of the file or directory on the ADMA system, and set to {path}."
            else:
                path = meta_program_graph["ADMA_get_meta_data&path"]["value"]
            # update the value of the meta data
            meta_program_graph["ADMA_get_meta_data&meta_data"]["value"] = ADMA_get_meta_data(path)
            # update the description of the meta data
            meta_program_graph["ADMA_get_meta_data&meta_data"]["description"] = meta_program_graph["ADMA_get_meta_data&path"]["description"]+"\n"
            meta_program_graph["ADMA_get_meta_data&meta_data"]["description"] += f"ADMA_get_meta_data&meta_data is the meta data of the file or directory {path} in the ADMA system."


        elif next_task["method"] == "iter_list_1":

            if "ADMA_list_directory_contents&output_list_current_index" in args_dict and not args_dict["ADMA_list_directory_contents&output_list_current_index"] == "DEFAULT":
                index = args_dict["ADMA_list_directory_contents&output_list_current_index"]
                meta_program_graph["ADMA_list_directory_contents&output_list_current_index"]["value"] = index
                meta_program_graph["ADMA_list_directory_contents&output_list_current_index"]["description"] = f"ADMA_list_directory_contents&output_list_current_index is the index of the file or directory in the ADMA system, and set to {index}."
            else:
                index = meta_program_graph["ADMA_list_directory_contents&output_list_current_index"]["value"]

            output_list = meta_program_graph["ADMA_list_directory_contents&output_list"]["value"]

            index = index % len(output_list)

            
            # update the value of the path
            meta_program_graph["ADMA_get_meta_data&path"]["value"] = output_list[index]
            meta_program_graph["ADMA_list_directory_contents&output_list_current_index"]["value"] = (index + 1) % len(output_list)
            print(meta_program_graph["ADMA_list_directory_contents&output_list_current_index"]["value"])

            # update the description of the path
            meta_program_graph["ADMA_get_meta_data&path"]["description"] = meta_program_graph["ADMA_list_directory_contents&output_list"]["description"]+"\n"
            meta_program_graph["ADMA_get_meta_data&path"]["description"] += f"ADMA_get_meta_data&path is path of the file or directory at the index {index} of ADMA_list_directory_contents&output_list."

        elif next_task["method"] == "iter_list_2":

            if "ADMA_list_directory_contents&output_list_current_index" in args_dict and not args_dict["ADMA_list_directory_contents&output_list_current_index"] == "DEFAULT":
                index = args_dict["ADMA_list_directory_contents&output_list_current_index"]
                meta_program_graph["ADMA_list_directory_contents&output_list_current_index"]["value"] = index
                meta_program_graph["ADMA_list_directory_contents&output_list_current_index"]["description"] = f"ADMA_list_directory_contents&output_list_current_index is the index of the file or directory in the ADMA system, and set to {index}."
            else:
                index = meta_program_graph["ADMA_list_directory_contents&output_list_current_index"]["value"]
            
            output_list = meta_program_graph["ADMA_list_directory_contents&output_list"]["value"]
            index = index % len(output_list)
            
            # update the value of the path
            meta_program_graph["ADMA_list_directory_contents&dir_path"]["value"] = output_list[index]
            meta_program_graph["ADMA_list_directory_contents&output_list_current_index"]["value"] = (index + 1) % len(output_list)
            # update the description of the path
            meta_program_graph["ADMA_list_directory_contents&dir_path"]["description"] = meta_program_graph["ADMA_list_directory_contents&output_list"]["description"]+"\n"
            meta_program_graph["ADMA_list_directory_contents&dir_path"]["description"] += f"ADMA_list_directory_contents&dir_path is the path of the file or directory at the index {index} of ADMA_list_directory_contents&output_list."
        
        elif next_task["method"] == "ADMA_push_to_meta_data_list":
            
            meta_data = meta_program_graph["ADMA_get_meta_data&meta_data"]["value"]
            #push the meta data to the list
            meta_program_graph["ADMA_push_to_meta_data_list&output_list"]["value"].append(meta_data)
            meta_program_graph["ADMA_push_to_meta_data_list&output_list"]["description"] = meta_program_graph["ADMA_get_meta_data&meta_data"]["description"]+"\n"
            meta_program_graph["ADMA_push_to_meta_data_list&output_list"]["description"] += f"ADMA_push_to_meta_data_list&output_list is a list of meta data of the file or folder on the ADMA server."


    final_output_type = output_typer.output_type(prompt)
    output = output_formatter.format_output(prompt,final_output_type["output_type"])

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
    elif response["type"] == "boundary":
        if if_history:
            st.chat_message("assistant", avatar="🤖").write(response["output"])
        else:
            st.chat_message("assistant", avatar="🤖").write(stream_data(response["output"]))

 



def main():
 
    #set the page title and icon
    #the icon is a green leaf
    st.set_page_config(page_title="ADMA Copilot", page_icon="🍃")
    st.header("ADMA Copilot",divider="green")



    st.sidebar.title("Control Panel")


    # Load meta program graph
    if 'meta_program_graph' not in st.session_state:
        with open("meta_program_graph_new.json") as f:
            st.session_state.meta_program_graph = json.load(f)
    
    if 'program_controller' not in st.session_state:
        st.session_state.program_controller = controller(st.session_state.meta_program_graph)
    if 'output_formatter' not in st.session_state:
        st.session_state.output_formatter = final_output_formatter(st.session_state.meta_program_graph)
    if 'output_typer' not in st.session_state:
        st.session_state.output_typer = final_output_typer(st.session_state.meta_program_graph)

    meta_program_graph = st.session_state.meta_program_graph
    program_controller = st.session_state.program_controller
    output_formatter = st.session_state.output_formatter
    output_typer = st.session_state.output_typer



    # upload file
    files = st.sidebar.file_uploader("Upload Your File",accept_multiple_files=True)
    for file in files:
        st.write(file.name)

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
      response = get_answer(prompt,meta_program_graph,program_controller,output_formatter,output_typer,max_iter=20)

      ai_reply(response)

      
      bot_message = {"role": "assistant","content": response}
      st.session_state['chat_history'].append(bot_message)



if __name__ == '__main__':
    main()

