# -*- coding: utf-8 -*-
# NOTE: run in an environment with Python 2.7
# Must have Stanford CoreNLP installed https://stanfordnlp.github.io/CoreNLP/
import os
#import re
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


# defining file paths
input_folder = "C:\\Users\\miame\\Box\\Nepal Event Data Project\\Articles\\2002-txt"
petrarch2_path = "C:/Users/miame/OneDrive/Backups/Documents/GitHub/petrarch2/petrarch2/petrarch2.py"
output_json = "petrarch_output.json"
structured_csv = "structured_event_data.csv"


# escapes xml special characters (&, <, >, etc.) to prevent parsing errors
def escape_xml(text):
    return cgi.escape(text)

# need to create parse tree for given sentence; using Stanford CoreNLP
def generate_parse_tree(sentence):
    corenlp_path = "C:/stanford-corenlp-4.5.8/"  
    jar_path = "C:/stanford-corenlp-4.8.2/stanford-corenlp-4.8.2.jar"

    command = [
        "java", "-mx5g", "-cp", "{};{}*".format(jar_path, corenlp_path),
        "edu.stanford.nlp.pipeline.StanfordCoreNLP",
        "-annotators", "tokenize,ssplit,pos,parse",
        "-outputFormat", "xml"
    ]
    
    try:
        # using Popen with communicate() for Python 2.7
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        result, error = process.communicate(sentence.encode("utf-8"))

        if error:
            print("Stanford CoreNLP Error:", error)
            return "(S (NP (NNP Unknown)) (VP (VBD said)))"  # Fallback parse

        # Extract <parse> section
        parse_start = result.find("<parse>")
        parse_end = result.find("</parse>")

        if parse_start != -1 and parse_end != -1:
            return result[parse_start + 7: parse_end].strip()  # Extract parsed text
        else:
            return "(S (NP (NNP Unknown)) (VP (VBD said)))"  # Default fallback

    except Exception as e:
        print("Error running Stanford CoreNLP:", str(e))
        return "(S (NP (NNP Unknown)) (VP (VBD said)))"  # Fallback parse

# reads txt files, converts to Petrarch2 XML format with the parsed trees
def convert_txt_to_petrarch(input_folder):
    petrarch_input = '<Root>\n'  # XML root tag

    for idx, filename in enumerate(os.listdir(input_folder)):
        if filename.endswith(".txt"):
            file_path = os.path.join(input_folder, filename)

            with open(file_path, "r") as file:
                text = file.read().decode("utf-8", "ignore")  # needed for resolving a Python 2 error
                text = escape_xml(text)  # escape special characters

            parse_tree = generate_parse_tree(text)  # create dependency parse tree

            # format into Petrarch2 XML structure
            article_id = str(idx + 1)
            article_date = "20020101"  # default date

            petrarch_input += '''
<Sentence date="{date}" id="{id}">
    <Text>{text}</Text>
    <Parse>{parse}</Parse>
</Sentence>
'''.format(date=article_date, id=article_id, text=text, parse=parse_tree)

    petrarch_input += '\n</Root>'  # close XML root

    # save as XML file
    with open("petrarch_input.xml", "w") as f:
        f.write(petrarch_input)

    return "petrarch_input.xml"


# run Petrarch2 with XML input
def run_petrarch2(petrarch_input_xml, output_json):
    try:
        subprocess.call(["python", petrarch2_path, "batch", "-i", petrarch_input_xml, "-o", output_json])
        print("Petrarch2 completed successfully!")
    except Exception as e:
        print("Petrarch2 failed:", str(e))



# parse Petrarch2 output; output in JSON format
def parse_petrarch_output(output_json):
    if not os.path.exists(output_json):
        print("Petrarch2 did not generate an output file.")
        sys.exit(1)

    with open(output_json, "r") as f:
        data = json.load(f)

    events = []
    for sentence_id, content in data.items():
        date = content["meta"]["date"]
        for actor1, actions in content.get("events", {}).items():
            for action, targets in actions.items():
                for actor2 in targets:
                    events.append((sentence_id, date, actor1, action, actor2))

    return events

print("Converting txt articles to Petrarch2 format...")
petrarch_input_xml = convert_txt_to_petrarch(input_folder)

print("Running Petrarch2...")
run_petrarch2(petrarch_input_xml, output_json)

print("Parsing Petrarch2 output...")
structured_events = parse_petrarch_output(output_json)

# Save structured event data as CSV
df = pd.DataFrame(structured_events, columns=["ID", "Date", "Actor1", "CAMEO_Code", "Actor2"])
df.to_csv(structured_csv, index=False, encoding="utf-8")

print("Event data saved to file: {file}".format(file=structured_csv))



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



