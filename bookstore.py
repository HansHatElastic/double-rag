import streamlit as st
from elasticsearch import Elasticsearch
from datetime import date
import ast


# --- Authentication Section ---
es_host = "https://minutes-dbfc0f.es.us-east-1.aws.elastic.cloud:443"
es_api_key = "ZGhmWDZKY0JvVnJ5ejlfWkNDSXI6aFJ1Ym9seGYyOUFyR1p5aXNpQVNRQQ=="
es_iid = "proxy_completion"

# --- Service Clients ---
es_client = Elasticsearch(hosts=[es_host], api_key=es_api_key)

# --- Building Blocks for Service Calls ---
def search_elasticsearch(query_no, query):
    if query_no == 1:
        es_query = {
            "retriever": {
                "standard": {
                    "query": {
                        "semantic": {
                            "field": "semantic_text",
                            "query": query
                        }
                    }
                }
            },
            "highlight": {
                "fields": {
                    "semantic_text": {
                        "type": "semantic",
                        "number_of_fragments": 2,
                        "order": "score"
                    }
                }
            }
        }
        full_result = es_client.search(
            index=".kibana-observability-ai-assistant-kb-000002",
            body=es_query
        )
        result = full_result["hits"]["hits"]
    elif query_no == 2:
        es_query = {
            "retriever": {
                "rrf": {
                    "retrievers": [
                        {
                            "standard": {
                                "query": {
                                    "semantic": {
                                        "field": "summary-of-content_semantic",
                                        "query": query
                                    }
                                }
                            }
                        },
                        {
                            "standard": {
                                "query": {
                                    "semantic": {
                                        "field": "summary-of-reviews_semantic",
                                        "query": query
                                    }
                                }
                            }
                        },
                        {
                            "standard": {
                                "query": {
                                    "semantic": {
                                        "field": "title_semantic",
                                        "query": query
                                    }
                                }
                            }
                        },
                        {
                            "standard": {
                                "query": {
                                    "semantic": {
                                        "field": "category",
                                        "query": query
                                    }
                                }
                            }
                        },
                        {
                            "standard": {
                                "query": {
                                    "multi_match": {
                                        "query": query,
                                        "fields": [
                                            "author",
                                            "publisher",
                                            "original-language",
                                            "ISBN"
                                        ]
                                    }
                                }
                            }
                        }
                    ]
                }
            },
            "highlight": {
                "fields": {
                    "summary-of-content_semantic": {
                        "type": "semantic",
                        "number_of_fragments": 2,
                        "order": "score"
                    },
                    "summary-of-reviews_semantic": {
                        "type": "semantic",
                        "number_of_fragments": 2,
                        "order": "score"
                    },
                    "title_semantic": {
                        "type": "semantic",
                        "number_of_fragments": 2,
                        "order": "score"
                    }
                }
            },
            "size": 5
        }
        full_result = es_client.search(
            index="books",
            body=es_query
        )
        result = full_result["hits"]["hits"]
    else:
        print("Invalid query selection")
        result = []
    return result

def es_completion(prompt, inference_id):
    response = es_client.inference.inference(
        inference_id=inference_id,
        task_type="completion",
        input=prompt
    )
    return response['completion'][0]['result']

# --- UI Elements ---

st.set_page_config(page_title="The Friendly Bookstore", layout="centered")
st.title(":books: The Friendly Bookstore",width="stretch")

with st.form("chat_form"):
    
    col1, col2 = st.columns(2)
    with col1:
        chat_date = st.date_input(":blue-background[  Date of chat  ]", value=date.today())
        birth_date = st.date_input(":blue-background[ Your Birthdate ]", value=date(1999, 10, 11),min_value="1900-01-01")
    with col2:
        name = st.text_input(":blue-background[  Your Name  ]", max_chars=50, value="Mary Jones")
        city = st.text_input(":blue-background[  Where do you live  ]", value="Amsterdam")
    user_message = st.text_area(r"$\textsf{\large How can we help you?}$", value="Can you recommend some recent books?")
    submitted = st.form_submit_button(label="Just Ask !!",icon=":material/chat_paste_go:")
 
