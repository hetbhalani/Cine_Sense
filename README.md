# Create the README with the required header
cat > README.md << 'EOF'
---
title: Movie Sentiment Analysis API
emoji: 🎬
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
license: apache-2.0
---

# Movie Sentiment Analysis API

A FastAPI application for movie review sentiment analysis using RoBERTa.

## Endpoints:  
- POST /predict - Sentiment prediction


## Usage:
Visit `/docs` for interactive API documentation.
EOF