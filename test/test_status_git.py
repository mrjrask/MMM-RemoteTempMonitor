#!/usr/bin/env python3
"""
Unit tests for git status checking in status-broadcaster.py

Tests:
- Git folder existence check
- Git status parsing for various change types
- Handling edge cases (no folder, git not installed, etc.)
"""

import unittest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Pi'))

# Mock subprocess before importing status_broadcaster
from unittest.mock import Mock
original_run = subprocess.run
subprocess.run = Mock(returncode=0, stdout=b"", stderr=b"")

class TestDesktopGitCheck(unittest.TestCase):
    """Test git status checking in desk_display folder"""
    
    def test_git_check_without_folder(self):
        """Test that git check returns False when folder doesn't exist"""
        from status_broadcaster import StatusBroadcaster
        from pathlib import Path
        
        # Mock Path.exists to return False for desk_display
        original_exists = Path.exists
        Path.exists = lambda self: False
        
        broadcaster = StatusBroadcaster(port=9876, interval=60)
        result = broadcaster._check_desk_display_git_status()
        
        # Restore original
        Path.exists = original_exists
        
        self.assertFalse(result, "Should return False when desk_display doesn't exist")
    
    def test_git_check_with_clean_folder(self):
        """Test that git check returns False for a clean folder"""
        from status_broadcaster import StatusBroadcaster
        from unittest.mock import Mock
        
        # Mock subprocess.run to return clean git status
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = b""
        mock_result.stderr = b""
        
        def mock_run(*args, **kwargs):
            return mock_result
        
        original_run = subprocess.run
        subprocess.run = mock_run
        
        broadcaster = StatusBroadcaster(port=9876, interval=60)
        result = broadcaster._check_desk_display_git_status()
        
        # Restore original
        subprocess.run = original_run
        
        self.assertFalse(result, "Should return False for clean folder")
    
    def test_git_check_with_modified_files(self):
        """Test that git check returns True when files are modified"""
        from status_broadcaster import StatusBroadcaster
        from unittest.mock import Mock
        
        # Mock subprocess.run to return modified git status
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = b" M file1.txt\n M file2.txt\n"
        mock_result.stderr = b""
        
        def mock_run(*args, **kwargs):
            return mock_result
        
        original_run = subprocess.run
        subprocess.run = mock_run
        
        broadcaster = StatusBroadcaster(port=9876, interval=60)
        result = broadcaster._check_desk_display_git_status()
        
        # Restore original
        subprocess.run = original_run
        
        self.assertTrue(result, "Should return True for modified files")
    
    def test_git_check_with_added_files(self):
        """Test that git check returns True when files are added"""
        from status_broadcaster import StatusBroadcaster
        from unittest.mock import Mock
        
        # Mock subprocess.run to return added files
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = b" A newfile.txt\n"
        mock_result.stderr = b""
        
        def mock_run(*args, **kwargs):
            return mock_result
        
        original_run = subprocess.run
        subprocess.run = mock_run
        
        broadcaster = StatusBroadcaster(port=9876, interval=60)
        result = broadcaster._check_desk_display_git_status()
        
        # Restore original
        subprocess.run = original_run
        
        self.assertTrue(result, "Should return True for added files")
    
    def test_git_check_with_deleted_files(self):
        """Test that git check returns True when files are deleted"""
        from status_broadcaster import StatusBroadcaster
        from unittest.mock import Mock
        
        # Mock subprocess.run to return deleted files
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = b" D deletedfile.txt\n"
        mock_result.stderr = b""
        
        def mock_run(*args, **kwargs):
            return mock_result
        
        original_run = subprocess.run
        subprocess.run = mock_run
        
        broadcaster = StatusBroadcaster(port=9876, interval=60)
        result = broadcaster._check_desk_display_git_status()
        
        # Restore original
        subprocess.run = original_run
        
        self.assertTrue(result, "Should return True for deleted files")
    
    def test_git_check_with_renamed_files(self):
        """Test that git check returns True when files are renamed"""
        from status_broadcaster import StatusBroadcaster
        from unittest.mock import Mock
        
        # Mock subprocess.run to return renamed files
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = b" R oldname.txt newname.txt\n"
        mock_result.stderr = b""
        
        def mock_run(*args, **kwargs):
            return mock_result
        
        original_run = subprocess.run
        subprocess.run = mock_run
        
        broadcaster = StatusBroadcaster(port=9876, interval=60)
        result = broadcaster._check_desk_display_git_status()
        
        # Restore original
        subprocess.run = original_run
        
        self.assertTrue(result, "Should return True for renamed files")
    
    def test_git_check_with_untracked_files(self):
        """Test that git check returns True for untracked files"""
        from status_broadcaster import StatusBroadcaster
        from unittest.mock import Mock
        
        # Mock subprocess.run to return untracked files
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = b" ? untracked_file.txt\n"
        mock_result.stderr = b""
        
        def mock_run(*args, **kwargs):
            return mock_result
        
        original_run = subprocess.run
        subprocess.run = mock_run
        
        broadcaster = StatusBroadcaster(port=9876, interval=60)
        result = broadcaster._check_desk_display_git_status()
        
        # Restore original
        subprocess.run = original_run
        
        self.assertTrue(result, "Should return True for untracked files")
    
    def test_git_check_with_no_git_changes(self):
        """Test that git check returns False when there are no unstaged changes"""
        from status_broadcaster import StatusBroadcaster
        from unittest.mock import Mock
        
        # Mock subprocess.run to return normal git status (all committed)
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = b"On branch main\nAll changes staged.\n"
        mock_result.stderr = b""
        
        def mock_run(*args, **kwargs):
            return mock_result
        
        original_run = subprocess.run
        subprocess.run = mock_run
        
        broadcaster = StatusBroadcaster(port=9876, interval=60)
        result = broadcaster._check_desk_display_git_status()
        
        # Restore original
        subprocess.run = original_run
        
        self.assertFalse(result, "Should return False when all changes are committed")
    
    def test_git_check_git_not_installed(self):
        """Test that git check handles case when git command is not found"""
        from status_broadcaster import StatusBroadcaster
        from unittest.mock import Mock
        
        # Mock subprocess.run to simulate git not found
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = b""
        mock_result.stderr = b"git: command not found\n"
        
        def mock_run(*args, **kwargs):
            return mock_result
        
        original_run = subprocess.run
        subprocess.run = mock_run
        
        broadcaster = StatusBroadcaster(port=9876, interval=60)
        result = broadcaster._check_desk_display_git_status()
        
        # Restore original
        subprocess.run = original_run
        
        self.assertFalse(result, "Should return False when git is not installed")


if __name__ == "__main__":
    # Run with unittest
    unittest.main()