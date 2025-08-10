#!/usr/bin/env python3
"""
Tests for conda_check.py
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
import subprocess
import shutil
from unittest.mock import patch

# Add the bin directory to the path so we can import the script
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bin'))

def write_condarc_format(config, file_obj):
    """Write config dictionary in .condarc format."""
    for key, value in config.items():
        if isinstance(value, list):
            file_obj.write(f"{key}:\n")
            for item in value:
                file_obj.write(f"  - {item}\n")
        else:
            file_obj.write(f"{key}: {value}\n")

try:
    import conda_check
except ImportError as e:
    print(f"Warning: Could not import conda_check: {e}")
    conda_check = None


class TestCondaCheck(unittest.TestCase):
    """Test cases for conda_check functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.test_dir)
    
    def test_script_help_output(self):
        """Test that help output contains expected information."""
        script_path = Path(__file__).parent.parent / 'bin' / 'conda_check.py'
        
        result = subprocess.run(
            [sys.executable, str(script_path), '--help'],
            capture_output=True,
            text=True
        )
        
        self.assertEqual(result.returncode, 0)
        self.assertIn('Check conda configuration', result.stdout)
        self.assertIn('--verbose', result.stdout)
        self.assertIn('--condarc', result.stdout)
    
    @unittest.skipIf(conda_check is None, "Could not import conda_check module")
    def test_is_within_weka_direct_path(self):
        """Test is_within_weka with direct /mnt/weka paths."""
        # Test direct weka path
        self.assertTrue(conda_check.is_within_weka('/mnt/weka/pkg/cmr/user/conda'))
        
        # Test non-weka path
        self.assertFalse(conda_check.is_within_weka('/home/user/conda'))
        
        # Test empty/None path
        self.assertFalse(conda_check.is_within_weka(''))
        self.assertFalse(conda_check.is_within_weka(None))
    
    @unittest.skipIf(conda_check is None, "Could not import conda_check module")
    @patch('conda_check.resolve_path')
    def test_is_within_weka_symlink(self, mock_resolve):
        """Test is_within_weka with symlinked paths."""
        
        # Test symlink that resolves to weka
        mock_resolve.return_value = '/mnt/weka/pkg/cmr/user/conda'
        self.assertTrue(conda_check.is_within_weka('/home/user/.conda'))
        
        # Test symlink that doesn't resolve to weka
        mock_resolve.return_value = '/tmp/conda'
        self.assertFalse(conda_check.is_within_weka('/home/user/.conda'))
    
    @unittest.skipIf(conda_check is None, "Could not import conda_check module")
    def test_load_condarc_missing_file(self):
        """Test loading a non-existent .condarc file."""
        missing_file = Path(self.test_dir) / 'nonexistent.condarc'
        result = conda_check.load_condarc(missing_file)
        self.assertIsNone(result)
    
    @unittest.skipIf(conda_check is None, "Could not import conda_check module")
    def test_load_condarc_valid_file(self):
        """Test loading a valid .condarc file."""
        # Create a test .condarc file
        condarc_path = Path(self.test_dir) / '.condarc'
        test_config = {
            'channels': ['conda-forge', 'bioconda'],
            'envs_dirs': ['/mnt/weka/pkg/cmr/testuser/conda/envs'],
            'pkgs_dirs': ['/mnt/weka/pkg/cmr/testuser/conda/pkgs']
        }
        
        with open(condarc_path, 'w') as f:
            write_condarc_format(test_config, f)
        
        result = conda_check.load_condarc(condarc_path)
        self.assertEqual(result, test_config)
    
    @unittest.skipIf(conda_check is None, "Could not import conda_check module")
    def test_load_condarc_invalid_format(self):
        """Test loading a .condarc file that can't be read."""
        # Create a file that can't be read (permission issue would be one case)
        # For this test, we'll create a file and then make it unreadable
        condarc_path = Path(self.test_dir) / '.condarc'
        with open(condarc_path, 'w') as f:
            f.write('some content')
        
        # Test by patching open to raise an exception
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            result = conda_check.load_condarc(condarc_path)
            self.assertIsNone(result)
    
    @unittest.skipIf(conda_check is None, "Could not import conda_check module")
    def test_check_env_dirs_valid(self):
        """Test checking environment directories with valid configuration."""
        config = {
            'envs_dirs': ['/pkg/cmr/testuser/conda/envs', '~/miniconda3/envs']
        }
        
        is_ok, message = conda_check.check_env_dirs(config)
        self.assertTrue(is_ok)
        self.assertIn('/pkg/cmr or /mnt/weka', message)
    
    @unittest.skipIf(conda_check is None, "Could not import conda_check module")
    def test_check_env_dirs_invalid(self):
        """Test checking environment directories with invalid configuration."""
        config = {
            'envs_dirs': ['/home/user/conda/envs', '/mnt/weka/pkg/cmr/testuser/conda/envs']
        }
        
        is_ok, message = conda_check.check_env_dirs(config)
        self.assertFalse(is_ok)
        self.assertIn('not within /pkg/cmr or /mnt/weka', message)
    
    @unittest.skipIf(conda_check is None, "Could not import conda_check module")
    def test_check_env_dirs_missing(self):
        """Test checking environment directories when not configured."""
        config = {}
        
        is_ok, message = conda_check.check_env_dirs(config)
        self.assertFalse(is_ok)
        self.assertIn('No environment directories', message)
    
    @unittest.skipIf(conda_check is None, "Could not import conda_check module")
    def test_check_pkg_dirs_valid(self):
        """Test checking package directories with valid configuration."""
        config = {
            'pkgs_dirs': ['/pkg/cmr/testuser/conda/pkgs', '~/miniconda3/pkgs']
        }
        
        is_ok, message = conda_check.check_pkg_dirs(config)
        self.assertTrue(is_ok)
        self.assertIn('/pkg/cmr or /mnt/weka', message)
    
    @unittest.skipIf(conda_check is None, "Could not import conda_check module")
    def test_check_pkg_dirs_invalid(self):
        """Test checking package directories with invalid configuration."""
        config = {
            'pkgs_dirs': ['/home/user/conda/pkgs', '/mnt/weka/pkg/cmr/testuser/conda/pkgs']
        }
        
        is_ok, message = conda_check.check_pkg_dirs(config)
        self.assertFalse(is_ok)
        self.assertIn('not within /pkg/cmr or /mnt/weka', message)
    
    @unittest.skipIf(conda_check is None, "Could not import conda_check module")
    @patch('conda_check.Path.home')
    @patch('conda_check.getpass.getuser')
    def test_check_conda_symlink_correct(self, mock_getuser, mock_home):
        """Test checking ~/.conda symlink when correctly configured."""
        mock_getuser.return_value = 'testuser'
        mock_home_path = Path(self.test_dir)
        mock_home.return_value = mock_home_path
        
        # Create a local target directory for the symlink
        target_dir = Path(self.test_dir) / 'weka_target'
        target_dir.mkdir(parents=True)
        
        # Create symlink
        conda_link = mock_home_path / '.conda'
        conda_link.symlink_to(target_dir)
        
        # Mock the pathlib.Path.resolve method to return a /pkg/cmr path
        with patch.object(Path, 'resolve') as mock_resolve:
            mock_resolve.return_value = Path('/pkg/cmr/testuser/.conda')
            is_ok, message = conda_check.check_conda_symlink()
            
        self.assertTrue(is_ok, f"Expected symlink check to pass, but got: {message}")
        self.assertIn('correctly symlinked', message)
    
    @unittest.skipIf(conda_check is None, "Could not import conda_check module")
    @patch('conda_check.Path.home')
    def test_check_conda_symlink_missing(self, mock_home):
        """Test checking ~/.conda symlink when it doesn't exist."""
        mock_home_path = Path(self.test_dir)
        mock_home.return_value = mock_home_path
        
        is_ok, message = conda_check.check_conda_symlink()
        self.assertFalse(is_ok)
        self.assertIn('does not exist', message)
    
    @unittest.skipIf(conda_check is None, "Could not import conda_check module")
    def test_generate_template_condarc(self):
        """Test generating template .condarc content."""
        suggested_envs_dir = '/pkg/cmr/testuser/conda/envs'
        suggested_pkgs_dir = '/pkg/cmr/testuser/conda/pkgs'
        
        template = conda_check.generate_template_condarc(suggested_envs_dir, suggested_pkgs_dir)
        
        self.assertIn('testuser', template)
        self.assertIn('/pkg/cmr/testuser', template)
        self.assertIn('envs_dirs:', template)
        self.assertIn('pkgs_dirs:', template)
        self.assertIn('conda-forge', template)
    
    @unittest.skipIf(conda_check is None, "Could not import conda_check module")
    def test_generate_fix_suggestions(self):
        """Test generating fix suggestions for various issues."""
        with patch('conda_check.getpass.getuser', return_value='testuser'):
            # Test when all checks fail
            suggestions = conda_check.generate_fix_suggestions(False, False, False)
        
        self.assertTrue(len(suggestions) > 0)
        suggestion_text = ' '.join(suggestions)
        self.assertIn('condarc', suggestion_text)
        self.assertIn('symlink', suggestion_text)
    
    @unittest.skipIf(conda_check is None, "Could not import conda_check module")
    def test_script_exit_code_success(self):
        """Test that script shows configuration check results."""
        script_path = Path(__file__).parent.parent / 'bin' / 'conda_check.py'
        
        # Create a temporary .condarc with correct configuration
        with tempfile.NamedTemporaryFile(mode='w', suffix='.condarc', delete=False) as f:
            config = {
                'envs_dirs': ['/pkg/cmr/testuser/conda/envs'],
                'pkgs_dirs': ['/pkg/cmr/testuser/conda/pkgs']
            }
            write_condarc_format(config, f)
            condarc_path = f.name
        
        try:
            # Test with --show-success to ensure we get output
            result = subprocess.run(
                [sys.executable, str(script_path), '--show-success', '--condarc', condarc_path],
                capture_output=True,
                text=True,
                env={**os.environ, 'PYTHONPATH': str(Path(__file__).parent.parent / 'bin')}
            )
            
            # Should at least show that it's checking conda configuration
            self.assertIn('conda configuration', result.stdout.lower())
            
        finally:
            os.unlink(condarc_path)

    @unittest.skipIf(conda_check is None, "Could not import conda_check module")
    @patch('conda_check.check_conda_symlink')
    @patch('conda_check.check_pkg_dirs')
    @patch('conda_check.check_env_dirs')
    def test_main_function_success(self, mock_env_dirs, mock_pkg_dirs, mock_symlink):
        """Test main function when all checks pass."""
        # Mock all checks to pass
        mock_env_dirs.return_value = (True, "Environment directories OK")
        mock_pkg_dirs.return_value = (True, "Package directories OK") 
        mock_symlink.return_value = (True, "Symlink OK")
        
        # Create a valid config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.condarc', delete=False) as f:
            config = {
                'envs_dirs': ['/pkg/cmr/testuser/conda/envs'],
                'pkgs_dirs': ['/pkg/cmr/testuser/conda/pkgs']
            }
            write_condarc_format(config, f)
            condarc_path = f.name
        
        try:
            # Test that main exits with 0 when all checks pass
            with patch('sys.argv', ['conda_check.py', '--condarc', condarc_path]):
                with self.assertRaises(SystemExit) as cm:
                    conda_check.main()
                self.assertEqual(cm.exception.code, 0)
        finally:
            os.unlink(condarc_path)
    
    def test_script_exit_code_failure(self):
        """Test that script exits with 1 when checks fail."""
        script_path = Path(__file__).parent.parent / 'bin' / 'conda_check.py'
        
        # Create a temporary .condarc with incorrect configuration
        with tempfile.NamedTemporaryFile(mode='w', suffix='.condarc', delete=False) as f:
            config = {
                'envs_dirs': ['/home/user/conda/envs'],
                'pkgs_dirs': ['/home/user/conda/pkgs']
            }
            write_condarc_format(config, f)
            condarc_path = f.name
        
        try:
            result = subprocess.run(
                [sys.executable, str(script_path), '--condarc', condarc_path],
                capture_output=True,
                text=True
            )
            
            self.assertEqual(result.returncode, 1)
            self.assertIn('Configuration Issues Found', result.stdout)
        finally:
            os.unlink(condarc_path)


if __name__ == '__main__':
    unittest.main()
