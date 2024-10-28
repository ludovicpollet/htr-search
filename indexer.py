import hashlib
import json
import logging
import os
from typing import Any, Dict, List

from tqdm import tqdm
from whoosh.fields import ID, STORED, TEXT, Schema  # type: ignore
from whoosh.index import Index, create_in, exists_in, open_dir  # type: ignore
from whoosh.qparser import FuzzyTermPlugin, QueryParser  # type: ignore
from whoosh.query import Query  # type: ignore

from pagexml_parser import parse_pagexml


def generate_line_id(doc_path: str, coords: List[float]) -> str:
    """
    Generate a stable and unique line ID based on document path and coordinates using hashing.
    The goal is to avoid duplicate lines in the index when indexing multiple times by leveraging
    whoosh's built in update capability.

    Args:
        doc_path (str): Path of the document.
        coords (List[float]): Coordinates associated with the line.

    Returns:
        str: A unique line ID.
    """
    # Convert coordinates to a consistent string format
    coords_str: str = "_".join(map(str, coords))
    # Create a SHA-256 hash of the coordinates string
    coords_hash: str = hashlib.sha256(coords_str.encode("utf-8")).hexdigest()
    # Combine with document path to form a unique line ID
    return f"{doc_path}_{coords_hash}"


def save_index_meta(index_dir: str, meta: Dict[str, float]) -> None:
    """Save index metadata to a JSON file."""
    meta_path = os.path.join(index_dir, "index_meta.json")
    with open(meta_path, "w") as f:
        json.dump(meta, f)


def load_index_meta(index_dir: str) -> Dict[str, float]:
    """Load index metadata from a JSON file."""
    meta_path = os.path.join(index_dir, "index_meta.json")
    if os.path.exists(meta_path):
        with open(meta_path, "r") as f:
            return json.load(f)
    return {}


def open_or_create_search_index(index_dir: str) -> Index:
    """Open or create a Whoosh index in the specified directory. Will create the directory if it doesn't exist."""

    if not os.path.isdir(index_dir):
        os.makedirs(index_dir)
        logging.info(f"Created index directory '{index_dir}'.")

    schema: Schema = Schema(
        doc_path=ID(stored=True),
        line_id=ID(stored=True, unique=True),
        content=TEXT(stored=True),
        coords=STORED,  # not indexed
        image_path=STORED,
    )

    if exists_in(index_dir):
        ix: Index = open_dir(index_dir)
        logging.info(f"Opened existing index in '{index_dir}' for updating.")
    else:
        ix = create_in(index_dir, schema)
        logging.info(f"Created new index in '{index_dir}'.")

    return ix


def get_lines_from_documents(
    document_dir: str, image_dir: str | None
) -> List[Dict[str, Any]] | None:
    """Find PageXML files located in xml_dir and parse them."""

    if not os.path.isdir(document_dir):
        logging.error(
            f"XML directory '{document_dir}' does not exist or is not a directory."
        )
        return None

    if image_dir is not None and not os.path.isdir(image_dir):
        logging.error(
            f"The specified directory '{image_dir} does not exist or is not a directory."
        )
        return None

    if image_dir is None:
        image_dir = document_dir

    # Gather all XML paths
    xml_paths: List[str] = [
        os.path.join(root, file)
        for root, _dirs, files in os.walk(document_dir)
        for file in files
        if file.endswith(".xml")
    ]

    if not xml_paths:
        logging.info("No XML files found to index.")
        return None

    # Create a dict to map basenames to image paths
    image_dict: Dict[str, str] = {}
    allowed_image_extensions = {".jpg", ".jpeg", ".tif", ".tiff"}
    for root, _, files in os.walk(image_dir):
        for file in files:
            if os.path.splitext(file)[1].lower() in allowed_image_extensions:
                basename = os.path.splitext(file)[0].lower()
                image_path = os.path.join(root, file)
                if basename not in image_dict:
                    image_dict[basename] = image_path
                else:
                    logging.warning(
                        f"Multiple images found for basename '{basename}'; using the first match."
                    )

    documents: List[Dict[str, Any]] = []

    for xml_path in tqdm(xml_paths, desc="Parsing XML files", unit="file"):
        try:
            lines = parse_pagexml(xml_path)
            if lines:
                basename = os.path.splitext(os.path.basename(xml_path))[0].lower()
                image_path = image_dict.get(basename)
                if image_path is not None:
                    document = {
                        "path": xml_path,
                        "image_path": image_dict[basename],
                        "lines": lines,
                    }
                    documents.append(document)
                else:
                    logging.debug(f"No image match found for {xml_path}. Skipping it.")
            else:
                logging.debug(f"No lines found in {xml_path}. Skipping it.")
        except Exception:
            logging.exception(f"Error parsing '{xml_path}'. Skipping it.")

    return documents


