"""
Test script for the Naming Engine.

Run with: python test_naming_engine.py
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from naming_engine import (
    NamingEngine,
    NamingConfig,
    FileMetadata,
    NamingContext,
    CaseStyle,
    CollisionStrategy,
)


def test_basic_template():
    """Test basic template rendering."""
    print("Testing basic template rendering...")
    
    config = NamingConfig(template="{poster_name}_{mockup_name}")
    engine = NamingEngine(config)
    
    context = NamingContext(
        poster_name="sunset_beach",
        mockup_name="wooden_frame"
    )
    
    result = engine.render_filename(context)
    print(f"  Template: {{poster_name}}_{{mockup_name}}")
    print(f"  Result: {result}")
    assert "sunset" in result.lower() and "wooden" in result.lower(), f"Unexpected result: {result}"
    print("  ✓ PASSED\n")


def test_number_padding():
    """Test that single digits are padded to two digits."""
    print("Testing number padding (1 -> 01, 2 -> 02)...")
    
    config = NamingConfig(template="{poster_name}_{mockup_name}")
    engine = NamingEngine(config)
    
    # Test cases with single digits
    test_cases = [
        ("design_1", "kit_1", "01"),
        ("poster_3", "frame_2", "02"),
        ("art_9", "mockup_5", "05"),
        ("test_12", "frame_10", "12"),  # Should NOT pad 12 or 10
    ]
    
    for poster, mockup, expected_digit in test_cases:
        context = NamingContext(poster_name=poster, mockup_name=mockup)
        result = engine.render_filename(context)
        print(f"  {poster} + {mockup} -> {result}")
        
        if expected_digit == "12":
            # For double digits, ensure they're not padded
            assert "012" not in result, f"Double digit incorrectly padded: {result}"
        else:
            assert expected_digit in result, f"Expected {expected_digit} in {result}"
    
    print("  ✓ PASSED\n")


def test_collision_resolution():
    """Test that duplicate filenames are resolved."""
    print("Testing collision resolution...")
    
    config = NamingConfig(
        template="{poster_name}_{mockup_name}",
        collision_strategy=CollisionStrategy.SUFFIX
    )
    engine = NamingEngine(config)
    engine.reset_batch()
    
    # Generate same filename multiple times
    context = NamingContext(poster_name="design", mockup_name="frame")
    
    results = []
    for i in range(5):
        filename = engine.resolve_collision(engine.render_filename(context))
        results.append(filename)
        print(f"  Iteration {i+1}: {filename}")
    
    # All should be unique
    assert len(results) == len(set(results)), "Collision resolution failed - duplicates found!"
    print("  ✓ PASSED\n")


def test_case_styles():
    """Test different case style conversions."""
    print("Testing case style conversions...")
    
    test_input = "my_design"
    mockup = "frame_mockup"
    
    styles = [
        (CaseStyle.SNAKE, "_"),
        (CaseStyle.KEBAB, "-"),
        (CaseStyle.CAMEL, ""),
        (CaseStyle.PASCAL, ""),
    ]
    
    for style, expected_sep in styles:
        config = NamingConfig(
            template="{poster_name}_{mockup_name}",
            case_style=style
        )
        engine = NamingEngine(config)
        context = NamingContext(poster_name=test_input, mockup_name=mockup)
        result = engine.render_filename(context)
        print(f"  {style.value}: {result}")
    
    print("  ✓ PASSED\n")


def test_template_validation():
    """Test template validation."""
    print("Testing template validation...")
    
    engine = NamingEngine()
    
    # Valid template
    result = engine.validate_template("{poster_name}_{mockup_name}")
    print(f"  Valid template: {result.valid} - {result.message}")
    assert result.valid, "Valid template marked as invalid"
    
    # Invalid template with unknown placeholder
    result = engine.validate_template("{poster_name}_{unknown_field}")
    print(f"  Invalid template: {result.valid} - {result.message}")
    assert not result.valid, "Invalid template marked as valid"
    
    # Custom field should be valid
    result = engine.validate_template("{poster_name}_{custom_brand}")
    print(f"  Custom field template: {result.valid} - {result.message}")
    assert result.valid, "Custom field template marked as invalid"
    
    print("  ✓ PASSED\n")


def test_metadata_extraction():
    """Test file metadata extraction from filename."""
    print("Testing metadata extraction...")
    
    engine = NamingEngine()
    
    # Create a simple test image in memory (1x1 white pixel PNG)
    import numpy as np
    import cv2
    
    # Create a 100x200 test image
    test_img = np.ones((200, 100, 3), dtype=np.uint8) * 255
    _, buffer = cv2.imencode('.png', test_img)
    image_bytes = buffer.tobytes()
    
    metadata = engine.extract_metadata(image_bytes, "my_poster_design.png")
    
    print(f"  Filename: my_poster_design.png")
    print(f"  Base name: {metadata.base_name}")
    print(f"  Extension: {metadata.extension}")
    print(f"  Dimensions: {metadata.width}x{metadata.height}")
    print(f"  Orientation: {metadata.orientation}")
    
    assert metadata.base_name == "my_poster_design"
    assert metadata.extension == "png"
    assert metadata.width == 100
    assert metadata.height == 200
    assert metadata.orientation == "portrait"
    
    print("  ✓ PASSED\n")


def test_preview_filename():
    """Test preview filename generation."""
    print("Testing preview filename generation...")
    
    config = NamingConfig(template="{poster_name}_{mockup_name}_{size}")
    engine = NamingEngine(config)
    
    preview = engine.preview_filename(
        "{poster_name}_{mockup_name}_{size}",
        poster_name="beach_sunset",
        mockup_name="wooden_frame",
        width=1920,
        height=1080
    )
    
    print(f"  Preview: {preview}")
    assert "1920x1080" in preview or "1920" in preview
    assert ".webp" in preview
    
    print("  ✓ PASSED\n")


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("NAMING ENGINE TEST SUITE")
    print("=" * 60 + "\n")
    
    try:
        test_basic_template()
        test_number_padding()
        test_collision_resolution()
        test_case_styles()
        test_template_validation()
        test_metadata_extraction()
        test_preview_filename()
        
        print("=" * 60)
        print("ALL TESTS PASSED! ✓")
        print("=" * 60)
        return True
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
