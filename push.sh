#!/bin/bash
git remote remove origin 2>/dev/null
git remote add origin https://github.com/childersjac-max/arbitrage-by-JAC.git
echo "Remote set! Now run: git push -u origin main"
