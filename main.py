#import os
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
#max_tokens=40

instructions = """I will give a title, publication date, and text of newspaper articles. Tell me four things in this order:
1. On a scale of 0 to 10 rate if this article discusses a violent event in Nepal, where 0 is definitely no and 10 is definitely yes? If the event is in another country (e.g. Iraq), give a 0. See examples below. Be conservative. 
2. If rating is at least 5: what is the date(s) of the violent event (there might be more than one date)? Use the format “yyyy-mm-dd”. Separate by a semicolon. If the article also mentions peaceful events, do not tell me those dates. If no date is mentioned, use the publication date. For example if the article says events happened on Friday and is published on Sunday, subtract two days from the publication date. 
3. If rating is at least 5: what is the location(s) (there might be more than one location)? Be as specific as possible. Format as: “City: District”. Sometimes only a district is mentioned. Separate multiple locations with a semicolon. If the article also mentions peaceful events, do not tell me those places. 
4. Rate how sure are you about the date(s) and place(s), where 0 is not sure at all and 10 is very sure? Provide a single COMBINED score. If you did not find a date and/or place, rate how sure you are that no date(s) or place(s) were mentioned. Be conservative. 
Types of events that most likely ARE violent: Protests/marches that turn violent (people are arrested, beaten, turn into riots, etc.) Riots; Maoists, rebels, guerillas, or soldiers killed by each other; Shootings; Bombings; Detentions/arrests; Burning things; Abductions/kidnappings; Sexual assaults/rapes, including sexual harassment
Types of events that most likely are NOT violent: Accidents; Peaceful protests/marches; Discussions of pervasive problems like violence against women or human trafficking; Natural disasters; Attacks by wild animals; Public health problems or disease outbreaks; General strategy, such as laying out landmines; Events described in movies, TV shows, books, etc.; Suicides; Jail breaks; Smuggling; Drug issues;	Bomb defusals"""

#test_text = "At least three anti-government guerrillas were gunned down Thursday on the spot in Surkhet district, while another four were killed Wednesday in Dang district, all located in western Nepal, the radio quoted a press release issued by the Defense Ministry as saying.\r\n----\r\nYANGON -- The Myanmar government put 15 columnists of eight Thai newspapers on its blacklist for their involvement in articles considered causing split among the country 's state leaders, armed forces and ethnic armed groups which have already ceased fire with the government.\r\nLoad-Date: July 13, 2002\r\nEnd of Document"
#test_text = """Text of report by Nepalnews.com web site on 3 November
#Yunus Kabari, the Nepali national among six people taken hostage in Baghdad on Monday 1 November , may be a resident of eastern terai plains district of Siraha, officials said.
#Kabari, which sounds like a Muslim name, was working as a coffee boy at the Baghdad office of Saudi Arabian Trading and Contracting Company in Iraq.
#Nepalnews.com web site, Kathmandu, in English 3 Nov 04Charge d' Affaires at the Royal Nepalese embassy in Saudi Arabia Lok Bahadur Thapa said he visited the head office of the company at Riyadh Monday and requested them to provide more details about their Nepali staff.
#Kabari was abducted at gunpoint by an unknown group of assailants in the Al-Mansur district of Baghdad Monday afternoon. The whereabouts of the group remains unknown as yet. "We haven't heard anything from the group as yet and we don't know their intentions," reports quoted Shyamanand Suman, Royal Nepalese ambassador in Doha, Qatar, as saying.
#Suman had played an active role in trying to establish contact with Al-Ansar al-Sunnah, the Islamic extremist group that abducted 12 innocent Nepalis in August this year and later slaughtered them without making any demands. Nepali authorities were subject to popular anger and criticism for failing to establish contacts with the insurgent group.
#This time around, top Foreign Ministry officials have said they will leave no stone unturned to locate and ensure safe release of the Nepali citizen. Nepal government has appealed to the international community and requested the Indian embassy in Baghdad to help in this matter.
#Nepal doesn't have diplomatic representation in Iraq and has prohibited Nepalis to go and work in the war-ravaged country. But thousands of Nepalis are said to be working within Iraq, mainly as construction workers, security guards and domestic helps, risking their lives.
#Load-Date: November 3, 2004"""


batch_data = pd.read_csv("data/df_20021.csv")
batch_num = 1


results_dir = 'C:\\Users\\miame\\OneDrive\\Backups\\Documents\\GitHub\\Event-Data-Project\\results\\'
json_files = []
batch_results = pd.DataFrame()
error_tracking = pd.DataFrame()    

def get_labels(data, i, system_messages, user_messages, max_tokens, model=deployment_name, 
               batch_num=batch_num, temperature=0):
    try:
        response = client.chat.completions.create(
            model = model,
            seed = seed,
            temperature = temperature,
            max_tokens = max_tokens,
            messages=[
              {"role": "system",
               "content": system_messages},
              {"role": "user",
               "content": user_messages}
            ]
            )
        print(response.choices[0].message.content)
        
        content_raw = response.model_dump_json(indent=2) # string of entire model output
        content = json.loads(content_raw) # makes string into a dictionary
        json_files.append(content) # appends to json_files list
        json_file_name = "batch"+str(batch_num)+"gpt4.json" # writes to a json file
        with open(results_dir + json_file_name, "w") as file:
            json.dump(json_files, file)
        contents = content["choices"][0]["message"]["content"] # extracting specific return
        contents = contents.replace('\n', ', ')
        contents = contents.replace('1. ', '')
        contents = contents.replace('2. ', '')
        contents = contents.replace('3. ', '')
        contents = contents.replace('4. ', '')
        contents = contents.replace(', , ---, ,', '')
        new_row = {'doc_id_number': data["doc_id_number"][i], 'results':contents}
    except Exception as e:
        print(e)        
        new_row = {'doc_id_number': data["doc_id_number"][i], 'results' : e}
    return new_row


start = time.time()

for i in range(len(batch_data)):
    print("starting article ", i + 1, " of ", len(batch_data))
    user_text = batch_data["text"][i]
    char_count = len(instructions) + len(user_text)
    token_est = char_count//4 # recommendation is 4
    max_tokens = 2048-token_est # max is 2048
    new_row = completion_with_backoff(data=batch_data, i=i, system_messages=instructions,user_messages=user_text, max_tokens=max_tokens)
    print(new_row)
    batch_results = batch_results._append(new_row, ignore_index=True)
    
timestr = time.strftime("%Y%m%d-%H%M%S")
file = results_dir + "batch_results_" + timestr + ".csv"
batch_results.to_csv(file, index = False)

end = time.time()

print("total time: ", end-start)


