import argparse
import logging
import sys
import os.path

from PySide6.QtWidgets import QApplication

from gui import MainWindow
from indexer import optimize_index, update_index


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="A small programm with a CLI to index a corpus of pageXML documents and a simple GUI to search them.")
    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument(
        "--index", "-i", action="store_true", help="Update or create the index and exit."
    )
    action_group.add_argument(
        "--optimize-index", action="store_true", help="Optimize the index and exit."
    )
    action_group.add_argument(
        "--search", "-s", action="store_true", help="Launch the search GUI."
    )
    parser.add_argument(
        "--xml-dir",
        default="sample_data",
        help="Directory containing where the XML files and the images are stored.",
    )
    parser.add_argument(
        "--image-dir",
        help="Directory containing the images. If not provided, the program will try looking for them in the XML directory."
    )
    parser.add_argument(
        "--index-name",
        default="default_index",
        help="Name of the index to be stored, updated or searched.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output.",
    )

    return parser.parse_args()


def main():
    args = get_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    index_dir = os.path.join("indexes", args.index_name)

    if args.optimize_index:
        optimize_index(index_dir)
        sys.exit()

    if args.index:
        update_index(index_dir, args.xml_dir, args.image_dir)
        sys.exit()

    if args.search:
        app = QApplication(sys.argv)
        window = MainWindow(index_dir=index_dir)
        window.show()
        sys.exit(app.exec())

    sys.exit()


if __name__ == "__main__":
    main()
