import boto3
import os
import random
import streamlit as st

from langchain_aws import ChatBedrock
from langchain_community.chat_message_histories import StreamlitChatMessageHistory
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts import MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory


from dotenv import load_dotenv
load_dotenv()


def title_setup() -> None:
    """
    Setup the title, subtitle and information in the header
    """
    st.title_setup(page_title="Documentation Chat", layout="wide")
    st.title("Documentation Chat")


def sidepanel_setup() -> None:
    with st.sidebar:
        st.title('Example questions')
        st.divider()
        st.write("History Logs")



def main() -> None:
    """
    This function will be reach as the start point to the chat
    """
    title_setup()

    if "widget_key" not in st.session_state:
        st.session_state["widget_key"] = str(random.randint(1, 1000000))

    sidepanel_setup()

    # Bedrock setup

    boto_session = boto3.session.Session(
        aws_access_key_id=os.environ["AWS_ACCESS_KEY"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"]
    )

    bedrock_runtime = boto_session.client(
        service_name="bedrock-runtime",
        region_name="us-east-1",
    )

    model_kwargs = {
        "max_tokens": 2048,
        "temperature": 0.0,
        "top_k": 250,
        "top_p": 1,
        "stop_sequences": ["\n\nUser"],
    }

    model_id = "anthropic.claude-3-sonnet-20240229-v1:0"

    template = [
        ("system", "You are a helpful assistant."),
        MessagesPlaceholder(variable_name="history"),
        ("user", "{question}"),
    ]

    prompt = ChatPromptTemplate.from_messages(template)

    model = ChatBedrock(
        client=bedrock_runtime,
        model_id=model_id,
        model_kwargs=model_kwargs,
    )

    # Chain with no History
    chain = prompt | model | StrOutputParser()

    # Streamlit Chat Message History
    history = StreamlitChatMessageHistory(key="chat_messages")

    # Chain with History
    chain_with_history = RunnableWithMessageHistory(
        chain,
        lambda session_id: history,
        input_messages_key="question",
        history_messages_key="history",
    )

    if history.messages == []:
        history.add_user_message("Hello")
        history.add_ai_message("How may I assist you today?")

    for msg in history.messages[1:]:
        st.chat_message(msg.type).write(msg.content)

    # Get the prompt from the user
    if prompt := st.chat_input():
        st.chat_message("user").write(prompt)
        config = {"configurable": {"session_id": "any"}}
        streaming_on = True
        if streaming_on:
            # Chain - Stream
            placeholder = st.empty()
            full_response = ''
            for chunk in chain_with_history.stream({"question": prompt}, config):
                full_response += chunk
                placeholder.chat_message("ai").write(full_response)
            placeholder.chat_message("ai").write(full_response)

        else:
            # Chain - Invoke
            response = chain_with_history.invoke({"question": prompt}, config)
            st.chat_message("ai").write(response)


if __name__ == "__main__":
    main()

