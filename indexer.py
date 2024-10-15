import logging
import os
from typing import Any, Dict, List

from whoosh.fields import ID, TEXT, STORED, Schema
from whoosh.index import create_in, exists_in, open_dir
from whoosh.qparser import QueryParser, FuzzyTermPlugin


def create_search_index(index_dir: str, documents: List[Dict[str, Any]]) -> None:
    """
    Creates or updates a Whoosh index in the specified directory using the provided documents.
    Each document should be a dictionary with 'path' and 'content' keys.

    Args:
        index_dir (str): Directory where the Whoosh index will be stored.
        documents (List[Dict[str, Any]]): List of documents to index.
    """
    if not os.path.exists(index_dir):
        os.makedirs(index_dir)
        logging.debug(f"Created index directory '{index_dir}'.")

    schema = Schema(
        doc_path=ID(stored=True, unique=True),
        line_id=ID(stored=True, unique=True),
        content=TEXT(stored=True),
        coords=STORED,
    )
    if exists_in(index_dir):
        idx = open_dir(index_dir)
        logging.debug(f"Opened existing index in '{index_dir}' for updating.")
    else:
        idx = create_in(index_dir, schema)
        logging.debug(f"Created new index in '{index_dir}'.")

    writer = idx.writer()
    for doc in documents:
        doc_path = doc["path"]
        lines = doc["lines"]
        for id, line in enumerate(lines):
            content = line["transcription"]
            coords = line["coords"]
            line_id = f"{doc_path}_{id}"
            writer.update_document(
                doc_path=doc_path, line_id=line_id, content=content, coords=coords
            )
    writer.commit()
    logging.info(f"Indexed {len(documents)} documents.")


def search_index(index_dir: str, query_str: str) -> List[str]:
    """
    Searches the index for the given query string.
    Returns a list of document paths that match the query.

    Args:
        index_dir (str): Directory where the Whoosh index is stored.
        query_str (str): The query string to search for.

    Returns:
        List[str]: List of document paths that match the query.
    """
    if not exists_in(index_dir):
        logging.error(f"No index found in '{index_dir}'.")
        return []

    idx = open_dir(index_dir)
    qp = QueryParser("content", schema=idx.schema)
    qp.add_plugin(FuzzyTermPlugin)
    q = qp.parse(query_str)

    with idx.searcher() as searcher:
        results = searcher.search(q, limit=None, scored=True)
        logging.debug(f"Found {len(results)} results for query '{query_str}'.")
        matching_lines = []
        for hit in results:
            line = {
                'doc_path': hit['doc_path'],
                'line_id': hit['line_id'],
                'content': hit['content'],
                'coords': hit['coords'],
                'score': hit.score
            }
            matching_lines.append(line)
        return matching_lines
    
def group_lines_by_document(matching_lines):
    doc_dict = {}
    for line in matching_lines:
        doc_path = line['doc_path']
        if doc_path not in doc_dict:
            doc_dict[doc_path] = {
                'lines': [],
                'num_lines': 0
            }
        doc_dict[doc_path]['lines'].append(line)
        doc_dict[doc_path]['num_lines'] += 1
    return doc_dict