if submitted:
    
    # --- Input Validation ---
    if not name.strip() or not any(char.isalnum() for char in name):
        
        st.error("Name must contain at least one alphanumeric character.")
    elif not user_message.strip():
        st.error("Please enter a message.")
    else:
        # --- Call Services ---
        config_message = (f"""
            Find: What books categories are interesting by age, 
            what books categories are bought in seasons and for holidays,
            our customer profile,
            our business objectives,                             
            and contact information for our store"
            """              
        )
        es_results = search_elasticsearch(1, config_message)
        es_info = ""
        for i in range(len(es_results)):
            es_info += es_results[i]["highlight"]["semantic_text"][0]

        # Ask LLM for creating the query configuration
        prompt_query = f"""
Instructions:

- You are an Assistant for creating parts of prompts. Your goal is to deliver precise and professional responses only based on the provided information below, labeled as 'Context'. All generated content should be in English.

-Definitions of the output:
1. Name : just the following value: {name}  
2. Date: just the following value: {chat_date}
3. Age: Calculate the age of the user on {chat_date}, given the birth date {birth_date}. Age should be just a numeric value
4. Distance to the store: Calculate the he travel distance from {city} to Amsterdam in kilometers, and put only the numerical result here in 
5. Season and or holidays: List here,separated by comma's, given the date {chat_date}, what season we are in, and what Dutch holidays and events are in the near future
6. Categories: a comma separated list of book categories. These categories should be derived from the context below based on age, and the time of the year given by the date {chat_date}.
    Only list the top 3 most relevant categories  
7. Customer profile: a summary of maximum 200 words of our customer profile
8. Business objectives : a summary of maximum 200 words of our business objectives
9. Contact information : Name of the store address of the book store in Amsterdam, and the web site

Always follow this exact structure when responding, a well-formed Python dictionary containing the values as described above, containing only the following entries:
-"name": <the value of name as described above, enclosed in double quotes>,
-"date": <the value of date as described above, enclosed in double quotes>,
-"age" : <the value of age as described above, no quotes, numerical value>,
-"distance": <the value of distance as described above, no quotes, numerical value>,
-"season_holidays": <the value of season or holidays as described above, enclosed in double quotes>,    
-"categories": <the value of categories as described above, enclosed in double quotes>, 
-"contact_information": <the value of contact information as described above, enclosed in double quotes>,
-"customer_profile": <the value of the customer profile as described above, enclosed in double quotes>,
-"business_objectives": <the value of the business objectives as described above, enclosed in double quotes>

Context:
{es_info}
"""
        llm_query_content = es_completion(prompt_query, es_iid)
        llm_query_content = ast.literal_eval(llm_query_content)
        st.subheader(":card_index: *Building block for the books query*",divider="grey",)
        st.json(llm_query_content)

        # Query the right books
        books_query = f"""
{user_message},
Categories: {llm_query_content["categories"]}
"""
        es_results = search_elasticsearch(2, books_query)

        # Asking the LLM to make the final response
        prompt_chat = f"""
Instructions:
- You are a friendly chatbot for the web shop of {llm_query_content["contact_information"]}. You only answers questions regarding the content described in this prompt. 
- The question of the user of the chatbot is : {user_message}
- The person you are talking to is {llm_query_content["name"]}, aged {llm_query_content["age"]}
- The information you deliver is related to date {llm_query_content["date"]}, and if applicable mention the seasons or holidays mentioned here : {llm_query_content["season_holidays"]}
- The distance to the store is {llm_query_content["distance"]} kilometers. If this distance is less than 10 kilometers recommend visiting the store in Amsterdam, else refer to the web site. Do not mention actual distance in the response, but use terms as 'close' , or 'far'
- The user is mainly interested in books in the categories : {llm_query_content["categories"]}
- Books that are interesting for the user are described in this API response: {es_results}, use only books from this API response
- The URL to the page of the book on the web site of our store has the following structure: https://www.the-friendly-bookstore.nl/<ISNBN> , where <ISBN> is the ISBN number of the book. 
   Always mention the url when you mention a book.
- Take into account our customer profile as described here : {llm_query_content["customer_profile"]}
- Align your response with our business objectives : {llm_query_content["business_objectives"]}
- Do not list all categories of interest in the response
- Your response should be at the most 250 words
- Always respond in English (UK)
"""
        llm_final_content = es_completion(prompt_chat, es_iid)
       
        st.subheader(":sparkles: *Search AI Response*",divider="grey")
        st.markdown(llm_final_content)
        st.image("elastic-logo.svg",width=200)

        