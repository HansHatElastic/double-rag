import streamlit as st
from elasticsearch import Elasticsearch
from datetime import date

# --- Authentication Section ---

es_host = "https://minutes-dbfc0f.es.us-east-1.aws.elastic.cloud:443"
es_api_key="ZGhmWDZKY0JvVnJ5ejlfWkNDSXI6aFJ1Ym9seGYyOUFyR1p5aXNpQVNRQQ=="
es_iid="proxy_completion"

 # --- Service Clients ---
es_client=Elasticsearch(hosts=[es_host], api_key=es_api_key) 

# --- UI Elements ---
st.title("Bookstore Chatbot")

chat_date = st.date_input("Date", value=date.today())
name = st.text_input("Name (alphanumeric only)", max_chars=50)
age = st.text_input("Age (numbers only)", max_chars=3)
city = st.text_input("City")
user_message = st.text_area("Your Question/Chat")

if st.button("Submit"):
    # --- Input Validation ---
    if not name.isalnum():
        st.error("Name must be alphanumeric.")
    elif not age.isdigit():
        st.error("Age must be numeric.")
    elif not user_message.strip():
        st.error("Please enter a message.")
   
    else:
       

        # --- Building Blocks for Service Calls ---
        # Call LLM
        def es_completion(prompt, inference_id):
    
          response = es_client.inference.inference(
              inference_id = inference_id,
              task_type = "completion",
              input = prompt
           )

          return response['completion'][0]['result']

        #  Call ElasticSearch
        def search_elasticsearch(query):
            es_query = {
                "retriever": {
                    "rrf": {
                        "retrievers": [
                            {
                                "standard": {
                                    "query": {
                                        "semantic": {
                                            "field": "semantic_text",
                                            "query": query
                                        }
                                    }
                                }
                            },
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
                            }
                        ]
                    }
                },
                "highlight": {
                    "fields": {
                        "semantic_text": {
                            "type": "semantic",
                            "number_of_fragments": 2,
                            "order": "score"
                        },
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
                "size": 10
            }
            result = es_client.search(index="booklist,.kibana-observability-ai-assistant-kb-000002", body=es_query)
            return result["hits"]["hits"]

        # --- Example Usage ---
        # Call LLM with user message
        ai_response = es_completion(user_message,es_iid)
        st.markdown("**Chatbot Response:**")
        st.write(ai_response)

        # Optionally, show ElasticSearch results (for demonstration)
        es_results = search_elasticsearch(user_message)
        st.markdown("**ElasticSearch Results:**")
        st.json(es_results)