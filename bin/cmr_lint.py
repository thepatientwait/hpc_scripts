#!/usr/bin/env python3
"""
cmr_lint.py - Check and validate conda configuration for CMR HPC environment.

This script checks a user's ~/.condarc file to ensure:
1. The first element of env_dirs is within /pkg/cmr or /mnt/weka
2. The first element of pkg_dirs is within /pkg/cmr or /mnt/weka
3. ~/.conda is symlinked to /pkg/cmr/[username]/.conda or /mnt/weka/pkg/cmr/[username]/.conda

If any of these conditions are not met, it provides warnings and suggestions
for fixing the configuration.
"""

import argparse
import getpass
import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd, capture_output=True):
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=capture_output,
            text=True,
            check=True
        )
        return result.stdout.strip() if capture_output else None
    except subprocess.CalledProcessError as e:
        if capture_output:
            return None
        else:
            print(f"Error running command '{cmd}': {e}")
            return None


def resolve_path(path):
    """Resolve a path using readlink -f to handle symlinks."""
    resolved = run_command(f"readlink -f {path}")
    return resolved if resolved else str(path)


def is_within_weka(path):
    """Check if a path is within /mnt/weka or /pkg/cmr (either directly or via symlink)."""
    if not path:
        return False
    
    # Check direct path for both /mnt/weka and /pkg/cmr
    path_str = str(path)
    if path_str.startswith('/mnt/weka') or path_str.startswith('/pkg/cmr'):
        return True
    
    # Check resolved path (following symlinks)
    resolved = resolve_path(path)
    if resolved and (resolved.startswith('/mnt/weka') or resolved.startswith('/pkg/cmr')):
        return True
    
    return False


def parse_condarc_line(line):
    """Parse a single line from .condarc file."""
    line = line.strip()
    if not line or line.startswith('#'):
        return None, None
    
    if ':' in line and not line.startswith(' ') and not line.startswith('-'):
        # This is a key line
        key, value = line.split(':', 1)
        key = key.strip()
        value = value.strip()
        if value:
            # Single value on same line
            return key, [value] if key.endswith('_dirs') else value
        else:
            # Multi-line list follows
            return key, []
    elif line.startswith('- '):
        # This is a list item
        return 'list_item', line[2:].strip()
    
    return None, None


def format_config(config):
    """Format configuration dictionary as YAML-like text."""
    lines = []
    for key, value in config.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {item}")
        else:
            lines.append(f"{key}: {value}")
    return '\n'.join(lines)


def load_condarc(condarc_path):
    """Load and parse the .condarc file. Returns None if file doesn't exist or can't be parsed."""
    if not condarc_path.exists():
        return None
    
    try:
        config = {}
        current_key = None
        
        with open(condarc_path, 'r') as f:
            for line in f:
                key, value = parse_condarc_line(line)
                
                if key and key != 'list_item':
                    current_key = key
                    if isinstance(value, list):
                        config[key] = value
                    else:
                        config[key] = value
                elif key == 'list_item' and current_key:
                    if current_key not in config:
                        config[current_key] = []
                    if isinstance(config[current_key], list):
                        config[current_key].append(value)
        
        return config if config else {}
    except Exception as e:
        print(f"Warning: Could not read {condarc_path}: {e}")
        return None


def check_env_dirs(config):
    """Check if the first env_dirs entry is within /mnt/weka or /pkg/cmr."""
    env_dirs = config.get('envs_dirs', config.get('env_dirs', []))
    
    if not env_dirs:
        return False, "No environment directories configured"
    
    first_env_dir = env_dirs[0]
    if is_within_weka(first_env_dir):
        return True, f"First env_dirs entry is correctly within /pkg/cmr or /mnt/weka: {first_env_dir}"
    else:
        resolved = resolve_path(first_env_dir)
        return False, f"First env_dirs entry '{first_env_dir}' (resolves to '{resolved}') is not within /pkg/cmr or /mnt/weka"


def check_pkg_dirs(config):
    """Check if the first pkg_dirs entry is within /mnt/weka or /pkg/cmr."""
    pkg_dirs = config.get('pkgs_dirs', config.get('pkg_dirs', []))
    
    if not pkg_dirs:
        return False, "No package directories configured"
    
    first_pkg_dir = pkg_dirs[0]
    if is_within_weka(first_pkg_dir):
        return True, f"First pkgs_dirs entry is correctly within /pkg/cmr or /mnt/weka: {first_pkg_dir}"
    else:
        resolved = resolve_path(first_pkg_dir)
        return False, f"First pkgs_dirs entry '{first_pkg_dir}' (resolves to '{resolved}') is not within /pkg/cmr or /mnt/weka"


