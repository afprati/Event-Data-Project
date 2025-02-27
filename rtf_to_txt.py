# -*- coding: utf-8 -*-
"""
Created on Wed Feb 26 16:32:49 2025

@author: miame
"""

# convert all RTF files in a folder to txt

import os
import win32com.client

# Set the folder containing RTF files
input_folder = "C:\\Users\\miame\\Box\\Nepal Event Data Project\\Articles\\2002"
output_folder = "C:\\Users\\miame\\Box\\Nepal Event Data Project\\Articles\\2002-txt"

# Ensure the output folder exists
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# Initialize Word application
word = win32com.client.Dispatch("Word.Application")
word.Visible = False  # Run Word in the background

# Loop through all RTF files in the input folder
for filename in os.listdir(input_folder):
    if filename.endswith(".rtf"):
        input_path = os.path.join(input_folder, filename)
        output_path = os.path.join(output_folder, filename.replace(".rtf", ".txt"))
        
        print(f"Converting: {filename} -> {output_path}")

        # Open the RTF file in Word
        doc = word.Documents.Open(input_path)

        # Save as plain text (FileFormat=2 means TXT format)
        doc.SaveAs(output_path, FileFormat=2)

        # Close the document
        doc.Close()

# Quit Word when done
word.Quit()

print("Conversion complete!")
