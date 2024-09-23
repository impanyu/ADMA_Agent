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



class controller_output(BaseModel):
    method: str = Field(description="The name of the method to call.")
    args: dict = Field(description="The values of the arguments of the method.")

class controller:
    def __init__(self,meta_program_graph):
        self.meta_program_graph = meta_program_graph
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.system_prompt = "You are a program controller. The user will tell you what they want to do. Given the following meta program graph which contains the information of each method and each variable, you need to decide the next method to call."
        self.system_prompt += "The meta program graph is: " + json.dumps(self.meta_program_graph)
        self.system_prompt += 'If you consider there\'s no more methods to call, you should only output a json with the following format: {"method": "None","args": {}}, with no other extra word at all.'
        self.system_prompt += 'Else if you consider there should be a method to call, you need to output a json with the following format: {"method": "the name of the method to call","args": {"arg_name": "arg_value"}}, with no other extra word at all.'
        self.system_prompt += 'The name of the method should match one of the methods in the meta program graph, and the args should match one of the keys in the meta program graph, and also be the element in the "input" field of the method. If you decide to use the values in the meta program graph, you only need to set the values of the arguments as "DEFAULT", otherwise you need to set the values of the arguments as the values you want to use.'
    def get_next_task(self,user_instruction):
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": self.system_prompt},
                      {"role": "user", "content": user_instruction}],
            response_format= controller_output,
            temperature=0.5,
        )
        return response.choices[0].message.parsed
    
class output_format(BaseModel):
    type: str = Field(description="The type of the output, in the following format: boundary, file, list, string")
    output: str = Field(description="The output of the program, which is a json string")

class final_output_formatter:
    def __init__(self,meta_program_graph):
        self.meta_program_graph = meta_program_graph
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.system_prompt = "You are a output formatter. The user will tell you what they want to do. Given the following meta program graph which contains the information of each variable, you need to output the final answer or result, as closed as possible to user's instruction."
        self.system_prompt += "The output field in your output should be consistent with the type you specify. For example, if you specify the type as a list, you need to output a list, if you specify the type as a string, you need to output a string, if you specify the type as a boundary, you need to output a list of tuple of coordinates on the map , etc."
        self.system_prompt += "The meta program graph is: " + json.dumps(self.meta_program_graph)

    def format_output(self, user_instruction):
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": self.system_prompt},
                      {"role": "user", "content": user_instruction}],
            response_format= output_format,
            temperature=0.5,
        )
        return response.choices[0].message.parsed


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


def get_answer(prompt,meta_program_graph,program_controller,output_formatter,max_iter=10):
    while max_iter > 0:
        max_iter -= 1
        next_task = program_controller.get_next_task(prompt)
        print(next_task)
        # process different methods
        if next_task["method"] == "None":
            break
        
        elif next_task["method"] == "ADMA_list_directory_contents":
            if "ADMA_list_directory_contents&dir_path" in next_task["args"] and next_task["args"]["ADMA_list_directory_contents&dir_path"] == "DEFAULT":
                dir_path = next_task["args"]["ADMA_list_directory_contents&dir_path"]
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
            if "ADMA_get_meta_data&path" in next_task["args"] and next_task["args"]["ADMA_get_meta_data&path"] == "DEFAULT":
                path = next_task["args"]["ADMA_get_meta_data&path"] 
                meta_program_graph["ADMA_get_meta_data&path"]["value"] = path
                meta_program_graph["ADMA_get_meta_data&path"]["description"] = f"ADMA_get_meta_data&path is the path of the file or directory on the ADMA system, and set to {path}."
            else:
                path = meta_program_graph["ADMA_get_meta_data&path"]["value"]
            # update the value of the meta data
            meta_program_graph["ADMA_get_meta_data&meta_data"]["value"] = ADMA_get_meta_data(path)
            # update the description of the meta data
            meta_program_graph["ADMA_get_meta_data&meta_data"]["description"] = meta_program_graph["ADMA_get_meta_data&path"]["description"]+"\n"
            meta_program_graph["ADMA_get_meta_data&meta_data"]["description"] += f"ADMA_get_meta_data&meta_data is the meta data of the file or directory {path} in the ADMA system."


        elif next_task["method"] == "subscribe_list_1":

            if "ADMA_list_directory_contents&output_list_current_index" in next_task["args"] and next_task["args"]["ADMA_list_directory_contents&output_list_current_index"] == "DEFAULT":
                index = next_task["args"]["ADMA_list_directory_contents&output_list_current_index"]
                meta_program_graph["ADMA_list_directory_contents&output_list_current_index"]["value"] = index
                meta_program_graph["ADMA_list_directory_contents&output_list_current_index"]["description"] = f"ADMA_list_directory_contents&output_list_current_index is the index of the file or directory in the ADMA system, and set to {index}."
            else:
                index = meta_program_graph["ADMA_list_directory_contents&output_list_current_index"]["value"]

            output_list = meta_program_graph["ADMA_list_directory_contents&output_list"]["value"]

            if index < len(output_list):
                # update the value of the path
                meta_program_graph["ADMA_get_meta_data&path"]["value"] = output_list[index]
                meta_program_graph["ADMA_list_directory_contents&output_list_current_index"]["value"] = index + 1
                # update the description of the path
                meta_program_graph["ADMA_get_meta_data&path"]["description"] = meta_program_graph["ADMA_list_directory_contents&output_list"]["description"]+"\n"
                meta_program_graph["ADMA_get_meta_data&path"]["description"] += f"ADMA_get_meta_data&path is path of the file or directory at the index {index} of ADMA_list_directory_contents&output_list."

        elif next_task["method"] == "subscribe_list_2":

            if "ADMA_list_directory_contents&output_list_current_index" in next_task["args"] and next_task["args"]["ADMA_list_directory_contents&output_list_current_index"] == "DEFAULT":
                index = next_task["args"]["ADMA_list_directory_contents&output_list_current_index"]
                meta_program_graph["ADMA_list_directory_contents&output_list_current_index"]["value"] = index
                meta_program_graph["ADMA_list_directory_contents&output_list_current_index"]["description"] = f"ADMA_list_directory_contents&output_list_current_index is the index of the file or directory in the ADMA system, and set to {index}."
            else:
                index = meta_program_graph["ADMA_list_directory_contents&output_list_current_index"]["value"]
            
            output_list = meta_program_graph["ADMA_list_directory_contents&output_list"]["value"]
            if index < len(output_list):
                # update the value of the path
                meta_program_graph["ADMA_list_directory_contents&dir_path"]["value"] = output_list[index]
                meta_program_graph["ADMA_list_directory_contents&output_list_current_index"]["value"] = index + 1
                # update the description of the path
                meta_program_graph["ADMA_list_directory_contents&dir_path"]["description"] = meta_program_graph["ADMA_list_directory_contents&output_list"]["description"]+"\n"
                meta_program_graph["ADMA_list_directory_contents&dir_path"]["description"] += f"ADMA_list_directory_contents&dir_path is the path of the file or directory at the index {index} of ADMA_list_directory_contents&output_list."
            


    
    output = output_formatter.format_output(prompt)

    return output

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

    #load meta program graph
    with open("meta_program_graph_new.json") as f:
        meta_program_graph = json.load(f)

    program_controller = controller(meta_program_graph)
    output_formatter = final_output_formatter(meta_program_graph)
    



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
      response = get_answer(prompt,meta_program_graph,program_controller,output_formatter,max_iter=10)

      ai_reply(response)

      
      bot_message = {"role": "assistant","content": response}
      st.session_state['chat_history'].append(bot_message)



if __name__ == '__main__':
    main()

