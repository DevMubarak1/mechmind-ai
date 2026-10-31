#!/usr/bin/env bash
# ==============================================================================
# MechMind AI — DigitalOcean Droplet Automated Setup Script
# Hacktoberfest 2026: Open-Source AI Prize Challenge
# ==============================================================================
set -e

echo "=== [1/5] Updating DigitalOcean Droplet Packages ==="
sudo apt-get update -y && sudo apt-get upgrade -y
sudo apt-get install -y git curl ufw htop

echo "=== [2/5] Installing Docker & Docker Compose ==="
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
fi

echo "=== [3/5] Installing Ollama for Open-Source Model Inference ==="
if ! command -v ollama &> /dev/null; then
    curl -fsSL https://ollama.com/install.sh | sh
fi

echo "=== [4/5] Pulling Google Gemma 2 (gemma2:2b) ==="
ollama serve > /dev/null 2>&1 &
sleep 3
ollama pull gemma2:2b

echo "=== [5/5] Launching MechMind AI Containerized Stack ==="
git clone https://github.com/DevMubarak1/mechmind-ai.git /opt/mechmind-ai || true
cd /opt/mechmind-ai/deploy/digitalocean
docker compose -f docker-compose.digitalocean.yml up -d --build

echo ""
echo "=============================================================================="
echo " MechMind AI Successfully Deployed on DigitalOcean!"
echo " Telemetry Dashboard: http://$(curl -s ifconfig.me):8080"
echo " WhatsApp Gateway:    http://$(curl -s ifconfig.me):3001"
echo "=============================================================================="