def update_index(index_dir: str, document_dir: str, image_dir: str | None) -> None:
    """
    Creates or updates a Whoosh index in the specified directory using the provided documents.
    If index metadata exists in the directory, files that have not been touched after the last indexing are skipped.
    Tries to mark line

    Args:
        index_dir (str): Directory where the Whoosh index will be stored.
        documents (List[Dict[str, Any]]): List of documents to index.
    """
    ix = open_or_create_search_index(index_dir)

    documents = get_lines_from_documents(document_dir, image_dir)

    if not documents:
        logging.info("No documents to index.")
        return

    # Load existing index metadata
    meta: Dict[str, float] = load_index_meta(index_dir)
    new_meta: Dict[str, float] = {}

    new_doc_counter = 0
    skipped_doc_counter = 0
    new_line_counter = 0

    writer: Any = ix.writer()  # type: ignore
    # Add all the lines and document to the writer transaction
    for doc in tqdm(documents, desc="Indexing documents", position=0):
        doc_path = doc["path"]
        image_path = doc["image_path"]
        last_modified = os.path.getmtime(doc_path)
        if doc_path in meta and meta[doc_path] >= last_modified:
            logging.debug(f"Skipping unchanged file: {doc_path}")
            new_meta[doc_path] = meta[doc_path]
            skipped_doc_counter += 1
            continue  # Skip unchanged files

        lines = doc["lines"]
        for line in tqdm(lines, desc="Indexing lines", position=1, leave=False):
            content = line.get("transcription", "")
            coords = line.get("coords", [])

            # Generate line id from coordinates and document path
            line_id = generate_line_id(doc_path, coords)

            writer.update_document(
                doc_path=doc_path,
                line_id=line_id,
                content=content,
                coords=coords,
                image_path=image_path,
            )
            new_line_counter += 1
            logging.debug(f"Added/updated line ID: {line_id}")

        new_doc_counter += 1
        new_meta[doc_path] = last_modified
        logging.debug(f"Added/Updated file: {doc_path}")

    writer.commit()
    if new_doc_counter != 0:
        # Update metadata
        save_index_meta(index_dir, new_meta)
        logging.info(
            f"Added/Updated {new_doc_counter} documents with {new_line_counter} lines."
        )
        logging.info(f"Skipped {skipped_doc_counter} unmodified documents.")
    else:
        logging.info("No new or modified documents to index.")

    log_index_stats(index_dir)


def search_index(index_dir: str, query_str: str) -> List[Dict[str, Any]]:
    """
    Searches the index for the given query string.
    Returns a list of matching lines with their details.

    Args:
        index_dir (str): Directory where the Whoosh index is stored.
        query_str (str): The query string to search for.

    Returns:
        List[Dict[str, Any]]: List of dictionaries containing line data with highlighted content.
    """
    if not exists_in(index_dir):
        logging.error(f"No index found in '{index_dir}'.")
        return []

    ix: Any = open_dir(index_dir)
    qp: Any = QueryParser("content", schema=ix.schema)
    qp.add_plugin(FuzzyTermPlugin())
    q: Query = qp.parse(query_str)

    with ix.searcher() as searcher:
        results = searcher.search(q, limit=None, scored=True, terms=True)
        logging.debug(f"Found {len(results)} results for query '{query_str}'.")

        matching_lines: List[Dict[str, Any]] = []
        for hit in results:
            matches: list[tuple[str, bytes]] = hit.matched_terms()
            matched_terms: List[str] = [
                term.decode(encoding="utf-8") for _fieldname, term in matches
            ]
            line: Dict[str, Any] = {
                "doc_path": hit["doc_path"],
                "line_id": hit["line_id"],
                "content": hit["content"],
                "matched_terms": matched_terms,
                "coords": hit["coords"],
                "image_path": hit["image_path"],
                "score": hit.score,  # not used yet
            }
            matching_lines.append(line)
        return matching_lines


def count_documents(index_dir: str) -> int:
    ix: Any = open_dir(index_dir)
    with ix.searcher() as searcher:
        total_docs: int = searcher.doc_count()
    return total_docs


def get_index_size(index_dir: str) -> float:
    total_size = sum(
        (
            os.path.getsize(file)
            for file in os.scandir(index_dir)
            if os.path.isfile(file)
        )
    )
    return total_size / (1024**2)


def log_index_stats(index_dir: str) -> None:
    """Print out the size and line count of an index"""
    if not exists_in(index_dir):
        logging.debug(f"No index found in '{index_dir}'.")
    line_count = count_documents(index_dir)
    total_size = get_index_size(index_dir)
    logging.info(f"Total lines in index: {line_count}")
    logging.info(f"Current index size: {total_size:.2f} MB")


def optimize_index(index_dir: str) -> None:
    """
    Optimize the Whoosh index for better performance. Should be run once in a while.

    Args:
        index_dir (str): Directory where the Whoosh index is stored.
    """
    if exists_in(index_dir):
        ix: Any = open_dir(index_dir)
        ix.optimize()
        logging.info(f"Optimized index in '{index_dir}'.")
        log_index_stats(index_dir)
    else:
        logging.info(f"No index in '{index_dir}' to optimize.")


def group_lines_by_document(
    matching_lines: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """
    Groups matching lines by their document paths.

    Args:
        matching_lines (List[Dict[str, Any]]): List of matching lines with document paths.

    Returns:
        Dict[str, Dict[str, Any]]: Dictionary mapping document paths to their matching lines and counts.
    """
    doc_dict: Dict[str, Dict[str, Any]] = {}
    for line in matching_lines:
        doc_path = line["doc_path"]
        image_path = line["image_path"]
        if doc_path not in doc_dict:
            doc_dict[doc_path] = {"image_path": image_path, "lines": [], "num_lines": 0}
        doc_dict[doc_path]["lines"].append(line)
        doc_dict[doc_path]["num_lines"] += 1
    return doc_dict
