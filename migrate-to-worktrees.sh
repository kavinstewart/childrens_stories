#!/bin/bash
set -euo pipefail

# Migration script: Convert childrens_stories to git worktree structure
#
# BEFORE RUNNING:
# 1. Review this script carefully
# 2. Ensure you have backups or can recover from git remote
# 3. Commit or stash any uncommitted changes you want to keep

PROJECT_NAME="childrens_stories"
PARENT_DIR="/home/kavin"
OLD_DIR="${PARENT_DIR}/${PROJECT_NAME}"
NEW_DIR="${PARENT_DIR}/${PROJECT_NAME}_worktree"
BACKUP_DIR="${PARENT_DIR}/${PROJECT_NAME}_backup"

echo "=== Git Worktree Migration Script ==="
echo "Old directory: ${OLD_DIR}"
echo "New directory: ${NEW_DIR}"
echo "Backup directory: ${BACKUP_DIR}"
echo ""

# Safety check
if [[ ! -d "${OLD_DIR}/.git" ]]; then
    echo "ERROR: ${OLD_DIR} is not a git repository"
    exit 1
fi

# Step 1: Stop services
echo "=== Step 1: Stopping services ==="
systemctl --user stop expo-frontend.service || true
systemctl --user stop stories-backend.service || true
systemctl --user stop stories-worker.service || true
echo "Services stopped"

# Step 2: Create backup of critical ignored files
echo ""
echo "=== Step 2: Backing up ignored files ==="
mkdir -p "${BACKUP_DIR}"
cp "${OLD_DIR}/.env" "${BACKUP_DIR}/.env"
cp "${OLD_DIR}/frontend/.env" "${BACKUP_DIR}/frontend.env"
cp -r "${OLD_DIR}/.claude" "${BACKUP_DIR}/.claude" 2>/dev/null || true
cp -r "${OLD_DIR}/data" "${BACKUP_DIR}/data"
echo "Backed up: .env, frontend/.env, .claude/, data/"

# Step 3: Create new directory structure
echo ""
echo "=== Step 3: Creating new directory structure ==="
mkdir -p "${NEW_DIR}"
cd "${NEW_DIR}"

# Step 4: Clone as bare repository
echo ""
echo "=== Step 4: Cloning as bare repository ==="
git clone --bare "${OLD_DIR}/.git" .bare
echo "gitdir: ./.bare" > .git

# Configure for worktree use
git config core.bare false
git config remote.origin.fetch "+refs/heads/*:refs/remotes/origin/*"
echo "Bare repository configured"

# Step 5: Create .shared directory with preserved files
echo ""
echo "=== Step 5: Setting up .shared directory ==="
mkdir -p .shared
cp "${BACKUP_DIR}/.env" .shared/.env
cp "${BACKUP_DIR}/frontend.env" .shared/frontend.env
cp -r "${BACKUP_DIR}/.claude" .shared/.claude 2>/dev/null || true
mv "${BACKUP_DIR}/data" .shared/data
echo "Shared files moved to .shared/"

# Step 6: Create main worktree
echo ""
echo "=== Step 6: Creating main worktree ==="
git worktree add main main
echo "Main worktree created"

# Step 7: Set up symlinks in main worktree
echo ""
echo "=== Step 7: Setting up symlinks ==="
cd main

# Root .env
ln -sf ../.shared/.env .env

# Frontend .env
ln -sf ../../.shared/frontend.env frontend/.env

# .claude directory
ln -sf ../.shared/.claude .claude

# data directory
ln -sf ../.shared/data data

echo "Symlinks created:"
ls -la .env .claude data frontend/.env

# Step 8: Install dependencies
echo ""
echo "=== Step 8: Installing dependencies ==="
cd "${NEW_DIR}/main"

# Python dependencies
if command -v poetry &> /dev/null; then
    poetry install --no-interaction
    echo "Python dependencies installed"
else
    echo "WARNING: poetry not found, skipping Python deps"
fi

# Node dependencies
cd frontend
if command -v npm &> /dev/null; then
    npm install
    echo "Node dependencies installed"
else
    echo "WARNING: npm not found, skipping Node deps"
fi
cd ..

# Step 9: Add .shared to .gitignore (in the worktree, will need to commit)
echo ""
echo "=== Step 9: Updating .gitignore ==="
if ! grep -q "^\.shared/$" .gitignore 2>/dev/null; then
    echo "" >> .gitignore
    echo "# Shared files for worktree setup" >> .gitignore
    echo ".shared/" >> .gitignore
    echo "Added .shared/ to .gitignore (needs to be committed)"
fi

# Step 10: Verify setup
echo ""
echo "=== Step 10: Verification ==="
echo "Checking symlinks..."
for f in .env .claude data frontend/.env; do
    if [[ -L "$f" ]] && [[ -e "$f" ]]; then
        echo "  ✓ $f -> $(readlink "$f")"
    else
        echo "  ✗ $f - BROKEN or missing"
    fi
done

echo ""
echo "Checking git status..."
git status --short | head -10

# Final instructions
echo ""
echo "=== Migration Complete ==="
echo ""
echo "New structure:"
echo "  ${NEW_DIR}/"
echo "  ├── .bare/          # Bare git repo"
echo "  ├── .git            # Points to .bare"
echo "  ├── .shared/        # Shared ignored files"
echo "  │   ├── .env"
echo "  │   ├── frontend.env"
echo "  │   ├── .claude/"
echo "  │   └── data/"
echo "  └── main/           # Main branch worktree"
echo ""
echo "Next steps:"
echo "  1. cd ${NEW_DIR}/main"
echo "  2. Verify everything works: poetry run pytest tests/unit/ -v"
echo "  3. Update systemd services to point to ${NEW_DIR}/main"
echo "  4. Restart services: systemctl --user start stories-backend stories-worker expo-frontend"
echo "  5. Once verified, remove old directory: rm -rf ${OLD_DIR}"
echo "  6. Rename new directory: mv ${NEW_DIR} ${OLD_DIR}"
echo "  7. Update systemd services back to original path"
echo ""
echo "To create a new worktree:"
echo "  cd ${NEW_DIR}"
echo "  git worktree add feature-xyz -b feature-xyz"
echo "  # Then set up symlinks in feature-xyz/"
