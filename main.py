import argparse
import logging
import os
import sys
from typing import Any, Dict, List

from PySide6.QtWidgets import QApplication
from tqdm import tqdm

from gui import MainWindow
from indexer import create_search_index
from pagexml_parser import parse_pagexml


def index_pagexml_files(xml_dir: str, index_dir: str) -> None:
    """
    Index PageXML files located in xml_dir and create a search index in index_dir.

    Args:
        xml_dir (str): Directory containing XML files to index.
        index_dir (str): Directory where the search index will be stored.
    """
    if not os.path.isdir(xml_dir):
        logging.error(
            f"XML directory '{xml_dir}' does not exist or is not a directory."
        )
        return

    xml_paths = [os.path.join(root, file) for root, _dirs, files in os.walk(xml_dir) for file in files if file.endswith(".xml")]

    if not xml_paths:
        logging.info("No XML files found to index.")
        return

    documents: List[Dict[str, Any]] = []

    for xml_path in tqdm(xml_paths, desc="Indexing XML files", unit="file"):
        try:
            lines = parse_pagexml(xml_path)
            if lines:
                document = {
                    'path': xml_path,
                    'lines': lines
                }
                documents.append(document)
            else:
                logging.info(f"No lines found in '{xml_path}'")
        except Exception:
            logging.exception(f"Error parsing '{xml_path}'")

    if documents:
        create_search_index(index_dir, documents)
    else:
        logging.info("No documents to index.")


def main():
    parser = argparse.ArgumentParser(description="Index PageXML files and start GUI.")
    parser.add_argument(
        "--xml-dir",
        default="xml_dir",
        help="Directory containing XML files to index.",
    )
    parser.add_argument(
        "--index-dir",
        default="index_dir",
        help="Directory where the search index will be stored.",
    )
    parser.add_argument(
        "--skip-indexing",
        action="store_true",
        help="Skip the indexing step.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output.",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    if not args.skip_indexing:
        index_pagexml_files(args.xml_dir, args.index_dir)

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