def check_conda_symlink():
    """Check if ~/.conda is symlinked to the correct location in /pkg/cmr or /mnt/weka."""
    username = getpass.getuser()
    home_conda = Path.home() / '.conda'
    expected_target_pkg = f"/pkg/cmr/{username}/.conda"
    expected_target_weka = f"/mnt/weka/pkg/cmr/{username}/.conda"
    
    if not home_conda.exists():
        return False, f"~/.conda does not exist"
    
    if not home_conda.is_symlink():
        resolved = resolve_path(str(home_conda))
        if resolved and (resolved.startswith('/mnt/weka') or resolved.startswith('/pkg/cmr')):
            return True, f"~/.conda is within /pkg/cmr or /mnt/weka (resolves to {resolved})"
        else:
            return False, f"~/.conda is not a symlink to /pkg/cmr or /mnt/weka (actual path: {resolved})"
    
    # It's a symlink, check if it points to the right place
    actual_target = str(home_conda.resolve())
    if actual_target in [expected_target_pkg, expected_target_weka] or actual_target.startswith('/mnt/weka') or actual_target.startswith('/pkg/cmr'):
        return True, f"~/.conda correctly symlinked to {actual_target}"
    else:
        return False, f"~/.conda symlinked to wrong location: {actual_target}"


def generate_template_condarc(suggested_envs_dir, suggested_pkgs_dir):
    """Generate a template .condarc file with CMR-specific settings."""
    
    template = f"""# CMR HPC conda configuration
# Place this in ~/.condarc

channels:
  - conda-forge
  - bioconda
  - defaults

envs_dirs:
  - {suggested_envs_dir}

pkgs_dirs:
  - {suggested_pkgs_dir}

solver: libmamba
"""
    return template


def generate_fix_suggestions(env_dirs_ok, pkg_dirs_ok, conda_symlink_ok, qsub_logs_ok):
    """Generate suggestions for fixing conda configuration issues."""
    username = getpass.getuser()
    suggestions = []
    suggested_envs_dir = f"/pkg/cmr/{username}/conda/envs"
    suggested_pkgs_dir = f"/pkg/cmr/{username}/conda/pkgs"

    step_num = 1
    if not env_dirs_ok:
        suggestions.append(f"{step_num}. Move the conda dir to new location")
        suggestions.append(f"   mv ~/.conda/envs {suggested_envs_dir}")
        step_num += 1

    if not pkg_dirs_ok:
        suggestions.append(f"{step_num}. Remove the old pkgs_dirs:")
        suggestions.append(f"   rm -rf ~/.conda/pkgs")
        step_num += 1

    if not env_dirs_ok or not pkg_dirs_ok:
        # Include template when there are config issues
        suggestions.append("Recommended .condarc template:")
        suggestions.append("-" * 40)
        suggestions.append(generate_template_condarc(suggested_envs_dir, suggested_pkgs_dir))
        suggestions.append("")
        suggestions.append(f"{step_num}. Update your ~/.condarc file with the template shown above")
        step_num += 1

    if not conda_symlink_ok:
        target_dir = f"/pkg/cmr/{username}/.conda"
        suggestions.append(f"{step_num}. Create the correct ~/.conda symlink:")
        suggestions.append(f"   rm -rf ~/.conda/pkgs")
        suggestions.append(f"   mkdir -p /pkg/cmr/{username}/")
        suggestions.append(f"   mv ~/.conda {target_dir}")
        suggestions.append(f"   ln -sf {target_dir} ~/.conda")
        step_num += 1
    
    if not qsub_logs_ok:
        suggestions.append(f"{step_num}. Clean up old qsub log folders:")
        suggestions.append(f"   # Review and remove folders older than 3 months in ~/qsub_logs")
        suggestions.append(f"   # Example: rm -rf ~/qsub_logs/2024-01-*  # (adjust dates as needed)")
        suggestions.append(f"   # Or use: find ~/qsub_logs -maxdepth 1 -name '????-??-??' -type d -mtime +90 -delete")
    
    return suggestions


