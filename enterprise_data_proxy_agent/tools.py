from google.cloud import geminidataanalytics
import pandas as pd
import time
from datetime import datetime
import logging
import os


PROJECT_ID = os.environ.get("PROJECT_ID", "kallogjeri-project-345114")
LOCATION = os.environ.get("LOCATION", "global")
DATA_AGENT_ID = os.environ.get("DATA_AGENT_ID", "agent_4310cf0c-cb88-439a-ab85-f57f62bfc7f9")
def get_clients():
    data_agent_client = geminidataanalytics.DataAgentServiceClient()
    data_chat_client = geminidataanalytics.DataChatServiceClient()
    return data_agent_client, data_chat_client


def extract_sql_from_response(msg):
    m = msg.system_message
    if 'data' in m:
        data_resp = getattr(m, 'data')
        if 'generated_sql' in data_resp:
            return data_resp.generated_sql
    return None

def extract_data_from_response(msg):
    m = msg.system_message
    if 'data' in m:
        data_resp = getattr(m, 'data')
        if 'result' in data_resp:
            result = data_resp.result
            fields = [field.name for field in result.schema.fields]
            d = {}
            for el in result.data:
                for field in fields:
                    if field in d:
                        d[field].append(el.get(field, None))
                    else:
                        d[field] = [el.get(field, None)]
            return pd.DataFrame(d)
    return None

def extract_text_from_response(msg):
    m = msg.system_message
    if 'text' in m:
        text_resp = getattr(m, 'text')
        parts = text_resp.parts
        full_text = "".join(parts)
        return {
            'type': text_resp.text_type,
            'content': full_text
        }
    return None

