# argus/utils/yaml_loader.py
"""
YAML Loading Utilities for ARGUS.

This module provides utilities for loading YAML content from various sources:
    - Filesystem paths (user-provided configuration files)
    - Package resources (bundled defaults shipped with ARGUS)
    - Raw strings or bytes (useful for testing)

Architecture:
    All loading functions delegate to a single parse_yaml_to_dict() function
    that handles parsing and structural validation. This ensures consistent
    error handling and messaging regardless of the YAML source.

    ┌─────────────────────┐     ┌─────────────────────────────┐
    │ load_yaml_from_path │────▶│                             │
    └─────────────────────┘     │                             │
                                │   parse_yaml_to_dict()      │
    ┌─────────────────────────┐ │   (parsing + validation)    │
    │ load_yaml_from_package_ │▶│                             │
    │ resource                │ │                             │
    └─────────────────────────┘ └─────────────────────────────┘

Design Notes:
    - Uses binary mode ('rb') for file I/O; yaml.safe_load handles decoding
    - All functions require a source description for clear error messages
    - Validation ensures YAML root is always a non-empty dictionary
    - Tilde expansion (~) is handled automatically for filesystem paths
"""

import logging
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Any, Final, Protocol, TypeVar, cast

import yaml

__all__: list[str] = [
    'DEFAULT_RESOURCE_PACKAGE',
    'load_yaml_from_package_resource',
    'load_yaml_from_path',
    'parse_yaml_to_dict',
]

logger: logging.Logger = logging.getLogger(__name__)

# Default package name for ARGUS bundled resources.
DEFAULT_RESOURCE_PACKAGE: Final[str] = 'argus'

# -----------------------------------------------------------------------------
# Type Definitions for YAML Sources
# -----------------------------------------------------------------------------
# PyYAML's safe_load accepts strings, bytes, or file-like objects with a
# read() method. However, the type stubs use a generic SupportsRead[T]
# protocol that is parameterized by return type (str or bytes).
#
# We define our own Protocol to match PyYAML's expectations and handle the
# zoo of file-like types: IO[bytes], IO[str], BytesIO, StringIO, and
# importlib.resources Traversable handles—none of which share a common
# base class that type checkers recognize.
# -----------------------------------------------------------------------------

# TypeVar constrained to str or bytes (not a union).
# Covariant because it appears only in return position (output).
_ReadContentType_co = TypeVar('_ReadContentType_co', str, bytes, covariant=True)


class SupportsRead(Protocol[_ReadContentType_co]):
    """
    Protocol for file-like objects that support reading.

    This generic protocol defines the minimal interface required by
    yaml.safe_load(): an object with a read() method. The type parameter
    indicates whether the stream returns str (text mode) or bytes
    (binary mode).

    Type Parameters:
        _ReadContentType_co: The type returned by read()—either str or bytes.
            This is covariant (output position only), meaning:
            - SupportsRead[str] for text-mode files (open('r'))
            - SupportsRead[bytes] for binary-mode files (open('rb'))

    Why Generic?:
        PyYAML's type stubs define separate protocols for text and binary
        streams. A non-generic protocol returning `str | bytes` doesn't
        satisfy either. By making this generic, we correctly model that
        a specific file handle returns ONE type, not a union.

    Compatibility:
        Satisfied by all standard file-like objects:
        - open('file.yaml', 'rb')      -> IO[bytes]    -> SupportsRead[bytes]
        - open('file.yaml', 'r')       -> IO[str]      -> SupportsRead[str]
        - io.BytesIO(b'data')          -> BytesIO      -> SupportsRead[bytes]
        - io.StringIO('data')          -> StringIO     -> SupportsRead[str]
        - Traversable.open('rb')       -> BufferedReader -> SupportsRead[bytes]
    """

    def read(self, length: int = -1, /) -> _ReadContentType_co:
        """
        Read and return up to length bytes or characters from the stream.

        Args:
            length: Maximum number of bytes/characters to read. If -1 or
                omitted, read until EOF. Positional-only to match the
                standard file protocol signature.

        Returns:
            Content read from the stream. Type matches the stream mode:
            bytes for binary streams, str for text streams.
        """
        ...


# Union of all types accepted by yaml.safe_load().
# Explicitly lists both SupportsRead variants to satisfy PyYAML's type stubs.
type YamlSource = str | bytes | SupportsRead[str] | SupportsRead[bytes]


