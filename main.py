import argparse
import logging
import sys

from PySide6.QtWidgets import QApplication

from gui import MainWindow
from indexer import optimize_index, update_index


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Index PageXML files and start GUI.")
    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument(
        "--index", "-i", action="store_true", help="Update or create the index."
    )
    action_group.add_argument(
        "--optimize-index", action="store_true", help="Optimize the index and exit."
    )
    action_group.add_argument(
        "--search", "-s", action="store_true", help="Launch the search GUI."
    )
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

    if args.optimize_index:
        optimize_index(args.index_dir)
        sys.exit()

    if args.index:
        update_index(args.index_dir, args.xml_dir)
        sys.exit()

    if args.search:
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        sys.exit(app.exec())

    sys.exit()


if __name__ == "__main__":
    main()
