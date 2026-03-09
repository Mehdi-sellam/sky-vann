#!/bin/bash


# Set domain and email from parameters

# Function to install Docker
install_docker() {
    echo "Docker not found. Installing Docker..."
    sudo apt-get update
    sudo sudo apt install apt-transport-https ca-certificates curl software-properties-common
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
 

    sudo apt-get update
    apt-cache policy docker-ce
    sudo apt install docker-ce
    
    echo "Docker installed successfully."
}

# Function to install Docker Compose
install_docker_compose() {
    echo "Docker Compose not found. Installing Docker Compose..."
    mkdir -p ~/.docker/cli-plugins/
    curl -SL https://github.com/docker/compose/releases/download/v2.3.3/docker-compose-linux-x86_64 -o ~/.docker/cli-plugins/docker-compose
    chmod +x ~/.docker/cli-plugins/docker-compose
    docker compose version
    echo "Docker Compose installed successfully."
}

# Check if Docker is installed
if ! [ -x "$(command -v docker)" ]; then
    install_docker
else
    echo "Docker is already installed."
fi

# Check if Docker Compose is installed
if ! [ -x "$(command -v docker-compose)" ]; then
    install_docker_compose
else
    echo "Docker Compose is already installed."
fi

# Check if the user is in the Docker group
if ! groups $USER | grep &>/dev/null "\bdocker\b"; then
    echo "Adding $USER to the docker group..."
    sudo usermod -aG docker ${USER}
    echo "Please log out and log back in to apply the group changes, then re-run this script."
    exit 0
fi



sudo ln -s ~/.docker/cli-plugins/docker-compose /usr/local/bin/docker-compose

# Create necessary directories for NGINX and Certbot if they don't exist
