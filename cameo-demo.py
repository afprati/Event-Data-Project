# -*- coding: utf-8 -*-
# NOTE: run in an environment with Python 2.7
# Must have Stanford CoreNLP installed https://stanfordnlp.github.io/CoreNLP/
import os
import pandas as pd
#import geopandas as gpd # if using a shapefile for place names
#import spacy
#from fuzzywuzzy import process # for fuzzy matching
#from shapely.geometry import Point
#from tqdm import tqdm # ended up using stanford core nlp instead
#import pyth
#import os
import json
import subprocess
import sys
import cgi # to fix special characters in the text
import re
import xml.etree.ElementTree as ET
from datetime import datetime
import requests
import time

print("Starting script")
# defining file paths
input_folder = "C:\\Users\\miame\\Box\\Nepal Event Data Project\\Articles\\2002-txt"
petrarch2_path = "C:/Users/miame/OneDrive/Backups/Documents/GitHub/petrarch2/petrarch2/petrarch2.py"
output_json = "petrarch_output.json"
structured_csv = "structured_event_data.csv"

# Stanford CoreNLP server settings
corenlp_url = "http://localhost:9000"  # Default CoreNLP server URL
corenlp_timeout = 30000  # 30 seconds timeout

# Start CoreNLP server if not already running
def start_corenlp_server():
    print("Checking if CoreNLP server is running...")
    try:
        response = requests.get(corenlp_url)
        if response.status_code == 200:
            print("CoreNLP server is already running")
            return True
    except:
        print("CoreNLP server not detected, attempting to start...")
    
    # Update with your CoreNLP directory
    corenlp_dir = "C:/stanford-corenlp-full-2018-01-31"  # Update this to your path
    try:
        subprocess.Popen(
            "cd {0} && java -mx4g -cp \"*\" edu.stanford.nlp.pipeline.StanfordCoreNLPServer -port 9000".format(corenlp_dir),
            shell=True
        )
        # Wait for server to start
        time.sleep(10)
        return True
    except Exception as e:
        print("Failed to start CoreNLP server: {0}".format(str(e)))
        return False

# Get parse tree from CoreNLP
def get_parse_tree(text):
    """Gets a parse tree from Stanford CoreNLP."""
    try:
        # CoreNLP API parameters
        params = {
            'properties': json.dumps({
                'annotators': 'parse',
                'outputFormat': 'json',
                'timeout': corenlp_timeout
            })
        }
        
        # Send request to CoreNLP server
        response = requests.post(
            "{0}/?properties={{\"annotators\":\"parse\",\"outputFormat\":\"json\",\"timeout\":{1}}}".format(
                corenlp_url, corenlp_timeout),
            data=text.encode('utf-8'),
            headers={'Content-Type': 'text/plain; charset=utf-8'}
        )
        
        if response.status_code == 200:
            result = response.json()
            # Extract the parse tree from the first sentence
            if 'sentences' in result and len(result['sentences']) > 0:
                return result['sentences'][0]['parse']
            else:
                print("No parse tree found in CoreNLP response")
        else:
            print("CoreNLP request failed with status code {0}".format(response.status_code))
    except Exception as e:
        print("Error getting parse tree: {0}".format(str(e)))
    
    # Return default parse if anything fails
    return "(S (NP (NNP Placeholder)) (VP (VBD said)))"


# escapes xml special characters (&, <, >, etc.) to prevent parsing errors
def clean_text(text):
    """Cleans article text by removing metadata, multiple newlines, and extra symbols."""
    text = text.strip()  # Remove leading/trailing spaces & newlines
    text = re.sub(r"^Adv\d+[-\d;]*\s*", "", text)  # Remove 'Adv22-24;' at start
    text = re.sub(r"^\d+\s*", "", text)  # Remove leading numbers
    text = re.sub(r"Copyright.*?\n", "", text)  # Remove copyright notices
    text = re.sub(r"Load-Date:.*?\n", "", text)  # Remove load-date metadata
    text = re.sub(r"End of Document.*?\n", "", text)  # Remove "End of Document" lines
    text = re.sub(r"Section:.*?\n", "", text)  # Remove section info
    text = re.sub(r"Byline:.*?\n", "", text)  # Remove bylines
    text = re.sub(r"Page \d+ of \d+\n", "", text)  # Remove page numbers
    text = re.sub(r"^\s*[\w\s\.\-\']+(\n\s*)?$", "", text, flags=re.MULTILINE)  # Remove stray author names
    text = re.sub(r"\n+", " ", text)  # Replace multiple newlines with space
    text = text.lstrip("$0123456789-;:,")  # Remove unwanted symbols at the start
    return cgi.escape(text)  # Escape XML characters

def extract_date(text):
    """Extracts the first date found in the text in YYYYMMDD format."""
    date_pattern = r"([A-Za-z]+ \d{1,2}, \d{4})"  # Matches "February 11, 2002"
    match = re.search(date_pattern, text)

    if match:
        try:
            extracted_date = match.group(1)
            formatted_date = datetime.strptime(extracted_date, "%B %d, %Y").strftime("%Y%m%d")
            return formatted_date
        except ValueError:
            return "20020101"  # Default if conversion fails
    return "20020101"  # Default if no date found

