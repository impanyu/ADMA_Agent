from dotenv import load_dotenv
import streamlit as st
from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.chains.question_answering import load_qa_chain
from langchain_community.llms import OpenAI
from langchain_community.callbacks import get_openai_callback
import time

from langchain_experimental.autonomous_agents import AutoGPT
from langchain_openai import ChatOpenAI
from langchain_community.docstore import InMemoryDocstore
import faiss
from langchain_community.chat_message_histories import FileChatMessageHistory
from langchain.agents import Tool

from langchain_community.tools.file_management.read import ReadFileTool
from langchain_community.tools.file_management.write import WriteFileTool
from langchain_community.utilities import SerpAPIWrapper

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain.tools.retriever import create_retriever_tool

from langchain_community.agent_toolkits import NLAToolkit
from langchain_community.utilities import Requests
from langchain.agents import AgentType, initialize_agent

import langchain
from langchain.prompts import StringPromptTemplate
load_dotenv(".venv")
from JD_Tools import *
from utils import *
import folium
from streamlit_folium import st_folium, folium_static

from ADMA_Tools import *

from streamlit_echarts import st_echarts
import uuid


# Set up a prompt template
class CustomPromptTemplate(StringPromptTemplate):
    # The template to use
    template: str
    tools: list
    ############## NEW ######################
    # The list of tools available

    def format(self, **kwargs) -> str:
        # Get the intermediate steps (AgentAction, Observation tuples)
        # Format them in a particular way
        intermediate_steps = kwargs.pop("intermediate_steps")
        thoughts = ""
        for action, observation in intermediate_steps:
            thoughts += action.log
            thoughts += f"\nObservation: {observation}\nThought: "
        # Set the agent_scratchpad variable to that value
        kwargs["agent_scratchpad"] = thoughts
        ############## NEW ######################
        tools = self.tools
        # Create a tools variable from the list of tools provided
        kwargs["tools"] = "\n".join(
            [f"{tool.name}: {tool.description}" for tool in tools]
        )
        # Create a list of tool names for the tools provided
        kwargs["tool_names"] = ", ".join([tool.name for tool in tools])
        return self.template.format(**kwargs)



def define_agent():
    llm=ChatOpenAI(temperature=0,model="gpt-4o-mini")
    search = SerpAPIWrapper()


    # Define your embedding model
    embeddings_model = OpenAIEmbeddings()
    # Initialize the vectorstore as empty

    stored_docs = ["Yu Pan is a Research Assistant Professor at UNL. He is responsible for the development of the ADMA project.",
                   "Agriculture Data Management and Analytics (ADMA) is a comprehensive data management platform developed for experts within and outside IANR. It is a state-of-the-art solution designed to address the multifaceted challenges faced by modern agriculture. As the world grapples with population growth, climate change, and diminishing natural resources, the need for data-driven innovation in agroecosystems has never been more critical. ADMA is a comprehensive platform that harnesses the power of advanced technologies, such as IoT, high-resolution sensors, and cloud computing, to facilitate data collection, integration, and analysis across various agricultural disciplines. By incorporating the FAIR principles (Findable, Accessible, Interoperable, and Reusable), ADMA aims to break down data silos and promote collaboration among researchers, policymakers, and industry stakeholders. "
                   "ENREEC has organization id = 4193081 in John Deere API",
                 ]
      

    embedding_size = 1536
    index = faiss.IndexFlatL2(embedding_size)
    vectorstore = FAISS(embeddings_model.embed_query, index, InMemoryDocstore({}), {})
    vectorstore.add_texts(stored_docs)

    vectorstore_tool = create_retriever_tool(
    vectorstore.as_retriever(),
    "ADMA_vectorstore",
    "When the user ask for anything, you must use this tool!",
    )
    
   
    #requests = Requests(headers={"Authorization": f"Bearer {JD_api_key}", "User-Agent": "ADMA", "Accept": "application/vnd.deere.axiom.v3+json","Connection": "keep-alive","Accept-Encoding": "gzip, deflate, br"})
    #JD_toolkit = NLAToolkit.from_llm_and_url(
    #llm,
    #"https://spoonacular.com/application/frontend/downloads/spoonacular-openapi-3.json",
    #"https://www.klarna.com/us/shopping/public/openai/v0/api-docs/",
    #"http://unladma.hopto.org/static/JD_openapi.json",
    #requests=requests,
    #)


    tools=[]
    #for tool in JD_toolkit.get_tools(): #.nla_tools
    #    tool.name = tool.name.replace(".","_") 
    #    tools.append(tool)
        #tools.append(Tool(name=tool.name.replace(".","_"),func=tool.run,description=tool.description))
    JD_tools = [
        query_ENREEC,
        query_ENREEC_fields,
        query_ENREEC_farms_in_field,
        query_crop_types,
        query_ENREEC_operation_in_field,
        query_ENREEC_boundary_in_field,
        #file_existence_check,
    ]
    tools.extend(JD_tools)

    ADMA_tools = [
        ADMA_get_meta_data,
        ADMA_list_directory_contents,
        ADMA_get_running_instance,
        ADMA_check_file,
        ADMA_plot_option,
    ]
    tools.extend(ADMA_tools)
    tools.extend([
          Tool(
              name="search",
              func=search.run,
              description="useful for when you need to answer questions about current events. You should ask targeted questions",
          ),
          WriteFileTool(),
          ReadFileTool(),
          vectorstore_tool
      ])
   
    
   
    
    for tool in tools:
        print(f"tool name: {tool.name}")
        print(f"tool type: {type(tool)}")
    #print(tools[4].function.name)

    #agent = AutoGPT.from_llm_and_tools(
    #    ai_name="Tom",
    #    ai_role="Assistant",
    #    tools=tools,
    #    llm=ChatOpenAI(temperature=0),
    #    memory=vectorstore.as_retriever(),
    #    chat_history_memory=FileChatMessageHistory("chat_history.txt")
    #)
    prompt = ChatPromptTemplate.from_messages(
      [
          (
              "system",
              "You are a helpful assistant. \
               To answer each question, you should always call a tool. Never fabricate the answer! \
               Never fabricate unreal paths or files. Always call tools to generate real path.\
               For any query, make sure to use vectorstore_tool.\
               Make sure to use the tavily_search_results_json tool for something you do not know. \
               When the user want to draw a map or boundary of an ENREEC field, make sure to call query_ENREEC_boundary_in_field first. After that you only need to reply the json format returned from the tool: query_ENREEC_boundary_in_field, no more any extra charactors!\
               For ADMA_plot_option, you should call the tool to get the json string, then output the json string, do not add any extra charactors!\
               Use John_Deere_APIs for any questions about ENREEC.\
               Use ADMA_APIs for any questions about ADMA.\
               You might know the answer without running any tool, but you should always run the tool to get the answer. This is extremely important!!\
               If you get a json string, just output the json string, do not add any extra charactors! \
               When asked to plot some data, you can not fabricate the plot, try to call some tools to do that!!\
               "
          ),
          #("placeholder", "{chat_history}"),
          ("human", "{input}"),
          ("placeholder", "{agent_scratchpad}"),
      ]
    )

    tool_names = ", ".join([tool.name for tool in tools])

    # Set up the base template
    template = """Answer the following questions as best you can, but speaking as a pirate might speak. You have access to the following tools:

    {tools}
    Use the following format:
    Question: the input question you must answer
    Thought: you should always think about what to do
    Action: the action to take, should be one of [{tool_names}]
    Action Input: the input to the action
    Observation: the result of the action
    ... (this Thought/Action/Action Input/Observation can repeat N times)
    Thought: I now know the final answer
    Final Answer: the final answer to the original input question

    Begin! Remember to speak as a pirate when giving your final answer. Use lots of "Arg"s

    Question: {input}
    {agent_scratchpad}"""

    #prompt = CustomPromptTemplate(
    #    template=template,
    #    tools=tools,
        # This omits the `agent_scratchpad`, `tools`, and `tool_names` variables because those are generated dynamically
        # This includes the `intermediate_steps` variable because that is needed
    #    input_variables=["input", "intermediate_steps","agent_scratchpad","chat_history"],
    #)

    # Construct the Tools agent
    agent = create_tool_calling_agent(llm, tools, prompt)
    #Create an agent executor by passing in the agent and tools
    agent_executor = AgentExecutor.from_agent_and_tools(agent=agent, tools=tools,verbose=False,max_iterations=3)


    return agent_executor

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
    

