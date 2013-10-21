# -*- coding: utf-8 -*-
# Copyright 2103 Regents of the University of Minnesota
# Available under the terms of the MIT License: http://opensource.org/licenses/MIT

import requests
import json
import sys
import getopt
from urllib import urlretrieve
import os.path
import re
import string  

from jinja2 import Environment, PackageLoader
env = Environment(loader=PackageLoader('omeka2pdf', 'templates'))
template = env.get_template('deck.html')

from weasyprint import HTML, CSS

# From http://www.andrew-seaford.co.uk/generate-safe-filenames-using-python/
## Make a file name that only contains safe charaters  
# @param inputFilename A filename containing illegal characters  
# @return A filename containing only safe characters  
def makeSafeFilename(inputFilename):     
    try:  
	safechars = string.letters + string.digits + " -_."  
	return filter(lambda c: c in safechars, inputFilename).replace(" ","_")
    except:  
	return ""    
    pass  

def build_decks(api_endpoint):
    decks = {}
    root_path = os.path.join(os.path.expanduser('~'), 'omeka-temp')
    title_element = requests.get(api_endpoint + "elements?name=Title&element_set=1").json()
    title_element_id = title_element[0]['id']
    omeka_collections = requests.get(api_endpoint + "collections").json()
    for omeka_collection in omeka_collections[1:]:
        collection_name = omeka_collection['element_texts'][0]['text']
        collection_filename = os.path.join(root_path, makeSafeFilename(collection_name).lower())
        collection_tag = re.sub('[^0-9a-zA-Z]+', '*', collection_name.split(":")[0].lower().strip())
        omeka_items = requests.get(omeka_collection['items']['url']).json()
        decks[collection_name] = {"items": omeka_items}
        print decks
        if len(omeka_items) >= 1:
            deck = []
            for item in omeka_items:
                card = {'front':{}, 'back':{}}
                # Get the text of the item's 'Title' element
                item_title = [element['text'] for element in item['element_texts'] if element['element']['id'] == title_element_id][0]
                card['title'] = item_title
                print item_title
                item_files = requests.get(item['files']['url']).json()
                item_file_dict = {f['original_filename']:f for f in item_files}
                for item_file in item_files:
                    # Check to see if item is an image, and is not the annotated version of some other file
                    if ('image' in item_file['mime_type']) and ('_marked' not in item_file['original_filename']):
                        # Create a new card - a "note" in Anki terms
                        card_back = "<h3>%s</h3>" % item_title
                        
                        # If image hasn't been downloaded, fetch it
                        image_filename = os.path.join(root_path, item_file['filename'])
                        if not os.path.isfile(image_filename):
                            print "Downloading file %s" % item_file['filename']
                            file_image = urlretrieve(item_file['file_urls']['original'], image_filename)
                        card['front']['image'] = item_file['filename']
                        
                        # Look to see if there is a "_marked" version of this image
                        if "/" in item_file['original_filename']:
                            base_filename = item_file['original_filename'].rsplit("/",1)[1]
                        else:
                            base_filename = item_file['original_filename']
                        marked_filename = base_filename.replace(".jpg", "_marked.jpg")
                        
                        # If so, download the _marked file and add to the collection
                        if marked_filename in item_file_dict:
                            marked_file = item_file_dict[marked_filename]
                            marked_filename_local = os.path.join(root_path, marked_file['filename'])
                            if not os.path.isfile(marked_filename_local):
                                print "Downloading marked file %s" % marked_file['filename']
                                file_image = urlretrieve(marked_file['file_urls']['original'], marked_filename_local)
                            card['back']['image'] = marked_file['filename']
                        # If item has descriptive text, add it to the back of the card
                        if item_file['element_texts']:
                            card['back']['text'] = item_file['element_texts'][0]['text']
                deck.append(card)
                print deck
                        
            print "Generating HTML for %s" % collection_name
            deck_html = template.render(deck=deck)
            print "Writing HTML file"
            collection_file_html = open(collection_filename + ".html", "w")
            collection_file_html.write(deck_html)
            collection_file_html.close()
            print "Generating PDF"
            HTML(collection_filename + ".html").write_pdf(collection_filename + ".pdf")
            
            
def main():
    try:
        build_decks('http://archive.pathology.umn.edu/api/')
    except:
        print "Unexpected error:", sys.exc_info()[0]
        raise
            
if __name__ == "__main__":
    sys.exit(main())