def parse_yaml_to_dict(
    yaml_source: YamlSource,
    source_description: str,
) -> dict[str, Any]:
    """
    Parse YAML content and validate it is a non-empty dictionary with string keys.

    This is the core parsing utility that all higher-level loading functions
    delegate to. It ensures consistent parsing behavior and error messaging
    across all YAML loading paths in ARGUS.

    Validation Rules:
        1. Content must parse successfully (valid YAML syntax)
        2. Parsed result must not be None (empty file / comments only)
        3. Parsed result must be a dictionary (not list or scalar)
        4. Dictionary must contain at least one key (not empty {})
        5. All top-level keys must be strings (not int, bool, etc.)

    Args:
        yaml_source: The YAML content to parse. Accepts:
            - str: YAML as a string (common for testing)
            - bytes: Raw YAML bytes (from binary file reads)
            - SupportsRead[str]: Text-mode file-like object
            - SupportsRead[bytes]: Binary-mode file-like object
        source_description: Human-readable description of where the YAML
            came from. Used in error messages and logging to help developers
            quickly identify which file or resource failed. Examples:
            - "/home/user/.argus/policy.yaml"
            - "argus/defaults/policy.yaml"
            - "PolicyConfig YAML string"

    Returns:
        Parsed YAML content as a dictionary with string keys. Guaranteed to
        be non-empty (contains at least one key).

    Raises:
        yaml.YAMLError: If the YAML syntax is invalid. The exception
            message includes line/column information from PyYAML.
        ValueError: If the YAML content is empty (parses to None) or
            parses to an empty dictionary (no keys). Either case indicates
            a configuration file with no actual settings.
        TypeError: If the YAML root element is not a dictionary, or if
            any top-level key is not a string.

    Example:
        >>> # From a string (testing)
        >>> data = parse_yaml_to_dict(
        ...     'threshold: 3.0\\nenabled: true',
        ...     source_description='test config',
        ... )
        >>> data['threshold']
        3.0

        >>> # From a file handle
        >>> with open('config.yaml', 'rb') as file_handle:
        ...     data = parse_yaml_to_dict(file_handle, 'config.yaml')

    Note:
        This function intentionally does NOT handle FileNotFoundError or
        similar I/O errors. Callers are responsible for opening files and
        handling I/O exceptions at the appropriate level.
    """
    logger.debug('Parsing YAML from: %s', source_description)

    # yaml.safe_load handles str, bytes, and file-like objects uniformly.
    # For bytes/files, it assumes UTF-8 encoding (YAML spec default).
    parsed_content: Any = yaml.safe_load(yaml_source)

    # -------------------------------------------------------------------------
    # Validation: Ensure we have a usable, non-empty dictionary with string keys
    # -------------------------------------------------------------------------
    # These checks catch common mistakes:
    #   - Empty files (None)
    #   - Files with only comments (None)
    #   - Files with just "---" or "{}" (empty dict)
    #   - Files that are actually lists or scalar values (wrong structure)
    #   - Files with non-string keys (YAML allows int/bool/etc. as keys)
    # -------------------------------------------------------------------------

    # Check 1: Content must not be None.
    # yaml.safe_load returns None for empty files or files with only comments.
    if parsed_content is None:
        logger.error('YAML content is empty (None): %s', source_description)
        raise ValueError(
            f'YAML content is empty: {source_description}. '
            f'File may be empty or contain only comments.'
        )

    # Check 2: Root must be a dictionary (mapping type).
    # ARGUS configs are always key-value structures, never bare lists or scalars.
    if not isinstance(parsed_content, dict):
        actual_type_name: str = type(parsed_content).__name__
        logger.error(
            'YAML root must be a dictionary, got %s: %s',
            actual_type_name,
            source_description,
        )
        raise TypeError(
            f'YAML root must be a dictionary, got {actual_type_name}: '
            f'{source_description}'
        )

    # Check 3: Dictionary must not be empty.
    # A YAML file with just "{}" or "---\n{}" parses to an empty dict,
    # which is technically valid YAML but almost certainly a mistake.
    if len(parsed_content) == 0:
        logger.error(
            'YAML content is an empty dictionary (no keys): %s',
            source_description,
        )
        raise ValueError(
            f'YAML content is an empty dictionary: {source_description}. '
            f'Configuration files must contain at least one key.'
        )

    # Check 4: All top-level keys must be strings.
    # YAML allows non-string keys (e.g., `123: value` or `true: value`),
    # but configuration files should always use string keys. Catching this
    # here provides a clearer error than letting Pydantic fail later.
    non_string_keys: list[tuple[Any, type[Any]]] = [
        (key, type(key))
        for key in parsed_content  # pyright: ignore[reportUnknownVariableType]
        if not isinstance(key, str)
    ]

    if non_string_keys:
        # Format examples of bad keys for the error message.
        # Show up to 3 examples to keep the message readable.
        bad_key_examples: list[str] = [
            f'{key!r} ({key_type.__name__})' for key, key_type in non_string_keys[:3]
        ]
        bad_keys_display: str = ', '.join(bad_key_examples)

        if len(non_string_keys) > 3:  # noqa: PLR2004
            bad_keys_display += f', ... ({len(non_string_keys)} total)'

        logger.error(
            'YAML contains non-string keys: %s in %s',
            bad_keys_display,
            source_description,
        )
        raise TypeError(
            f'YAML keys must be strings, found non-string keys: '
            f'{bad_keys_display} in {source_description}'
        )

    logger.debug(
        'Successfully parsed YAML with %d top-level keys: %s',
        len(parsed_content),
        source_description,
    )

    # Type narrowing: we've verified it's a non-empty dict with string keys.
    # The cast is now justified by our runtime validation above.
    validated_content: dict[str, Any] = cast(dict[str, Any], parsed_content)

    return validated_content


