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
from embeddings_aoss import AOSSEmbeddings

from dotenv import load_dotenv
load_dotenv()

aoss_emb = AOSSEmbeddings()

def title_setup() -> None:
    """
    Set up the title, subtitle and information in the header
    """
    st.set_page_config(page_title="Documentation Chat", layout="wide")
    st.title("Documentation Chat")


def sidepanel_setup() -> None:
    with st.sidebar:
        st.title('Example questions')
        st.divider()
        st.write("History Logs")


def bedrock_setup():
    if 'setup_ready' not in st.session_state:
        print('#$%&')

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
        prompt_emb = ChatPromptTemplate.from_template("Question: {question}")

        model = ChatBedrock(
            client=bedrock_runtime,
            model_id=model_id,
            model_kwargs=model_kwargs,
        )

        # Chain with no History
        chain = prompt | model | StrOutputParser()
        st.session_state.chain_emb = prompt_emb | model | StrOutputParser()

        # Streamlit Chat Message History
        st.session_state.history = StreamlitChatMessageHistory(key="chat_messages")

        # Chain with History
        st.session_state.chain_with_history = RunnableWithMessageHistory(
            chain,
            lambda session_id: st.session_state.history,
            input_messages_key="question",
            history_messages_key="history",
        )

        st.session_state.setup_ready = 0



def main() -> None:
    """
    This function will be reach as the start point to the chat
    """
    title_setup()

    if "widget_key" not in st.session_state:
        st.session_state["widget_key"] = str(random.randint(1, 1000000))

    sidepanel_setup()

    bedrock_setup()

    if not st.session_state.history.messages:
        st.session_state.history.add_user_message("Hello")
        st.session_state.history.add_ai_message("How may I assist you today?")

    for msg in st.session_state.history.messages[1:]:
        st.chat_message(msg.type).write(msg.content)

    # Get the prompt from the user
    if prompt := st.chat_input():
        st.chat_message("user").write(prompt)
        config = {"configurable": {"session_id": "any"}}
        emb_question = f"""
        Summarize the following question in only the 3 to 5 most relevant words. 
        Answer using only 3 to 5 words, do not add anything else.
        Question: {prompt}
        """
        emb_abs = st.session_state.chain_emb.invoke({"question": emb_question}, config)
        print(f"{'-'*20}\nEmb abstract: {emb_abs}\n{'-'*20}")
        emb_info, metainfo = aoss_emb.query(question=emb_abs, k=10)
        full_question = f"""Answer the following question:
        {prompt}
        You can use the following information as guide.
        {emb_info}
        """
        print(f"{'*'*20}\n{full_question}\n{'*'*20}")
        placeholder = st.empty()
        full_response = ''
        for chunk in st.session_state.chain_with_history.stream({"question": prompt}, config):
            full_response += chunk
            placeholder.chat_message("ai").write(full_response)

        full_response = f"""
        {full_response}\n\n\t\t**You can find more information in the following sources:**\n\n\t\t{metainfo}
        """

        print(full_response)
        placeholder.chat_message("ai").write(full_response)


if __name__ == "__main__":
    main()

