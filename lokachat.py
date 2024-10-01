import boto3
import os
import random
import streamlit as st
import csv

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
    st.set_page_config(page_title="Documentation Chat")
    st.markdown("""
    <style>
    .huge-font {
        font-size:40px !important;
    }
    .huge-font-italic {
        font-size:20px !important;
        font-style: italic;
    }
    .big-font {
        font-size:18px !important;
    }

    .big-font-italic {
        font-size:15px !important;
        font-style: italic;
        text-align: center;
    }

    .disclaimer-font {
        font-size:15px !important;
        font-style: italic;
        text-align: center;
    }
    .release-notes-font {
        font-size:15px !important;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)
    col1, mid, col2 = st.columns([4, 1, 20])
    with col1:
        st.image('media/loka_logo.jpg', width=100)
    with col2:
        st.markdown(
            f'<p><span class="huge-font"><b>Document Chatbot</b></span> <span class="huge-font-italic">(Limited Support POC)</span></p>',
            unsafe_allow_html=True)
    subheader_text = "Hi! Welcome to Document Chatbot (powered by <a href='https://www.linkedin.com/in/dr-alberto-beltran/'>Soullest</a>)"
    disclaimer_text = ''

    st.markdown(f'<p class="big-font">{subheader_text}</p>', unsafe_allow_html=True)


def sidepanel_setup() -> None:
    with st.sidebar:
        st.title('Example questions')
        st.info("""
        • What is SageMaker?\n
        • What are all AWS regions where SageMaker is available?\n
        • How to check if an endpoint is KMS encrypted?\n
        • What are SageMaker Geospatial capabilities?\n
        """)
        st.divider()
        st.write("History Logs")


def load_links() -> None:
    if 'links_dict' not in st.session_state:
        filename = 'links.csv'
        st.session_state.links_dict = {}

        with open(filename, mode='r') as file:
            reader = csv.reader(file)

            for row in reader:
                st.session_state.links_dict[row[0]] = row[1]
        print(st.session_state.links_dict)

def bedrock_setup() -> None:
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

    load_links()

    if not st.session_state.history.messages:
        st.session_state.history.add_user_message("Hello")
        st.session_state.history.add_ai_message("How may I assist you today?")

    for msg in st.session_state.history.messages[1:]:
        st.chat_message(msg.type).write(msg.content, unsafe_allow_html=True)

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
        emb_info, metainfo = aoss_emb.query(question=emb_abs, k=10, links_dict=st.session_state.links_dict)
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
        {full_response}\n\n**You can find more information in the following sources:**\n\n{metainfo}
        """

        print(full_response)
        placeholder.chat_message("ai").write(full_response, unsafe_allow_html=True)
        st.session_state.history.messages[-1].content = full_response


if __name__ == "__main__":
    main()