def ai_reply(response_output, if_history=False):
    print(f"response output: {response_output}")
    json_output = response_output
        
    #json_output = find_largest_enclosed_json(response_output)
    print(f"json_output: {json_output}")
    if json_output == None:
        json_output = None
    else:
        json_output = is_json(json_output)
    print(f"json_output: {json_output}")
    if  json_output  and "type" in json_output and json_output["type"]=="boundary":
        
        if not os.path.exists(json_output["path"]):
            if if_history:
                st.chat_message("assistant", avatar="🤖").write("No boundary found for the field")
            else:
                st.chat_message("assistant", avatar="🤖").write(stream_data("No boundary found for the field"))

            return
        
        with open(json_output["path"]) as f:
            boundary = json.load(f)
            #print(boundary)
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
            with  st.chat_message("assistant", avatar="🤖"):
                folium_static(m,height=400,width=600)

    elif json_output and  "type" in json_output and json_output["type"]=="file":
        print("here!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print(response_output)
        print(is_json(response_output))
        with open(json_output["path"]) as f:
            data = f.read()
            if if_history:
                st.chat_message("assistant", avatar="🤖").write(data)
            else:
                st.chat_message("assistant", avatar="🤖").write(stream_data(data))

    elif  json_output  and "series" in json_output:
        # Generate a unique key for each widget
        unique_key = str(uuid.uuid4())  # This generates a unique identifier

        # Pass this unique key to the st_echarts function
        
  
        with st.chat_message("assistant", avatar="🤖"):
            st_echarts(options=json_output, height=400, width=500, key=unique_key)

    else:
        
        if if_history:
            st.chat_message("assistant", avatar="🤖").write(response_output)
        else:
            st.chat_message("assistant", avatar="🤖").write(stream_data(response_output))
     
def main():
 
    
    #set the page title and icon
    #the icon is a green leaf
    st.set_page_config(page_title="ADMA Copilot", page_icon="🍃")
    st.header("ADMA Copilot",divider="green")

    agent = define_agent()

    st.sidebar.title("Control Panel")

    
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

      # Generate a response and simulate some processing delay or logic
      #response = "I am processing your request... Generators are a type of iterable, like lists or tuples, but they do not store their contents in memory; instead, they generate the items on the fly and only hold one item at a time. This makes them very memory efficient when dealing with large datasets or potentially infinite streams."
      response = agent.invoke({"input":prompt,"chat_history":st.session_state['chat_history']})
      #response = agent.invoke({"input":prompt})
      #print(response)
      #draw map on the screen
      #print(response["output"])
      #print(is_json(response["output"]))
      ai_reply(response["output"])

      
      bot_message = {"role": "assistant","content": response["output"]}
      st.session_state['chat_history'].append(bot_message)




    
if __name__ == '__main__':
    langchain.debug = True
 
    main()

