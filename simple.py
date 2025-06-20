import ollama
import streamlit as st
import time
import os
from datetime import datetime
import json
from dcmcpdpfchat import create_qa_agent
from dcmcpdpfchat import ask_question
from io import StringIO
from PyPDF2 import PdfReader
import logging
from PIL import Image
from streamlit_pdf_viewer import pdf_viewer

# Configure logging
logging.basicConfig(level=logging.INFO)

#####################################
#                                   #
# This app is for those wanting to  #
# use the ollama library            #
#                                   #
#####################################

def response_generator(msg_content):
    lines = msg_content.split('\n')  # Split the content into lines to preserve paragraph breaks.
    for line in lines:
        words = line.split()  # Split the line into words to introduce a delay for each word.
        for word in words:
            yield word + " "
            time.sleep(0.1)
        yield "\n"  # After finishing a line, yield a newline character to preserve paragraph breaks.

def show_msgs():
    for msg in st.session_state.messages:
        if msg["role"] == "assistant":
            # For assistant messages, use the custom avatar
            with st.chat_message("assistant"):
                st.write(msg["content"])
        else:
            # For user messages, display as usual
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

def chat(message, model='llama3.2-vision:latest'): ### CHANGE MODEL ID HERE 
    try:

        PDF_PATH = "Service_Manual_En.pdf"
        qa_agent = create_qa_agent(PDF_PATH)
        result = ask_question(qa_agent, message)

        # response = ask_question(qa_agent,(model=model, messages=[
        #     {
        #         'role': 'user',
        #         'content': message,
        #     }
        # ])
        return result['answer']
    except Exception as e:
        error_message = str(e).lower()
        if "not found" in error_message:
            return f"Model '{model}' not found. Please refer to Doumentation at https://ollama.com/library."
        else:
            return f"An unexpected error occurred with model '{model}': {str(e)}"
        

def format_messages_for_summary(messages):
    # Create a single string from all the chat messages
    return '\n'.join(f"{msg['role']}: {msg['content']}" for msg in messages)

def summary(message, model='llama3'):
    sysmessage = "summarize this conversation in 3 words. No symbols or punctuation:\n\n\n"
    api_message = sysmessage + message
    try:
        response = ollama.chat(model=model, messages=[
            {
                'role': 'user',
                'content': api_message,
            }
        ])
        return response['message']['content']
    except Exception as e:
        error_message = str(e).lower()
        if "not found" in error_message:
            return f"Model '{model}' not found. Please refer to Documentation at https://ollama.com/library."
        else:
            return f"An unexpected error occurred with model '{model}': {str(e)}"

def save_chat():
    if not os.path.exists('./Chats'):
        os.makedirs('./Chats')
    if st.session_state['messages']:
        formatted_messages = format_messages_for_summary(st.session_state['messages'])
        chat_summary = summary(formatted_messages)
        filename = f'./Chats/{chat_summary}.txt'
        with open(filename, 'w') as f:
            for message in st.session_state['messages']:
                # Replace actual newline characters with a placeholder
                encoded_content = message['content'].replace('\n', '\\n')
                f.write(f"{message['role']}: {encoded_content}\n")
        st.session_state['messages'].clear()
    else:
        st.warning("No chat messages to save.")

def load_saved_chats():
    chat_dir = './Chats'
    if os.path.exists(chat_dir):
        # Get all files in the directory
        files = os.listdir(chat_dir)
        # Sort files by modification time, most recent first
        files.sort(key=lambda x: os.path.getmtime(os.path.join(chat_dir, x)), reverse=True)
        for file_name in files:
            display_name = file_name[:-4] if file_name.endswith('.txt') else file_name  # Remove '.txt' from display
            if st.sidebar.button(display_name):
                st.session_state['show_chats'] = False  # Make sure this is a Boolean False, not string 'False'
                st.session_state['is_loaded'] = True
                load_chat(f"./Chats/{file_name}")
                # show_msgs()

def format_chatlog(chatlog):
    # Formats the chat log for downloading
    return "\n".join(f"{msg['role']}: {msg['content']}" for msg in chatlog)

def load_chat(file_path):
    # Clear the existing messages in the session state
    st.session_state['messages'].clear()  # Using clear() to explicitly empty the list
    show_msgs()
    # Read and process the file to extract messages and populate the session state
    with open(file_path, 'r') as file:
        for line in file.readlines():
            role, content = line.strip().split(': ', 1)
            # Decode the placeholder back to actual newline characters
            decoded_content = content.replace('\\n', '\n')
            st.session_state['messages'].append({'role': role, 'content': decoded_content})

def main():
    st.title("DC Chat Interface")
    user_input = st.chat_input("Enter your Text here:", key="1")
    
    if 'show' not in st.session_state:
        st.session_state['show'] = 'True'
    if 'show_chats' not in st.session_state:
        st.session_state['show_chats'] = 'False'
    if 'messages' not in st.session_state:
        st.session_state['messages'] = []
    if 'upld_file_name' not in st.session_state:
        st.session_state['upld_file_name'] = ''
    show_msgs()
    if user_input:
        with st.chat_message("user"):
            st.write(user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})
        messages = "\n".join(msg["content"] for msg in st.session_state.messages)
        # print(messages)
        response = chat(messages)
        st.session_state.messages.append({"role": "assistant", "content": response})
        with st.chat_message("assistant"):
            st.write_stream(response_generator(response))
    elif st.session_state['messages'] is None:
        st.info("Enter a message or load chat above to start the conversation")
    chatlog = format_chatlog(st.session_state['messages'])
    st.sidebar.download_button(
        label="Download Chat Log",
        data=chatlog,
        file_name="chat_log.txt",
        mime="text/plain"
    )
    for i in range(5):
        st.sidebar.write("")
    if st.sidebar.button("Save Chat"):
        save_chat()

    # show file upload option 
    with st.sidebar:
        st.header("Upload your Image")
        uploaded_file = st.file_uploader("Choose an image...", type=['pdf'])

        if uploaded_file is not None:
            # Display the uploaded image
            os.makedirs("temp", exist_ok=True)

            with open(os.path.join("temp", uploaded_file.name), "wb") as f:
                f.write(uploaded_file.getbuffer())
                image_path = f.name
                logging.info("file details on upload ",image_path)
                st.session_state['upld_file_name'] = image_path
                pdf_viewer(image_path)


    if st.sidebar.button("Submit & Process"):
        with st.spinner("Processing..."):
            if st.session_state.upld_file_name:
                st.write(st.session_state.upld_file_name)
                st.session_state['qa_agent'] = create_qa_agent(st.session_state.upld_file_name)
                logging.info("file details on submit ")




    # Show/Hide chats toggle
    if st.sidebar.checkbox("Show/hide chat history", value=st.session_state['show_chats']):
        st.sidebar.title("Previous Chats")
        load_saved_chats()
        
    for i in range(3):
        st.sidebar.write(" ")
    

if __name__ == "__main__":
    main()


