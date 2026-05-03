#!/bin/bash
echo ""
echo "Paste your GitHub token (ghp_...) and press Enter:"
read -r TOKEN
if [ -z "$TOKEN" ]; then
  echo "No token entered. Exiting."
  exit 1
fi
git remote remove origin 2>/dev/null
git remote add origin "https://childersjac-max:${TOKEN}@github.com/childersjac-max/arbitrage-by-JAC.git"
echo "Pushing to GitHub..."
git push -u origin main
git remote remove origin 2>/dev/null
git remote add origin https://github.com/childersjac-max/arbitrage-by-JAC.git
echo ""
echo "All done! Token removed from config for security."
