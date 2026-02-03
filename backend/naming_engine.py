"""
Advanced Naming Engine for Mockup Generator

A flexible, modular naming system with automatic detection, customizable templates,
and robust bulk generation support.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Set, Any
from enum import Enum
import os
import re
import cv2
import numpy as np
from datetime import datetime
import hashlib


# ============================================================================
# Enums
# ============================================================================

class CaseStyle(str, Enum):
    """Supported case styles for filename output."""
    SNAKE = "snake"       # my_file_name
    KEBAB = "kebab"       # my-file-name
    CAMEL = "camel"       # myFileName
    PASCAL = "pascal"     # MyFileName
    ORIGINAL = "original" # Preserve original casing


class CollisionStrategy(str, Enum):
    """How to handle filename collisions in bulk operations."""
    SUFFIX = "suffix"         # file_001, file_002
    PREFIX = "prefix"         # 001_file, 002_file
    TIMESTAMP = "timestamp"   # file_1736455575123


# ============================================================================
# Data Models
# ============================================================================

class NamingConfig(BaseModel):
    """Configuration for the naming engine."""
    template: str = Field(
        default="{poster_name}_{mockup_name}",
        description="Naming template with placeholders"
    )
    separator: str = Field(
        default="_",
        description="Character used between name components"
    )
    case_style: CaseStyle = Field(
        default=CaseStyle.SNAKE,
        description="Case style for output filename"
    )
    max_length: int = Field(
        default=200,
        ge=20,
        le=255,
        description="Maximum filename length (excluding extension)"
    )
    collision_strategy: CollisionStrategy = Field(
        default=CollisionStrategy.SUFFIX,
        description="How to handle duplicate filenames"
    )
    output_format: str = Field(
        default="webp",
        description="Output image format extension"
    )
    custom_fields: Dict[str, str] = Field(
        default_factory=dict,
        description="Custom user-defined field values"
    )
    index_padding: int = Field(
        default=3,
        ge=1,
        le=6,
        description="Zero-padding for index numbers"
    )

    @field_validator('template')
    @classmethod
    def validate_template(cls, v: str) -> str:
        """Ensure template is not empty and has valid structure."""
        if not v or not v.strip():
            raise ValueError("Template cannot be empty")
        return v.strip()

    @field_validator('separator')
    @classmethod
    def validate_separator(cls, v: str) -> str:
        """Ensure separator is a valid filename character."""
        invalid_chars = r'<>:"/\|?*'
        if any(c in v for c in invalid_chars):
            raise ValueError(f"Separator contains invalid characters: {invalid_chars}")
        return v


class FileMetadata(BaseModel):
    """Extracted metadata from an input file."""
    original_name: str
    base_name: str
    extension: str
    width: Optional[int] = None
    height: Optional[int] = None
    orientation: Optional[str] = None  # portrait, landscape, square
    size_label: Optional[str] = None   # e.g., "1920x1080"


class NamingContext(BaseModel):
    """Context data available for template rendering."""
    poster_name: str = ""
    poster_width: Optional[int] = None
    poster_height: Optional[int] = None
    poster_orientation: Optional[str] = None
    mockup_name: str = ""
    mockup_width: Optional[int] = None
    mockup_height: Optional[int] = None
    date: str = ""
    time: str = ""
    timestamp: str = ""
    index: int = 0
    batch_id: str = ""
    custom: Dict[str, str] = Field(default_factory=dict)


class ValidationResult(BaseModel):
    """Result of template validation."""
    valid: bool
    message: str
    placeholders_found: List[str] = Field(default_factory=list)
    unknown_placeholders: List[str] = Field(default_factory=list)


# ============================================================================
# Naming Engine
# ============================================================================

class NamingEngine:
    """
    Advanced naming engine for mockup generation.
    
    Supports:
    - Automatic metadata extraction from images
    - Customizable naming templates with placeholders
    - Multiple case styles and separators
    - Collision detection and resolution for bulk operations
    - Graceful fallbacks for missing data
    """

    # All supported placeholders
    SUPPORTED_PLACEHOLDERS = {
        "poster_name": "Design/artwork filename (without extension)",
        "mockup_name": "Mockup template name (without extension)",
        "width": "Poster width in pixels",
        "height": "Poster height in pixels",
        "orientation": "Detected orientation (portrait/landscape/square)",
        "size": "Combined dimensions (e.g., 1920x1080)",
        "mockup_width": "Mockup template width",
        "mockup_height": "Mockup template height",
        "date": "Generation date (YYYY-MM-DD)",
        "time": "Generation time (HH-MM-SS)",
        "timestamp": "Unix timestamp",
        "index": "Batch index (padded)",
        "batch_id": "Unique batch identifier",
    }

    # Characters not allowed in filenames
    INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

    def __init__(self, config: Optional[NamingConfig] = None):
        """Initialize with optional configuration."""
        self.config = config or NamingConfig()
        self._generated_names: Set[str] = set()

    def reset_batch(self) -> None:
        """Reset tracking for a new batch operation."""
        self._generated_names.clear()

    def extract_metadata(self, image_content: bytes, filename: str) -> FileMetadata:
        """
        Extract metadata from an image file.
        
        Args:
            image_content: Raw bytes of the image
            filename: Original filename
            
        Returns:
            FileMetadata with extracted information
        """
        # Parse filename
        base_name = os.path.splitext(filename)[0]
        extension = os.path.splitext(filename)[1].lstrip('.')
        
        # Try to decode image and get dimensions
        width = None
        height = None
        orientation = None
        size_label = None
        
        try:
            nparr = np.frombuffer(image_content, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is not None:
                height, width = img.shape[:2]
                size_label = f"{width}x{height}"
                
                # Determine orientation
                if width > height:
                    orientation = "landscape"
                elif height > width:
                    orientation = "portrait"
                else:
                    orientation = "square"
        except Exception:
            pass  # Graceful fallback - leave as None
        
        return FileMetadata(
            original_name=filename,
            base_name=base_name,
            extension=extension,
            width=width,
            height=height,
            orientation=orientation,
            size_label=size_label
        )

    def extract_mockup_metadata(self, mockup_path: str, mockup_name: str) -> FileMetadata:
        """
        Extract metadata from a mockup template file on disk.
        
        Args:
            mockup_path: Path to the mockup image file
            mockup_name: Name of the mockup
            
        Returns:
            FileMetadata with extracted information
        """
        base_name = os.path.splitext(mockup_name)[0]
        extension = os.path.splitext(mockup_name)[1].lstrip('.')
        
        width = None
        height = None
        orientation = None
        size_label = None
        
        try:
            img = cv2.imread(mockup_path)
            if img is not None:
                height, width = img.shape[:2]
                size_label = f"{width}x{height}"
                
                if width > height:
                    orientation = "landscape"
                elif height > width:
                    orientation = "portrait"
                else:
                    orientation = "square"
        except Exception:
            pass
        
        return FileMetadata(
            original_name=mockup_name,
            base_name=base_name,
            extension=extension,
            width=width,
            height=height,
            orientation=orientation,
            size_label=size_label
        )

    def build_context(
        self,
        poster_metadata: FileMetadata,
        mockup_metadata: FileMetadata,
        batch_index: int = 0,
        batch_id: Optional[str] = None
    ) -> NamingContext:
        """
        Build a naming context from metadata.
        
        Args:
            poster_metadata: Metadata from the poster/design
            mockup_metadata: Metadata from the mockup template
            batch_index: Index in batch (0-based)
            batch_id: Optional batch identifier
            
        Returns:
            NamingContext ready for template rendering
        """
        now = datetime.now()
        
        return NamingContext(
            poster_name=poster_metadata.base_name,
            poster_width=poster_metadata.width,
            poster_height=poster_metadata.height,
            poster_orientation=poster_metadata.orientation,
            mockup_name=mockup_metadata.base_name,
            mockup_width=mockup_metadata.width,
            mockup_height=mockup_metadata.height,
            date=now.strftime("%Y-%m-%d"),
            time=now.strftime("%H-%M-%S"),
            timestamp=str(int(now.timestamp())),
            index=batch_index,
            batch_id=batch_id or self._generate_batch_id(),
            custom=self.config.custom_fields
        )

    def _generate_batch_id(self, length: int = 6) -> str:
        """Generate a short unique batch identifier."""
        return hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:length]

    def validate_template(self, template: str) -> ValidationResult:
        """
        Validate a naming template.
        
        Args:
            template: Template string to validate
            
        Returns:
            ValidationResult with validation status and details
        """
        if not template or not template.strip():
            return ValidationResult(
                valid=False,
                message="Template cannot be empty"
            )
        
        # Find all placeholders
        placeholder_pattern = re.compile(r'\{([^}]+)\}')
        found_placeholders = placeholder_pattern.findall(template)
        
        # Check for unknown placeholders
        unknown = []
        for p in found_placeholders:
            # Check standard placeholders
            if p in self.SUPPORTED_PLACEHOLDERS:
                continue
            # Check custom_* pattern
            if p.startswith("custom_"):
                continue
            unknown.append(p)
        
        if unknown:
            return ValidationResult(
                valid=False,
                message=f"Unknown placeholders: {', '.join(unknown)}",
                placeholders_found=found_placeholders,
                unknown_placeholders=unknown
            )
        
        return ValidationResult(
            valid=True,
            message="Template is valid",
            placeholders_found=found_placeholders
        )

    def _extract_placeholders(self, template: str) -> List[str]:
        """Extract all placeholder names from a template."""
        return re.findall(r'\{([^}]+)\}', template)

    def _apply_case_style(self, text: str, style: CaseStyle) -> str:
        """
        Apply case style transformation to text.
        
        Args:
            text: Input text
            style: Target case style
            
        Returns:
            Transformed text
        """
        if style == CaseStyle.ORIGINAL:
            return text
        
        # First, normalize to space-separated words
        # Replace common separators with spaces
        normalized = re.sub(r'[-_\s]+', ' ', text)
        # Split camelCase
        normalized = re.sub(r'([a-z])([A-Z])', r'\1 \2', normalized)
        words = normalized.lower().split()
        
        if not words:
            return text
        
        if style == CaseStyle.SNAKE:
            return '_'.join(words)
        elif style == CaseStyle.KEBAB:
            return '-'.join(words)
        elif style == CaseStyle.CAMEL:
            return words[0] + ''.join(w.capitalize() for w in words[1:])
        elif style == CaseStyle.PASCAL:
            return ''.join(w.capitalize() for w in words)
        
        return text

    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize a filename by removing invalid characters.
        
        Args:
            filename: Raw filename
            
        Returns:
            Sanitized filename safe for filesystem
        """
        # Remove invalid characters
        sanitized = self.INVALID_FILENAME_CHARS.sub('', filename)
        # Pad single-digit numbers (1 -> 01, 2 -> 02, etc.)
        sanitized = self._pad_numbers(sanitized)
        # Collapse multiple separators
        sanitized = re.sub(r'[-_\s]{2,}', self.config.separator, sanitized)
        # Remove leading/trailing separators
        sanitized = sanitized.strip('-_ ')
        # Truncate if too long
        if len(sanitized) > self.config.max_length:
            sanitized = sanitized[:self.config.max_length]
        # Ensure not empty
        if not sanitized:
            sanitized = "unnamed"
        
        return sanitized

    def _pad_numbers(self, text: str) -> str:
        """
        Pad single-digit numbers to two digits.
        
        Converts patterns like "kit 1", "frame2", "mockup_3" to
        "kit 01", "frame02", "mockup_03".
        
        Args:
            text: Input text
            
        Returns:
            Text with padded numbers
        """
        # Match single digits that are either:
        # - at word boundaries (e.g., "kit 1" or "frame_1")
        # - at the end of text
        # But NOT part of larger numbers (e.g., "12" should stay "12")
        def pad_match(match):
            prefix = match.group(1) or ''
            digit = match.group(2)
            suffix = match.group(3) or ''
            return f"{prefix}0{digit}{suffix}"
        
        # Pattern: captures optional separator, single digit, optional separator
        # Only matches single digits not adjacent to other digits
        pattern = r'([-_\s]?)(?<!\d)(\d)(?!\d)([-_\s]?)'
        return re.sub(pattern, pad_match, text)

    def render_filename(
        self,
        context: NamingContext,
        template: Optional[str] = None
    ) -> str:
        """
        Render a filename from template and context.
        
        Args:
            context: NamingContext with all available data
            template: Optional override template
            
        Returns:
            Rendered filename (without extension)
        """
        tmpl = template or self.config.template
        result = tmpl
        
        # Build replacement dictionary
        replacements = {
            "poster_name": context.poster_name or "design",
            "mockup_name": context.mockup_name or "mockup",
            "width": str(context.poster_width) if context.poster_width else "",
            "height": str(context.poster_height) if context.poster_height else "",
            "orientation": context.poster_orientation or "",
            "size": f"{context.poster_width}x{context.poster_height}" if context.poster_width and context.poster_height else "",
            "mockup_width": str(context.mockup_width) if context.mockup_width else "",
            "mockup_height": str(context.mockup_height) if context.mockup_height else "",
            "date": context.date,
            "time": context.time,
            "timestamp": context.timestamp,
            "index": str(context.index).zfill(self.config.index_padding),
            "batch_id": context.batch_id,
        }
        
        # Add custom fields
        for key, value in context.custom.items():
            replacements[f"custom_{key}"] = value
        
        # Perform replacements
        for placeholder in self._extract_placeholders(tmpl):
            value = replacements.get(placeholder, "")
            # Remove placeholder if value is empty (with surrounding separators)
            if not value:
                # Try to cleanly remove empty placeholders
                result = re.sub(r'[-_]*\{' + placeholder + r'\}[-_]*', '', result)
            else:
                result = result.replace(f'{{{placeholder}}}', value)
        
        # Apply case style
        result = self._apply_case_style(result, self.config.case_style)
        
        # Sanitize
        result = self._sanitize_filename(result)
        
        return result

    def resolve_collision(self, filename: str) -> str:
        """
        Resolve filename collision within current batch.
        
        Args:
            filename: Proposed filename (without extension)
            
        Returns:
            Unique filename
        """
        full_name = f"{filename}.{self.config.output_format}"
        
        if full_name not in self._generated_names:
            self._generated_names.add(full_name)
            return full_name
        
        # Apply collision strategy
        base = filename
        counter = 1
        
        while True:
            if self.config.collision_strategy == CollisionStrategy.SUFFIX:
                new_name = f"{base}{self.config.separator}{str(counter).zfill(self.config.index_padding)}"
            elif self.config.collision_strategy == CollisionStrategy.PREFIX:
                new_name = f"{str(counter).zfill(self.config.index_padding)}{self.config.separator}{base}"
            else:  # TIMESTAMP
                new_name = f"{base}{self.config.separator}{int(datetime.now().timestamp() * 1000)}"
            
            full_new = f"{new_name}.{self.config.output_format}"
            
            if full_new not in self._generated_names:
                self._generated_names.add(full_new)
                return full_new
            
            counter += 1
            if counter > 9999:  # Safety limit
                raise ValueError("Too many filename collisions")

    def generate_filename(
        self,
        poster_content: bytes,
        poster_filename: str,
        mockup_path: str,
        mockup_name: str,
        batch_index: int = 0,
        batch_id: Optional[str] = None,
        template: Optional[str] = None
    ) -> str:
        """
        Complete filename generation pipeline.
        
        Args:
            poster_content: Raw bytes of the poster image
            poster_filename: Original poster filename
            mockup_path: Path to mockup template on disk
            mockup_name: Mockup template name
            batch_index: Index in batch (0-based)
            batch_id: Optional batch identifier
            template: Optional template override
            
        Returns:
            Final unique filename with extension
        """
        # Extract metadata
        poster_meta = self.extract_metadata(poster_content, poster_filename)
        mockup_meta = self.extract_mockup_metadata(mockup_path, mockup_name)
        
        # Build context
        context = self.build_context(
            poster_meta,
            mockup_meta,
            batch_index,
            batch_id
        )
        
        # Render filename
        base_name = self.render_filename(context, template)
        
        # Resolve collisions
        final_name = self.resolve_collision(base_name)
        
        return final_name

    def get_available_placeholders(self) -> Dict[str, str]:
        """Return dictionary of all available placeholders and descriptions."""
        placeholders = dict(self.SUPPORTED_PLACEHOLDERS)
        # Add any custom fields as placeholders
        for key in self.config.custom_fields:
            placeholders[f"custom_{key}"] = f"Custom field: {key}"
        return placeholders

    def preview_filename(
        self,
        template: str,
        poster_name: str = "my_poster",
        mockup_name: str = "frame_mockup",
        width: int = 1920,
        height: int = 1080
    ) -> str:
        """
        Generate a preview filename for UI display.
        
        Args:
            template: Template to preview
            poster_name: Example poster name
            mockup_name: Example mockup name
            width: Example width
            height: Example height
            
        Returns:
            Example rendered filename
        """
        context = NamingContext(
            poster_name=poster_name,
            poster_width=width,
            poster_height=height,
            poster_orientation="landscape" if width > height else "portrait",
            mockup_name=mockup_name,
            date=datetime.now().strftime("%Y-%m-%d"),
            time=datetime.now().strftime("%H-%M-%S"),
            timestamp=str(int(datetime.now().timestamp())),
            index=1,
            batch_id="abc123",
            custom=self.config.custom_fields
        )
        
        base = self.render_filename(context, template)
        return f"{base}.{self.config.output_format}"


# ============================================================================
# Config Storage
# ============================================================================

def load_naming_config(config_path: str) -> NamingConfig:
    """Load naming configuration from JSON file."""
    import json
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                data = json.load(f)
                return NamingConfig(**data)
        except Exception:
            pass
    return NamingConfig()


def save_naming_config(config: NamingConfig, config_path: str) -> None:
    """Save naming configuration to JSON file."""
    import json
    with open(config_path, 'w') as f:
        json.dump(config.model_dump(), f, indent=2)
