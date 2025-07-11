import re
import time
import sqlite3
from datetime import datetime
from rca.api_router import get_chat_completion
import tiktoken
import traceback
import pandas as pd
import os
import json

DB_PATH = 'dataset/Telecom/data.db'

# Helper to get dataset name from DB_PATH

def get_dataset_name_from_db_path(db_path):
    parts = db_path.replace('\\', '/').split('/')
    if 'dataset' in parts:
        idx = parts.index('dataset')
        if idx + 1 < len(parts):
            return parts[idx + 1]
    return 'unknown'

def get_sql_logger(db_path):
    dataset_name = get_dataset_name_from_db_path(db_path)
    log_path = os.path.join('dataset', dataset_name, 'sql_executor.log')
    def log(msg):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        line = f"[{timestamp}] {msg}"
        print(line)
        with open(log_path, 'a') as f:
            f.write(line + '\n')
    return log

system = """You are a DevOps assistant for writing SQL queries to answer RCA (Root Cause Analysis) questions. For each question, you need to write a SQL query to solve it by retrieving and processing telemetry data of the target system. Your generated SQL query will be automatically submitted to a SQLite database. The execution result output in SQLite will be used as the answer to the question.

{rule}

There is some domain knowledge for you:

{background}

Your response should follow the SQL block format below:

{format}"""

format = """```sql
(YOUR SQL QUERY HERE)
```"""

summary = """The SQL execution is successful. The execution result is shown below: 

{result}

Please summarize a straightforward answer to the question based on the execution results. Use plain English."""

conclusion = """{answer}

The original SQL execution output is also provided below for reference:

{result}"""

rule = """## RULES OF SQL QUERY WRITING:

1. Use only the tables and columns provided in the schema.
2. Do not use Python or any programming language other than SQL.
3. If you encounter an error or unexpected result, revise your SQL query by referring to the given SQLite error message or empty result.
4. Do not simulate any virtual situation or assume anything unknown. Solve the real problem.
5. Do not store any data as files in the disk. Only use SQL queries to retrieve data.
6. Do not generate anything else except the SQL code block except the instruction tells you to 'Use plain English'. If you find the input instruction is a summarization task (which is typically happening in the last step), you should comprehensively summarize the conclusion as a string and display it directly.
"""

def execute_act(instruction: str, background: str, history, attempt, logger) -> str:
    logger.debug("Start execution")
    t1 = datetime.now()
    if history == []:
        history = [
            {'role': 'system', 'content': system.format(rule=rule, background=background, format=format)},
        ]
    sql_pattern = re.compile(r"```sql\n(.*?)\n```", re.DOTALL)
    sql_code = ""
    result = ""
    retry_flag = False
    status = False
    history.extend([{'role': 'user', 'content': instruction}])
    prompt = history.copy()
    note = [{'role': 'user', 'content': f"Continue your SQL writing process following the rules:\n\n{rule}\n\nResponse format:\n\n{format}"}]
    tokenizer = tiktoken.encoding_for_model("gpt-4")
    sql_log = get_sql_logger(DB_PATH)
    for i in range(2):
        try:
            if not retry_flag:
                response = get_chat_completion(
                    messages=prompt + note,
                )
            else:
                response = get_chat_completion(
                    messages=prompt,
                )
                retry_flag = False
            if re.search(sql_pattern, response):
                sql_code = re.search(sql_pattern, response).group(1).strip()
            else:
                sql_code = response.strip()
            logger.debug(f"Raw SQL:\n{sql_code}")
            sql_log(f"Executing SQL query (attempt {i+1}):\n{sql_code}")
            # Execute SQL
            try:
                with sqlite3.connect(DB_PATH) as conn:
                    df = None
                    try:
                        df = pd.read_sql_query(sql_code, conn)
                        status = True
                        if df.empty:
                            result = "(No results)"
                            sql_log(f"Query returned no results.")
                        else:
                            max_rows = 20
                            truncated = False
                            if len(df) > max_rows:
                                truncated = True
                                result = df.head(max_rows).to_string(index=False)
                                result += f"\n\n**Note**: Only the first {max_rows} rows are shown. The result was truncated."
                                sql_log(f"Query result truncated to {max_rows} rows.")
                            else:
                                result = df.to_string(index=False)
                            sql_log(f"Query result:\n{result}")
                    except Exception as sql_err:
                        status = False
                        result = str(sql_err)
                        sql_log(f"SQL ERROR: {result}")
            except Exception as db_err:
                status = False
                result = str(db_err)
                sql_log(f"DB ERROR: {result}")
            if status:
                tokens_len = len(tokenizer.encode(result))
                if tokens_len > 16384:
                    logger.warning(f"Token length exceeds the limit: {tokens_len}")
                    sql_log(f"Token length exceeds the limit: {tokens_len}")
                    continue
                t2 = datetime.now()
                logger.debug(f"Execution Result:\n{result}")
                logger.debug(f"Execution finished. Time cost: {t2-t1}")
                history.extend([
                    {'role': 'assistant', 'content': sql_code},
                    {'role': 'user', 'content': summary.format(result=result)},
                ])
                answer = get_chat_completion(
                    messages=history,
                )
                logger.debug(f"Brief Answer:\n{answer}")
                history.extend([
                    {'role': 'assistant', 'content': answer},
                ])
                result = conclusion.format(answer=answer, result=result)
                sql_log(f"Final answer: {answer}")
                return sql_code, result, status, history
            else:
                t2 = datetime.now()
                logger.warning(f"Execution failed. Error message: {result}")
                logger.debug(f"Execution finished. Time cost: {t2-t1}")
                prompt.append({'role': 'assistant', 'content': sql_code})
                prompt.append({'role': 'user', 'content': f"Execution failed:\n{result}\nPlease revise your SQL query and retry."})
                retry_flag = True
        except Exception as e:
            logger.error(e)
            sql_log(f"UNCAUGHT ERROR: {e}")
            time.sleep(1)
    t2 = datetime.now()
    logger.error(f"Max try reached. Please check the history. Time cost: {t2-t1}")
    sql_log(f"Max try reached. Final error: {result}")
    err = "The Executor failed to complete the instruction, please re-write a new instruction for Executor."
    history.extend([{'role': 'assistant', 'content': err}])
    return err, err, True, history