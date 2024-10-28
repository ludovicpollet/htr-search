# HTR search
## A quick (and dirty) solution for word-spotting in HTR noisy results.
- Built with [Whoosh](https://whoosh.readthedocs.io/) and [PySide6](https://pypi.org/project/PySide6/)
- CLI for parsing and indexing pageXML documents.
- Basic GUI for searching and displaying search results.
- Uses Whoosh's "Lucene-like" query language, with wildcards expansion and fuzzy search.
- Made with my own (specific) use case in mind. If you're looking for something full-featured, there's probably a better option.
- Should work under most recent versions of Linux and OSX, untested (but could work) under Windows.

## Installation and usage
1. Clone the repo:
```bash
git clone https://github.com/ludovicpollet/htr-search.git
cd htr-search
```
2. Create a virtual environement and install the requirements:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```
3. Create or update an index in ./indexes/default_index from the provided sample xml data and images:
```bash
python main.py --index
```
4. To use with you own data, specify the directory where the XML files can be found. You should also name the index if you wish to index more than one dataset: 
```bash
python main.py --index --index-name NAME --xml-dir your/xml/directory
```
> The parser expects pageXML formatted files with the same basename as their image counterparts. By default, it will recursively look for XML files and matching image files in any subdirectories of the specified folder.

5. If the images are not stored in the same directory as the xml files or any of its subdirectories, you may tell the parser to look for them elsewhere:
```bash
python main.py --index --index-name NAME --xml-dir your/xml/directory --image-dir your/image/directory
```

6. Start the search GUI:
```bash
python main.py --search
# or search another index: 
python main.py --search --index-name NAME
```

7. Use the search bar. 
    - "*" matches any number of any characters 
    - "?" matches one character
    - append "~" to any word to search for all matches within a Damerau-Levenshtein distance of 1
    - append "~2" for a distance of 2, "~3" for 3, etc...
    - append ~3/2 to specify a distance of 3 and a common prefix of length 2
    - you may use logical operators such as word1 OR (word2 NOT word3)
    - default operator for multiple word query is AND
    - use "word1 word2" to search for expressions
    - when making multiple word queries, mind the line breaks in the documents!

8. In the results, click on either a text line or a polygon on the image to highlight its counterpart.

9. If you modify your files, you may update the index with the --index command used to create it. If their path hasn't changed and the segmentation has not been modified, text lines in documents that have been touched will be added and their former version marked for removal to prevent duplicates in subsequent search results. You should consider running the following after updating the index multiple times with files that have been touched.
```bash
python main.py --optimize-index
```



## To do (if I have the time, one day):
- Housekeeping :
    - Better handling of image file locations.
    - Get the last modified timestamp from the xml metadata instead of the filesystem.
    - Sort out the mess between logging and tqdm output
- Functionality
    - Implement zoom in the image widget
    - Show the search results with more context (browse the whole document)
    - Alto XML support
    - Implement region-based indexing schema to allow for multiple field search.
    - GUI option for indexing