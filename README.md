# How to run

It is recommended to use python 3.10 or higher, as well as the virtual machine of your choice, after which you will only need to install the dependencies with the following command

```
pip install -r requirements.txt
```
Tras la instalación de las dependencias el sistema esta listo para correr en un ambiente local usando la siguiente instrucción:

```
streamlit run lokachat.py
```

## Project Description

To meet the requested features, a chatbot programmed in python and supported by AWS Bedrock has been proposed with a vector database in OpenSearch also stored within the same AWS account and communicated internally by a private VPC that encapsulates the data in the US-EAST-1 region, complying with the requirement of preventing data from leaving the United States and protecting any PII that may be stored within the documentation.

Claude 3 Sonete has been chosen as the foundational model as the main engine of the chatbot and as the model for the embeddings Amazon Titan Text Embeddings, to demonstrate the ability to work with different models. Given the current capacity of the system, less heavy models can be chosen, however, if we think about how quickly the number of documents analyzed can scale, and the capacity to access the embeddings, this proposal makes sense

## Credentials

The .env file contains access credentials for a private connection to AWS, these credentials are personal and the user assigned to these credentials has been created temporarily and with limited permissions, only for the recruitment process with LOKA, please make responsible use of these credentials without incurring any abuse.

## Contact

Dr. Alberto Beltrán Herrera:

[Linkedin](https://www.linkedin.com/in/dr-alberto-beltran/)



