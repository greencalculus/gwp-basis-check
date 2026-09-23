"""The pre-commit entry point: findings block, unreadable files do not."""

import sys

from gwp_basis_check import main


def hook_exit_code(status):
    """Map the checker result to the pre-commit contract.

    Exit 2 means a file was not in a form this checker can read.  That is an
    expected result when a broad pre-commit file filter sees an ordinary source
    file, so it must not reject the commit.  Findings (1) still block it.
    """
    return 0 if status == 2 else status


if __name__ == "__main__":
    sys.exit(hook_exit_code(main()))