def format_sql(sql):
    if not sql:
        return ""
    
    keywords = ['SELECT', 'FROM', 'WHERE', 'GROUP BY', 'ORDER BY', 'LIMIT', 
                'JOIN', 'LEFT', 'RIGHT', 'INNER', 'OUTER', 'ON', 'AS', 
                'AND', 'OR', 'COUNT', 'SUM', 'AVG', 'MAX', 'MIN', 'HAVING',
                'DISTINCT', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END']
    
    formatted = sql
    for keyword in keywords:
        formatted = formatted.replace(f' {keyword} ', f' <span class="sql-keyword">{keyword}</span> ')
        formatted = formatted.replace(f'\n{keyword} ', f'\n<span class="sql-keyword">{keyword}</span> ')
        if formatted.startswith(keyword):
            formatted = f'<span class="sql-keyword">{keyword}</span>' + formatted[len(keyword):]
    
    return formatted

def query_agent(question, conversation_messages=None):
    print(f"--- query_agent start: {question} ---")
    if conversation_messages is None:
        conversation_messages = []
    
    print("Initializing DataChatServiceClient...")
    _, data_chat_client = get_clients()
    
    # Create message
    print("Creating message object...")
    message = geminidataanalytics.Message()
    message.user_message.text = question
    conversation_messages.append(message)
    
    # Set up context
    print(f"Setting up context for Data Agent: {DATA_AGENT_ID}...")
    data_agent_context = geminidataanalytics.DataAgentContext()
    data_agent_context.data_agent = f"projects/{PROJECT_ID}/locations/{LOCATION}/dataAgents/{DATA_AGENT_ID}"
    
    # Create request
    print("Creating ChatRequest...")
    request = geminidataanalytics.ChatRequest(
        parent=f"projects/{PROJECT_ID}/locations/{LOCATION}",
        messages=conversation_messages,
        data_agent_context=data_agent_context
    )
    
    # Get response
    print("Calling data_chat_client.chat (streaming)...")
    try:
        stream = data_chat_client.chat(request=request, timeout=300)
    except Exception as e:
        print(f"❌ Error during chat call: {e}")
        raise
    
    results = {
        'sql': None,
        'data': None,
        'explanation': None,
        'thoughts': [],
        'progress_updates': [],
        'all_text_responses': [],
        'chart': None,
        'suggested_questions': []
    }
    
    print("Iterating through response stream...")
    count = 0
    for response in stream:
        count += 1
        print(f"Received chunk {count}")
        conversation_messages.append(response)
        
        # Extract SQL
        sql = extract_sql_from_response(response)
        if sql:
            print(f"Found SQL in chunk {count}")
            results['sql'] = sql
        
        # Extract data
        data = extract_data_from_response(response)
        if data is not None:
            print(f"Found data in chunk {count}")
            results['data'] = data
            
        # Extract Chart
        if hasattr(response.system_message, 'chart') and response.system_message.chart:
            chart_res = response.system_message.chart.result
            if chart_res and chart_res.vega_config:
                def proto_to_dict(obj):
                    if hasattr(obj, "items"):
                        return {k: proto_to_dict(v) for k, v in obj.items()}
                    elif hasattr(obj, "__iter__") and not isinstance(obj, (str, bytes)):
                        return [proto_to_dict(x) for x in obj]
                    else:
                        return obj
                results['chart'] = proto_to_dict(chart_res.vega_config)
        
        # Extract suggested questions (follow-up questions)
        if hasattr(response.system_message, 'text') and response.system_message.text:
            text_resp = response.system_message.text
            type_val = text_resp.text_type
            
            def is_type(val, enum_name, enum_int):
                if val == enum_name or val == enum_int:
                    return True
                if hasattr(val, 'name') and val.name == enum_name:
                    return True
                return False

            if is_type(type_val, 'FOLLOWUP_QUESTIONS', 4):
                results['suggested_questions'].extend(list(text_resp.parts))
        
        # Extract ALL text responses
        text = extract_text_from_response(response)
        if text:
            results['all_text_responses'].append(text)
            
            type_val = text['type']
            def is_type(val, enum_name, enum_int):
                if val == enum_name or val == enum_int:
                    return True
                if hasattr(val, 'name') and val.name == enum_name:
                    return True
                return False

            if is_type(type_val, 'FINAL_RESPONSE', 1):
                print(f"Found FINAL_RESPONSE in chunk {count}")
                results['explanation'] = text['content']
            elif is_type(type_val, 'THOUGHT', 2):
                results['thoughts'].append(text['content'])
            elif is_type(type_val, 'PROGRESS_UPDATE', 3) or is_type(type_val, 'PROGRESS', 3):
                results['progress_updates'].append(text['content'])
    
    print(f"--- query_agent finished ({count} chunks) ---")
    return results

def call_claims_agent(question: str) -> str:
    """Queries the Claims Data Agent with a natural language question and returns the answer."""
    print(f"--- tool call: call_claims_agent('{question}') ---")
    import json
    try:
        # We start a new conversation for each tool call
        response = query_agent(question)
        print(f"DEBUG: query_agent returned: {response}")
        
        explanation = response.get('explanation') or ""
        sql = response.get('sql') or ""
        chart = response.get('chart')
        suggested_questions = response.get('suggested_questions') or []
        
        data_records = []
        data = response.get('data')
        if data is not None and not data.empty:
            data_records = data.to_dict(orient="records")
            
        if not explanation.strip() and response.get('all_text_responses'):
            explanation = "\n".join([f"[{t.get('type')}]: {t.get('content')}" for t in response['all_text_responses']])
            
        structured_response = {
            "explanation": explanation,
            "sql": sql,
            "data": data_records,
            "chart": chart,
            "suggested_questions": suggested_questions
        }
        
        final_output = json.dumps(structured_response, indent=2)
        print(f"Tool call successful. Output length: {len(final_output)}")
        return final_output
    except Exception as e:
        logging.error(f"Error calling claims agent: {e}", exc_info=True)
        return json.dumps({
            "error": f"The tool failed with an error: {e}"
        })


# --- Sample USAGE ---
if __name__ == "__main__":
    pass
    # res=query_agent("how many rows of data are available in the table")
    # print(res)

