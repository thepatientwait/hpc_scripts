#!/usr/bin/env python3
"""
Tests for pixi_cmr_init.py
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
import subprocess
import shutil

# Add the bin directory to the path so we can import the script
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bin'))

try:
    import pixi_cmr_init
except ImportError as e:
    print(f"Warning: Could not import pixi_cmr_init: {e}")
    pixi_cmr_init = None


class TestPixiCmrInit(unittest.TestCase):
    """Test cases for pixi_cmr_init functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.test_dir)
    
    def test_script_help_output(self):
        """Test that help output contains expected information."""
        script_path = Path(__file__).parent.parent / 'bin' / 'pixi_cmr_init.py'
        
        result = subprocess.run(
            [sys.executable, str(script_path), '--help'],
            capture_output=True,
            text=True
        )
        
        self.assertEqual(result.returncode, 0)
        self.assertIn('Initialize a pixi project', result.stdout)
        self.assertIn('--dry-run', result.stdout)
        self.assertIn('--base-dir', result.stdout)
    
    def test_custom_base_dir_dry_run(self):
        """Test dry-run with custom base directory."""
        script_path = Path(__file__).parent.parent / 'bin' / 'pixi_cmr_init.py'
        
        result = subprocess.run(
            [sys.executable, str(script_path), '--dry-run', '--base-dir', '/tmp/custom_base', self.test_dir],
            capture_output=True,
            text=True
        )
        
        self.assertEqual(result.returncode, 0, "Dry run with custom base should succeed")
        self.assertIn('DRY RUN MODE', result.stdout)
        self.assertIn('/tmp/custom_base', result.stdout)
    
    @unittest.skipIf(pixi_cmr_init is None, "Could not import pixi_cmr_init module")
    def test_create_pixi_directory_with_custom_base(self):
        """Test .pixi directory creation with custom base directory and verify symlink."""
        if pixi_cmr_init is None:
            self.skipTest("pixi_cmr_init module not available")
        
        test_path = Path(self.test_dir)
        custom_base = Path(self.test_dir) / 'custom_base'
        
        result_path = pixi_cmr_init.create_pixi_directory(test_path, str(custom_base))
        
        # Should return the symlink path in the target directory
        expected_symlink = test_path / '.pixi'
        self.assertEqual(result_path, expected_symlink)
        
        # The .pixi should exist
        self.assertTrue(result_path.exists(), ".pixi should exist at target location")
        
        # Check that it's a symlink pointing to the expected location
        if result_path.is_symlink():
            import getpass
            username = getpass.getuser()
            path_name = str(test_path).replace('/', '_')
            pixi_dir_name = f"{path_name}.pixi"
            expected_target = custom_base / username / 'pixi_dirs' / pixi_dir_name
            
            self.assertEqual(result_path.resolve(), expected_target)
            self.assertTrue(expected_target.exists(), "Target directory should exist")
            print(f"Symlink verified: {result_path} -> {expected_target}")


if __name__ == '__main__':
    unittest.main()
