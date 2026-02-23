import os
import pytest
import xml.etree.ElementTree as ET
from src.core.exporter import MetadataExporter, ExportableMetadata

@pytest.fixture
def temp_media(tmp_path):
    """Creates temporary media files for testing."""
    jpg_file = tmp_path / "test.jpg"
    # Create a valid-ish minimal JPEG header or just a dummy file
    # For piexif to work, it often needs a real-ish JPEG structure.
    # We'll use a very basic one or let piexif handle it.
    jpg_file.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00\x48\x00\x48\x00\x00\xff\xdb\x00\x43\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\x09\x09\x08\x0a\x0c\x14\x0d\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c\x20\x24\x2e\x27\x20\x22\x2c\x23\x1c\x1c\x28\x37\x29\x2c\x30\x31\x34\x34\x34\x1f\x27\x39\x3d\x38\x32\x3c\x2e\x33\x34\x32\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00\x37\xff\xd9")
    
    mp4_file = tmp_path / "test.mp4"
    mp4_file.write_text("dummy mp4 content")
    
    return {
        "jpg": str(jpg_file),
        "mp4": str(mp4_file)
    }

def test_export_to_xmp_sidecar(temp_media):
    meta = ExportableMetadata(
        file_path=temp_media["jpg"],
        tags=["nature", "blue"],
        character_tags=["Miku"],
        series_tags=["Vocaloid"],
        caption="A beautiful landscape"
    )
    
    xmp_path = MetadataExporter.export_to_xmp_sidecar(meta)
    
    assert os.path.exists(xmp_path)
    base, _ = os.path.splitext(temp_media["jpg"])
    assert xmp_path == base + ".xmp"
    
    # Parse XMP to verify content
    tree = ET.parse(xmp_path)
    root = tree.getroot()
    
    # Namespaces
    ns = {
        'x': 'adobe:ns:meta/',
        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
        'dc': 'http://purl.org/dc/elements/1.1/',
        'lr': 'http://ns.adobe.com/lightroom/1.0/'
    }
    
    # Check caption
    caption_elem = root.find(".//dc:description/rdf:Alt/rdf:li", ns)
    assert caption_elem is not None
    assert caption_elem.text == "A beautiful landscape"
    
    # Check subject (keywords)
    subjects = root.findall(".//dc:subject/rdf:Bag/rdf:li", ns)
    tags = [s.text for s in subjects]
    assert "nature" in tags
    assert "blue" in tags
    assert "Miku" in tags
    assert "Vocaloid" in tags
    
    # Check hierarchical subject
    hier = root.findall(".//lr:hierarchicalSubject/rdf:Bag/rdf:li", ns)
    hier_tags = [h.text for h in hier]
    assert "Character|Miku" in hier_tags
    assert "Series|Vocaloid" in hier_tags

def test_export_to_exif_jpeg(temp_media):
    meta = ExportableMetadata(
        file_path=temp_media["jpg"],
        tags=["tag1", "tag2"],
        character_tags=[],
        series_tags=[],
        caption="EXIF caption"
    )
    
    success = MetadataExporter.export_to_exif(meta)
    assert success is True
    
    # Verify using piexif
    import piexif
    exif_dict = piexif.load(temp_media["jpg"])
    
    # Check description
    assert exif_dict["0th"][piexif.ImageIFD.ImageDescription] == b"EXIF caption"
    
    # Check keywords (XPKeywords)
    # XPKeywords is stored as UTF-16LE
    val = exif_dict["0th"][0x9C9E]
    if isinstance(val, tuple):
        # Some piexif versions return it as a tuple of ints
        val = bytes(val)
    keywords = val.decode("utf-16-le").strip("\x00")
    assert "tag1" in keywords
    assert "tag2" in keywords

def test_export_exif_unsupported_format(temp_media):
    """Negative test: Attempt EXIF export on .mp4 file and verify it fails gracefully."""
    meta = ExportableMetadata(
        file_path=temp_media["mp4"],
        tags=["test"],
        character_tags=[],
        series_tags=[],
        caption="Should fail"
    )
    
    # Should return False and not crash
    success = MetadataExporter.export_to_exif(meta)
    assert success is False
    assert os.path.exists(temp_media["mp4"]) # File still exists

def test_export_batch_mixed(temp_media):
    items = [
        ExportableMetadata(
            file_path=temp_media["jpg"],
            tags=["j1"],
            character_tags=[],
            series_tags=[],
            caption="c1"
        ),
        ExportableMetadata(
            file_path=temp_media["mp4"],
            tags=["m1"],
            character_tags=[],
            series_tags=[],
            caption="c2"
        )
    ]
    
    # Mode EXIF: jpg should succeed with EXIF, mp4 should fallback to XMP
    result = MetadataExporter.export_batch(items, mode="exif")
    
    assert result["success"] == 2
    assert result["failed"] == 0
    
    # Check jpg success (doesn't create xmp if exif worked)
    base_jpg, _ = os.path.splitext(temp_media["jpg"])
    # Not necessarily creating XMP if EXIF succeeded
    
    # For mp4, export_to_exif returns False, so it should create .xmp
    base_mp4, _ = os.path.splitext(temp_media["mp4"])
    assert os.path.exists(base_mp4 + ".xmp")

