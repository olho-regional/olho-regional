#!/bin/bash
set -e

echo "Starting dev server for compilation..."
npx nuxt dev --port 3000 &
DEV_PID=$!

# Wait for server to be ready
echo "Waiting for dev server..."
for i in $(seq 1 60); do
  if curl -s -o /dev/null -w '' http://localhost:3000/api/analises 2>/dev/null; then
    echo "Dev server ready!"
    break
  fi
  if [ $i -eq 60 ]; then
    echo "Timeout waiting for dev server"
    kill $DEV_PID 2>/dev/null
    exit 1
  fi
  sleep 1
done

echo "Compiling analyses..."
npx tsx scripts/compile-analises.ts

echo "Stopping dev server..."
kill $DEV_PID 2>/dev/null
wait $DEV_PID 2>/dev/null || true

echo "Building and deploying..."
npx nuxt build
npx wrangler pages deploy dist
