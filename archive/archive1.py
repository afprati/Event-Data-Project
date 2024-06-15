import os
from openai import AzureOpenAI
import pandas as pd
import time
import config
#import tiktoken
import json

seed = 1234

# for token counting
#def num_tokens_from_string(string: str, encoding_name: "gpt-4o") -> int:
#    encoding = tiktoken.encoding_for_model(encoding_name)
#    num_tokens = len(encoding.encode(string))
#    return num_tokens

# for rate limiting
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
)  # for exponential backoff
 
@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
def completion_with_backoff(**kwargs):
    return get_labels(**kwargs)

    
client = AzureOpenAI(
  api_key=config.api_key,  
  api_version= "2024-02-01",
  azure_endpoint = config.endpoint_url,
)
 
    
deployment_name='gpt4' #This will correspond to the custom name you chose for your deployment when you deployed a model. Use a gpt-35-turbo-instruct deployment. 
max_tokens=40

instructions = """I will give a title, publication date, and text of newspaper articles. Tell me in this order:
1. On a scale of 0 to 10 rate if this article discusses a violent event in Nepal, where 0 is definitely no and 10 is definitely yes? See examples below. Be conservative. 
2. If rating is at least 5: what is the date(s) of the violent event (there might be more than one date)? Use the format “yyyy-mm-dd”. Separate by a semicolon. If the article also mentions peaceful events, do not tell me those dates. If no date is mentioned, use the publication date. For example if the article says events happened on Friday and is published on Sunday, subtract two days from the publication date. 
3. If rating is at least 5: what is the location(s) (there might be more than one location)? Be as specific as possible. Format as: “City, District”. Sometimes only a district is mentioned. Separate multiple locations with a semicolon. If the article also mentions peaceful events, do not tell me those places. 
4. Rate how sure are you about the date(s) and place(s), where 0 is not sure at all and 10 is very sure? Provide a single COMBINED score. If you did not find a date and/or place, rate how sure you are that no date(s) or place(s) were mentioned. Be conservative. 
Types of events that most likely ARE violent: Protests/marches that turn violent (people are arrested, beaten, turn into riots, etc.) Riots; Maoists, rebels, guerillas, or soldiers killed by each other; Shootings; Bombings; Detentions/arrests; Burning things; Abductions/kidnappings; Sexual assaults/rapes, including sexual harassment
Types of events that most likely are NOT violent: Accidents; Peaceful protests/marches; Discussions of pervasive problems like violence against women or human trafficking; Natural disasters; Attacks by wild animals; Public health problems or disease outbreaks; General strategy, such as laying out landmines; Events described in movies, TV shows, books, etc.; Suicides; Jail breaks; Smuggling; Drug issues;	Bomb defusals"""

test_text = "At least three anti-government guerrillas were gunned down Thursday on the spot in Surkhet district, while another four were killed Wednesday in Dang district, all located in western Nepal, the radio quoted a press release issued by the Defense Ministry as saying.\r\n----\r\nYANGON -- The Myanmar government put 15 columnists of eight Thai newspapers on its blacklist for their involvement in articles considered causing split among the country 's state leaders, armed forces and ethnic armed groups which have already ceased fire with the government.\r\nLoad-Date: July 13, 2002\r\nEnd of Document"

batch_test = pd.read_csv("data/batch_test.csv")
batch_test = batch_test.iloc[0:2]
batch_num = 1

# how to format output
labeling = [{
    "name": "labeling_articles",
    "description": "A function that labels newspaper articles for violence and NER",
    "parameters": {
        "type": "object",
        "properties": {
            "labels": {
                "type": "array",
                "description": "A list labels from newspaper article.",
                "items":{
                    "violence": {"type":"integer", "description": "Is this about violence?"},
                    "location": {"type":"string", "description": "If about violence, where?"},
                    "date": {"type": "string", "description": "If about violence, when?"},
                    "confidence": {"type": "integer", "description": "Confidence on place/date"}
                    }
                }
        }, "required": ["labels"]
        }}]


DATA_DIR = 'C:\\Users\\miame\\OneDrive\\Backups\\Documents\\GitHub\\Event-Data-Project\\results\\'
json_files = []
batch_results = pd.DataFrame()
error_tracking = pd.DataFrame()    

def get_labels(data, system_messages, user_messages, model=deployment_name, batch_num=batch_num, temperature=0, max_tokens=max_tokens):
    try:
        response = client.chat.completions.create(
            model = model,
            seed = seed, 
            #functions=labeling,
            #function_call = {"name": "labeling_articles"},
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[
              {"role": "system",
               "content": system_messages},
              {"role": "user",
               "content": user_messages}
            ] 
         ) 
        print(response.choices[0].message.content)
        
        content = response.model_dump_json(indent=2)
        json_files.append(json.loads(content))
        json_file_name = "batch"+str(batch_num)+"gpt4.json"
        with open(DATA_DIR + json_file_name, "w") as file:
          json.dump(json_files, file)
        content_json = json.loads(content)
        contents = content_json["choices"][0]["message"]["content"]
        new_row = str(data["doc_id_number"][i]) + "\n"+ contents
        batch_results = batch_results._append(new_row, ignore_index=True)
    except:
        print("Error")
        error_tracking = pd.concat(error_tracking, pd.DataFrame(data['doc_id_number'].iloc[i]), ignore_index=True)



start = time.time()

for i in range(len(batch_test)-1):
    print("starting article ", i +1, " of ", len(batch_test))
    user_text = batch_test["text_short"][i]
    completion_with_backoff(data=batch_test, system_messages=instructions,user_messages=user_text)
timestr = time.strftime("%Y%m%d-%H%M%S")
file1 = "batch_results_" + timestr + ".tsv"
file2 = "error_tracking_" + timestr + ".tsv"
batch_results.to_csv(file1, sep='\t')
error_tracking.to_csv(file2, sep='\t')

end = time.time()

print("total time: ", end-start)


