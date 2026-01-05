"""
Image Hash Utility for Duplicate Detection
Uses perceptual hashing to detect similar images
"""
from PIL import Image
import imagehash
from pathlib import Path
from typing import Optional
import io
import base64


def calculate_image_hash(image_path: str) -> str:
    """
    Calculate perceptual hash of an image

    Args:
        image_path: Path to image file or base64 string

    Returns:
        hex string of image hash (16 characters)
    """
    try:
        # Handle base64 images
        if isinstance(image_path, str) and image_path.startswith('data:image'):
            # Extract base64 data
            header, encoded = image_path.split(',', 1)
            image_data = base64.b64decode(encoded)
            image = Image.open(io.BytesIO(image_data))
        else:
            # Handle file path
            image = Image.open(image_path)

        # Calculate perceptual hash (average hash)
        # This detects similar images even if resized, compressed, or slightly edited
        phash = imagehash.average_hash(image, hash_size=8)

        return str(phash)

    except Exception as e:
        print(f"Error calculating image hash: {e}")
        return None


def calculate_image_hash_from_bytes(image_bytes: bytes) -> str:
    """
    Calculate hash from image bytes

    Args:
        image_bytes: Raw image bytes

    Returns:
        hex string of image hash
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))
        phash = imagehash.average_hash(image, hash_size=8)
        return str(phash)
    except Exception as e:
        print(f"Error calculating image hash from bytes: {e}")
        return None


def are_images_similar(hash1: str, hash2: str, threshold: int = 5) -> bool:
    """
    Check if two image hashes are similar

    Args:
        hash1: First image hash
        hash2: Second image hash
        threshold: Maximum Hamming distance (0-64, lower = more strict)
                  0 = identical, 5 = very similar, 10 = similar, 20+ = different

    Returns:
        True if images are similar
    """
    if not hash1 or not hash2:
        return False

    try:
        h1 = imagehash.hex_to_hash(hash1)
        h2 = imagehash.hex_to_hash(hash2)

        # Calculate Hamming distance (number of different bits)
        distance = h1 - h2

        return distance <= threshold

    except Exception as e:
        print(f"Error comparing hashes: {e}")
        return False


def get_hash_similarity_score(hash1: str, hash2: str) -> Optional[int]:
    """
    Get similarity score between two hashes

    Args:
        hash1: First image hash
        hash2: Second image hash

    Returns:
        Hamming distance (0 = identical, higher = more different)
    """
    if not hash1 or not hash2:
        return None

    try:
        h1 = imagehash.hex_to_hash(hash1)
        h2 = imagehash.hex_to_hash(hash2)
        return h1 - h2
    except Exception as e:
        print(f"Error calculating similarity: {e}")
        return None