def convert_txt_to_petrarch(input_folder):
    """Converts text files to PETRARCH XML format with CoreNLP parsing."""
    print("Starting CoreNLP server and preparing PETRARCH input...")
    start_corenlp_server()
    
    petrarch_input = "<ROOT>\n"  # Note: PETRARCH expects uppercase ROOT

    for idx, filename in enumerate(os.listdir(input_folder)):
        if filename.endswith(".txt"):
            file_path = os.path.join(input_folder, filename)
            print("Processing file {0}: {1}".format(idx+1, filename))

            try:
                with open(file_path, "r") as file:
                    raw_text = file.read()

                clean_article_text = clean_text(raw_text)
                article_date = extract_date(raw_text)
                article_id = str(idx + 1)
                
                # Split text into sentences (simplified)
                sentences = re.split(r'(?<=[.!?])\s+', clean_article_text)
                
                # Add each sentence separately (PETRARCH works better with individual sentences)
                for sent_idx, sentence in enumerate(sentences[:10]):  # Limit to first 10 sentences for testing
                    if len(sentence.strip()) < 10:  # Skip very short sentences
                        continue
                        
                    sent_id = "{0}_{1}".format(article_id, sent_idx)
                    
                    # Get parse tree from CoreNLP
                    parse_tree = get_parse_tree(sentence)
                    
                    # Escape the parse tree for XML
                    parse_tree = cgi.escape(parse_tree)
                    
                    # Use old-style string formatting for Python 2.7
                    petrarch_input += '''
<STORY id="{0}" date="{1}">
    <SENTENCE id="{2}">
        <TEXT>{3}</TEXT>
        <PARSE>{4}</PARSE>
    </SENTENCE>
</STORY>
'''.format(article_id, article_date, sent_id, sentence, parse_tree)
            except Exception as e:
                print("Error processing file {0}: {1}".format(filename, str(e)))
                continue

    petrarch_input += "\n</ROOT>"
    
    # Save as XML file
    with open("petrarch_input.xml", "w") as f:
        f.write(petrarch_input)
    print("XML file created successfully")
    return "petrarch_input.xml"

# run Petrarch2 with XML input
def run_petrarch2(petrarch_input_xml, output_json):
    try:
        cmd = ["python", petrarch2_path, 
               "-i", petrarch_input_xml, 
               "-o", output_json]
        
        print("Running command: " + " ".join(cmd))
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        print("Petrarch2 output: {0}".format(output.decode('utf-8')))
    except subprocess.CalledProcessError as e:
        print("Petrarch2 failed with error code: {0}".format(e.returncode))
        print("Error output: {0}".format(e.output.decode('utf-8')))
    except Exception as e:
        print("Petrarch2 failed: {0}".format(str(e)))

# parse Petrarch2 output; output in JSON format
def parse_petrarch_output(output_json):
    """Parses PETRARCH2 JSON output into structured events."""
    if not os.path.exists(output_json):
        print("Petrarch2 did not generate an output file.")
        return []

    try:
        with open(output_json, "r") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        print("Error: Could not parse JSON output from PETRARCH2")
        return []

    events = []
    for sentence_id, content in data.items():
        try:
            date = content.get("meta", {}).get("date", "")
            
            # Handle newer and older PETRARCH output formats
            event_dict = content.get("events", {})
            if not event_dict:
                print("No events found for sentence {0}".format(sentence_id))
                continue
                
            for actor1, actions in event_dict.items():
                for action, targets in actions.items():
                    for actor2 in targets:
                        events.append((sentence_id, date, actor1, action, actor2))
        except Exception as e:
            print("Error parsing event for sentence {0}: {1}".format(sentence_id, str(e)))
            continue

    return events

# Main execution
if __name__ == "__main__":
    print("Converting txt articles to Petrarch2 format...")
    petrarch_input_xml = convert_txt_to_petrarch(input_folder)

    try:
        tree = ET.parse(petrarch_input_xml)
        print("XML is well-formed!")
    except ET.ParseError as e:
        print("XML Error:", e)
        # Print problematic lines
        with open(petrarch_input_xml, "r") as f:
            lines = f.readlines()
            line_number = e.position[0]
            print("Error near line {0}:".format(line_number))
            for i in range(max(0, line_number-5), min(len(lines), line_number+5)):
                print("{0}: {1}".format(i+1, lines[i].strip()))
        sys.exit(1)
    
    print("Debugging XML before Petrarch2:")
    with open(petrarch_input_xml, "r") as f:
        for _ in range(10):  # Print first 10 lines
            print(f.readline().strip())

    print("Running Petrarch2...")
    run_petrarch2(petrarch_input_xml, output_json)

    print("Parsing Petrarch2 output...")
    structured_events = parse_petrarch_output(output_json)

    if structured_events:
        # Save structured event data as CSV
        df = pd.DataFrame(structured_events, columns=["ID", "Date", "Actor1", "CAMEO_Code", "Actor2"])
        df.to_csv(structured_csv, index=False, encoding="utf-8")
        print("Event data saved to file: {0}".format(structured_csv))
        print("Total events extracted: {0}".format(len(structured_events)))
    else:
        print("No events were extracted. Check the Petrarch2 output for errors.")



#nlp = spacy.load("en_core_web_sm")

# creating place dictionary from shapefile
#shapefile_path = "C:/Users/miame/OneDrive/WashU/Fifth Year/Nepal Event Data Project/gadm41_NPL_shp/gadm41_NPL_4.shp"
#gdf = gpd.read_file(shapefile_path)
#place_dict = {}
#for _, row in gdf.iterrows():
#    district = row["NAME_3"]
#    village = row["NAME_4"]
#    geometry = row["geometry"]  
#    if pd.notna(village):  # if village exists, store it
#        place_dict[village.lower()] = geometry
#    elif pd.notna(district):  # if no village, store the district
#        place_dict[district.lower()] = geometry


# finding closest place name w fuzzy matching
#def find_closest_place(extracted_place):
#    if extracted_place.lower() in place_dict:
#        return extracted_place, place_dict[extracted_place.lower()]  # Exact match
#    closest_match, score = process.extractOne(extracted_place, place_dict.keys())
#    return (closest_match, place_dict[closest_match]) if score > 80 else ("Unknown", None)