def check_old_qsub_logs():
    """Check for qsub log folders older than 3 months in ~/qsub_logs."""
    from datetime import datetime, timedelta
    import re
    
    qsub_logs_dir = Path.home() / 'qsub_logs'
    
    if not qsub_logs_dir.exists():
        return True, "No ~/qsub_logs directory found"
    
    if not qsub_logs_dir.is_dir():
        return True, "~/qsub_logs exists but is not a directory"
    
    # Date pattern for YYYY-MM-DD
    date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
    three_months_ago = datetime.now() - timedelta(days=90)
    old_folders = []
    
    try:
        for item in qsub_logs_dir.iterdir():
            if item.is_dir() and date_pattern.match(item.name):
                try:
                    folder_date = datetime.strptime(item.name, '%Y-%m-%d')
                    if folder_date < three_months_ago:
                        old_folders.append(item.name)
                except ValueError:
                    # Skip folders that don't match the date format exactly
                    continue
    except PermissionError:
        return True, "Cannot access ~/qsub_logs directory (permission denied)"
    
    if old_folders:
        old_folders.sort()
        oldest_folder = old_folders[0]
        newest_old_folder = old_folders[-1]
        if len(old_folders) == 1:
            return False, f"Found 1 old qsub log folder: {oldest_folder}"
        else:
            return False, f"Found {len(old_folders)} old qsub log folders (oldest: {oldest_folder}, newest old: {newest_old_folder})"
    else:
        return True, "No old qsub log folders found"


def main():
    """Main function to check conda configuration."""
    parser = argparse.ArgumentParser(
        description="Check conda configuration for CMR HPC environment",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show verbose output including configuration details'
    )
    parser.add_argument(
        '--show-success',
        action='store_true',
        help='Show output even when all checks pass (default is silent on success)'
    )
    parser.add_argument(
        '--condarc',
        type=Path,
        default=Path.home() / '.condarc',
        help='Path to .condarc file (default: ~/.condarc)'
    )
    
    args = parser.parse_args()
    
    # Check .condarc file
    config = load_condarc(args.condarc)
    if config is None:
        if args.show_success:
            print("Checking conda configuration for CMR HPC environment...")
            print("=" * 60)
            print(f"⚠️  No readable .condarc file found at {args.condarc}")
        env_dirs_ok, env_msg = False, "No .condarc file"
        pkg_dirs_ok, pkg_msg = False, "No .condarc file"
    else:
        if args.show_success:
            print("Checking conda configuration for CMR HPC environment...")
            print("=" * 60)
            print(f"✓ Found .condarc file at {args.condarc}")
        env_dirs_ok, env_msg = check_env_dirs(config)
        pkg_dirs_ok, pkg_msg = check_pkg_dirs(config)
    
    # Check ~/.conda symlink
    conda_symlink_ok, conda_msg = check_conda_symlink()
    
    # Check old qsub log folders
    qsub_logs_ok, qsub_logs_msg = check_old_qsub_logs()
    
    # Only show results if --show-success is used or if there are issues
    all_good = env_dirs_ok and pkg_dirs_ok and conda_symlink_ok and qsub_logs_ok
    show_output = args.show_success or not all_good
    
    if show_output:
        if not args.show_success:
            # Only print header when there are issues and user didn't request show-success
            print("Checking conda configuration for CMR HPC environment...")
            print("=" * 60)
        
        print("\nResults:")
        print("-" * 40)
        
        status_env = "✓" if env_dirs_ok else "✗"
        print(f"{status_env} Environment directories: {env_msg}")
        
        status_pkg = "✓" if pkg_dirs_ok else "✗"
        print(f"{status_pkg} Package directories: {pkg_msg}")
        
        status_conda = "✓" if conda_symlink_ok else "✗"
        print(f"{status_conda} ~/.conda symlink: {conda_msg}")
        
        status_qsub_logs = "✓" if qsub_logs_ok else "✗"
        print(f"{status_qsub_logs} Old qsub log folders: {qsub_logs_msg}")
    
    # If verbose, show current config
    if args.verbose and config and show_output:
        print(f"\nCurrent .condarc configuration:")
        print("-" * 40)
        print(format_config(config))
    
    # Show warnings and suggestions if needed
    if not all_good:
        if not show_output:
            # Print header if we haven't already
            print("Checking conda configuration for CMR HPC environment...")
            print("=" * 60)

        print("\n⚠️ Configuration Issues Found! Fixes suggested:")
        print("=" * 60)
        
        suggestions = generate_fix_suggestions(env_dirs_ok, pkg_dirs_ok, conda_symlink_ok, qsub_logs_ok)
        if suggestions:
            print("")
            for suggestion in suggestions:
                print(suggestion)
        
        print("\nAfter making changes, restart your shell or run 'conda info' to verify.")
        sys.exit(1)
    else:
        if args.show_success:
            print("\n✓ All conda configuration checks passed!")
        sys.exit(0)


if __name__ == '__main__':
    main()
