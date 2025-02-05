#!/usr/bin/env python3
import argparse
import logging
import os
import sys
from pathlib import Path

from file_operator import FileOperator

def format_size(size_bytes):
    """Format file size in a human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024 or unit == 'GB':
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024

def dedupe_folder(folder_path, dry_run=False):
    """
    Find and remove duplicate files in the specified folder.
    
    Args:
        folder_path: Path to the folder to deduplicate
        dry_run: If True, only report duplicates without removing them
    
    Returns:
        Tuple of (total_files, unique_files, duplicate_files, removed_files)
    """
    folder_path = Path(folder_path).resolve()
    if not folder_path.exists() or not folder_path.is_dir():
        print(f"Error: {folder_path} is not a valid directory")
        return 0, 0, 0, 0
    
    # Create a FileOperator instance
    file_operator = FileOperator(
        input_base_path=folder_path,  # Not used for deduplication
        output_base_path=folder_path,
        remove_input_files=False  # We'll handle removal ourselves
    )
    
    # Scan the folder to build hash dictionary
    file_operator.scan_output_directory()
    
    # Get statistics
    stats = file_operator.get_duplicate_stats()
    total_files = stats['total_files']
    unique_files = stats['unique_files']
    duplicate_files = stats['duplicate_files']
    duplicate_groups = stats['duplicate_groups']
    
    print(f"\nDuplicate File Statistics for {folder_path}:")
    print(f"Total files scanned: {total_files}")
    print(f"Unique files: {unique_files}")
    print(f"Duplicate files: {duplicate_files}")
    print(f"Duplicate groups: {duplicate_groups}")
    
    removed_files = 0
    
    # Process duplicates
    if duplicate_groups > 0:
        print("\nDuplicate groups:")
        for file_hash, paths in file_operator.file_hash_dict.items():
            if len(paths) > 1:
                # Get size of first file
                try:
                    size = paths[0].stat().st_size
                    formatted_size = format_size(size)
                    print(f"- {paths[0]} ({len(paths)} duplicates, {formatted_size})")
                    
                    # Print all duplicate files with indentation
                    for path in paths[1:]:
                        try:
                            path_size = path.stat().st_size
                            path_formatted_size = format_size(path_size)
                            print(f"    - {path} ({path_formatted_size})")
                            
                            # Remove duplicate if not in dry run mode
                            if not dry_run:
                                try:
                                    os.remove(path)
                                    print(f"      Removed!")
                                    removed_files += 1
                                except (FileNotFoundError, PermissionError, OSError) as e:
                                    print(f"      Error removing: {e}")
                        except (FileNotFoundError, PermissionError) as e:
                            print(f"    - {path} (Error accessing: {e})")
                except (FileNotFoundError, PermissionError) as e:
                    print(f"- Error accessing {paths[0]}: {e}")
    
    # Print summary
    if dry_run:
        print(f"\nDRY RUN: Would have removed {duplicate_files} duplicate files")
    else:
        print(f"\nRemoved {removed_files} duplicate files")
    
    return total_files, unique_files, duplicate_files, removed_files

def main():
    parser = argparse.ArgumentParser(description='Find and remove duplicate files in a folder')
    parser.add_argument('folder', help='Folder to deduplicate')
    parser.add_argument('--dry-run', action='store_true', help='Only report duplicates, do not remove them')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format='%(levelname)s: %(message)s')
    
    # Run deduplication
    try:
        dedupe_folder(args.folder, args.dry_run)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
