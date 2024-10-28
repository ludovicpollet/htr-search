# pageXML search
## A quick and dirty solution for word-spotting in HTR noisy results.
- Built with [Whoosh](https://whoosh.readthedocs.io/) and [PySide6](https://pypi.org/project/PySide6/)
- CLI for indexing pageXML documents.
- Basic GUI for searching and displaying search results.
- Uses Whoosh's "Lucene-like" query language, with wildcards expansion and fuzzy search.
- Made with my own (specific) use case in mind. If you're looking for something full-featured, there's probably a better option.
- Should work under most recent versions of Linux and OSX, untested (but could work) under Windows.

## Installation and usage
1. Clone the repo:
```bash
git clone https://github.com/ludovicpollet/pagegui.git
```
2. Create a virtual environement and install the requirements:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```
3. Create an index in ./index_dir from the provided xml data and images samples:
```bash
python main.py --index
```
4. You can either move your data in the project folder or use other index or document directories:
```bash
python main.py --xml_dir your/xml/directory --index_dir your/index/directory
```
The parser expects pageXML formatted files with the same basename as their image counterparts, all in the same folder.

5. Consider running the following after updating the index multiple times:
```bash
python main.py --optimize-index
```
6. Start the GUI
```bash
python main.py --search
```
7. Use the search bar. 
    - "*" matches any number of any characters 
    - "?" matches one character
    - append "~" to any word to search for all matches within a Damereau-Levenshtein distance of 1
    - append "~2" for a distance of 2, "~3" for 3, etc...
    - append ~3/2 to specify a distance of 3 and a common prefix of length 2
    - you may use logical operators such as word1 OR (word2 NOT word3)
    - default operator for multiple word query is AND
    - use "word1 word2" to search for expressions
    - when making multiple word queries, mind the line breaks in the documents!

8. In the results, click on either a text line or a polygon on the image to highlight its counterpart. 



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