def load_yaml_from_path(file_path: str | Path) -> dict[str, Any]:
    """
    Load and parse a YAML file from the filesystem.

    This function handles user-provided configuration files. It opens the
    file in binary mode and delegates parsing to parse_yaml_to_dict().

    Path handling:
        - Tilde (~) is expanded automatically (e.g., ~/.argus/config.yaml)
        - Relative paths are resolved from the current working directory
        - Symlinks are resolved to their actual targets

    Args:
        file_path: Path to the YAML file. Can be a string or Path object.
            Supports tilde expansion for home directory references.

    Returns:
        Parsed YAML content as a dictionary.

    Raises:
        FileNotFoundError: If the file does not exist.
        IsADirectoryError: If the path points to a directory, not a file.
        PermissionError: If the file cannot be read due to permissions.
        yaml.YAMLError: If the YAML syntax is invalid.
        ValueError: If the YAML file is empty.
        TypeError: If the YAML root is not a dictionary.

    Example:
        >>> # Absolute path
        >>> config_data = load_yaml_from_path('/etc/argus/policy.yaml')
        >>>
        >>> # Tilde expansion
        >>> config_data = load_yaml_from_path('~/.argus/policy.yaml')
        >>>
        >>> # Relative path (resolved from cwd)
        >>> config_data = load_yaml_from_path('config/policy.yaml')

    See Also:
        load_yaml_from_package_resource: For loading bundled defaults.
        parse_yaml_to_dict: The underlying parsing function.
    """
    # Convert to Path if string, then expand ~ and resolve to absolute path.
    # Order matters: expanduser() must come before resolve() because
    # resolve() does NOT handle tilde expansion.
    resolved_path: Path = Path(file_path).expanduser().resolve()
    source_description: str = str(resolved_path)

    logger.debug('Loading YAML from filesystem: %s', source_description)

    # Open in binary mode. yaml.safe_load handles UTF-8 decoding internally.
    # This avoids encoding-related edge cases (BOMs, locale issues).
    #
    # We intentionally don't check exists()/is_file() before opening:
    #   1. EAFP (Easier to Ask Forgiveness than Permission) is Pythonic
    #   2. Avoids TOCTOU race conditions (file could be deleted between check and open)
    #   3. open() raises clear errors: FileNotFoundError, IsADirectoryError, PermissionError
    with resolved_path.open('rb') as file_handle:
        parsed_data: dict[str, Any] = parse_yaml_to_dict(
            yaml_source=file_handle,
            source_description=source_description,
        )

    logger.info('Loaded YAML from filesystem: %s', source_description)

    return parsed_data


def load_yaml_from_package_resource(
    resource_path: tuple[str, ...],
    package: str = DEFAULT_RESOURCE_PACKAGE,
) -> dict[str, Any]:
    """
    Load and parse a YAML file bundled within a Python package.

    This function uses importlib.resources to locate and read YAML files
    distributed as part of a package. This approach works correctly whether
    the package is installed via pip, run from source, or frozen with tools
    like PyInstaller.

    Args:
        resource_path: Tuple of path components within the package,
            starting from the package root. For example:
            ('defaults', 'policy.yaml') resolves to <package>/defaults/policy.yaml
        package: The package name containing the resource. Defaults to
            'argus' for ARGUS's bundled defaults.

    Returns:
        Parsed YAML content as a dictionary.

    Raises:
        FileNotFoundError: If the resource path does not exist within
            the package. This typically indicates a packaging error.
        yaml.YAMLError: If the YAML syntax is invalid.
        ValueError: If the YAML file is empty.
        TypeError: If the YAML root is not a dictionary.

    Example:
        >>> # Load ARGUS's default policy configuration
        >>> defaults = load_yaml_from_package_resource(
        ...     resource_path=('defaults', 'policy.yaml'),
        ... )
        >>> defaults['analysis']['zscore_threshold']
        3.0

    See Also:
        load_yaml_from_path: For loading user-provided files.
        parse_yaml_to_dict: The underlying parsing function.
    """
    # Build a readable description for error messages and logging.
    resource_path_joined: str = '/'.join(resource_path)
    source_description: str = f'{package}/{resource_path_joined}'

    logger.debug('Loading YAML from package resource: %s', source_description)

    # importlib.resources.files() returns a Traversable representing the
    # package root directory. joinpath() navigates to the specific resource.
    package_root: Traversable = files(package)
    resource_handle: Traversable = package_root.joinpath(*resource_path)

    # Open in binary mode, consistent with load_yaml_from_path().
    with resource_handle.open('rb') as resource_file:
        parsed_data: dict[str, Any] = parse_yaml_to_dict(
            yaml_source=resource_file,
            source_description=source_description,
        )

    logger.info('Loaded YAML from package resource: %s', source_description)

    return parsed_data
