from lxml import etree
from typing import Any, Dict, List


def parse_pagexml(file_path: str) -> List[Dict[str, Any]]:
    """
    Parses a PageXML file and extracts line coordinates and transcriptions.

    Args:
        file_path (str): The path to the PageXML file.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries containing 'coords' and 'transcription' for each text line.
    """
    tree = etree.parse(file_path)
    root = tree.getroot()

    # Get the default namespace
    namespace = root.nsmap.get(None)
    ns = {"ns": namespace} if namespace else {}

    # XPath expressions with namespace prefixes
    textline_xpath = ".//ns:TextLine"
    coords_xpath = "ns:Coords"
    unicode_xpath = ".//ns:Unicode"

    lines: List[Dict[str, Any]] = []

    for textline in root.xpath(textline_xpath, namespaces=ns):
        # Get the coordinates
        coords_element = textline.find(coords_xpath, namespaces=ns)
        if coords_element is not None:
            points = coords_element.get("points")
            if points:
                coords = [
                    tuple(map(int, point.split(",")))
                    for point in points.strip().split()
                ]
            else:
                coords = []
        else:
            coords = []

        # Get the transcription
        unicode_element = textline.find(unicode_xpath, namespaces=ns)
        if unicode_element is not None and unicode_element.text:
            transcription = unicode_element.text.strip()
        else:
            transcription = ""

        lines.append({"coords": coords, "transcription": transcription})

    return lines

