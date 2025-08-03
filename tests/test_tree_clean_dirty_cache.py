"""Test that Tree.update() cleans dirty cached repositories"""

import gordion
import os
import pytest


def test_tree_update_cleans_dirty_cached_repos(tree_a):
    """
    Verifies that tree.update() cleans dirty cached repositories.
    """
    # Get a cached repository
    workspace = gordion.Workspace()
    repo_b = workspace.get_repository('gordion_demo_b')
    assert workspace.is_dependency(repo_b.path), f"Expected {repo_b.path} to be in cache"
    
    # Make it dirty by adding an untracked file
    test_file = os.path.join(repo_b.path, 'test_dirty.txt')
    with open(test_file, 'w') as f:
        f.write('This should be cleaned!')
    
    # Also modify an existing file
    readme_path = os.path.join(repo_b.path, 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'a') as f:
            f.write('\n# Modified content')
    
    # Verify the repository is dirty
    assert repo_b.handle.is_dirty(untracked_files=True)
    assert os.path.exists(test_file)
    
    # Update the tree - this should clean the dirty cached repository
    tree_a.update('082abea', 'test_status', force=True)
    
    # Verify the repository is now clean
    assert not repo_b.handle.is_dirty(untracked_files=True)
    assert not os.path.exists(test_file)


def test_tree_update_only_cleans_at_root(tree_a):
    """
    Verifies that only root tree updates clean dirty cached repositories.
    """
    # Get cached repositories
    workspace = gordion.Workspace()
    repo_b = workspace.get_repository('gordion_demo_b')
    repo_c = workspace.get_repository('gordion_demo_c')
    assert workspace.is_dependency(repo_b.path), f"Expected {repo_b.path} to be in cache"
    assert workspace.is_dependency(repo_c.path), f"Expected {repo_c.path} to be in cache"
    
    # Make repo_c dirty (not repo_b which we'll update directly)
    test_file = os.path.join(repo_c.path, 'test_dirty.txt')
    with open(test_file, 'w') as f:
        f.write('This should NOT be cleaned by non-root update!')
    
    # Verify repo_c is dirty
    assert repo_c.handle.is_dirty(untracked_files=True)
    
    # Create a tree for repo_b with parent (not root)
    repo_a = workspace.get_repository('gordion_demo_a')
    parent_tree = gordion.Tree(repo_a)
    child_tree = gordion.Tree(repo_b, parent=parent_tree)
    
    # Update the child tree - this should NOT clean cached repositories
    # since it's not the root
    child_tree.update('fe4fd4d', 'develop', force=True)
    
    # Verify repo_c is still dirty (not cleaned because update wasn't at root)
    assert repo_c.handle.is_dirty(untracked_files=True)
    assert os.path.exists(test_file)
    
    # Now update from the root - this should clean dirty cached repos
    tree_a.update('082abea', 'test_status', force=True)
    
    # Verify repo_c is now clean
    assert not repo_c.handle.is_dirty(untracked_files=True)
    assert not os.path.exists(test_file)