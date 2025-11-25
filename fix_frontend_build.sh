#!/bin/bash
# Fix frontend build issue - "Cannot find module 'nodepath'"
# This script cleans and reinstalls frontend dependencies

set -e

echo "🔧 Fixing frontend build issue..."
echo ""

PROJECT_DIR="/home/azureuser/MetaStackerBandit"
cd "$PROJECT_DIR/frontend"

echo "📦 Step 1: Checking Node.js version..."
node --version
npm --version
echo ""

echo "🧹 Step 2: Cleaning old dependencies..."
rm -rf node_modules
rm -f package-lock.json
echo "✅ Cleaned node_modules and package-lock.json"
echo ""

echo "📦 Step 3: Reinstalling dependencies..."
npm cache clean --force
npm install
echo "✅ Dependencies reinstalled"
echo ""

echo "🔨 Step 4: Testing build..."
npm run build
echo ""

echo "✅ Frontend build fixed!"
echo ""
echo "You can now restart the application:"
echo "  cd $PROJECT_DIR"
echo "  python3 start_project.py --gunicorn --daemon"

