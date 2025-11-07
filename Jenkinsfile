pipeline {
    agent any
    
    environment {
        DOCKER_HOST = 'tcp://10.0.4.55:2376'
        DOCKER_TLS_VERIFY = '1'
        DOCKER_CERT_PATH = '/var/jenkins_home/docker-certs'
        DOCKER_REGISTRY = '10.0.6.48:3000'  // Gitea registry
        IMAGE_NAME = 'wol-api-service'
        DOCKER_CREDENTIALS_ID = 'gitea-docker-registry'  // You'll need to add this in Jenkins
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        
        stage('Build Docker Image') {
            steps {
                script {
                    // Build the Docker image
                    docker.build("${DOCKER_REGISTRY}/bifroest/${IMAGE_NAME}:${env.BUILD_NUMBER}")
                    docker.build("${DOCKER_REGISTRY}/bifroest/${IMAGE_NAME}:latest")
                }
            }
        }
        
        stage('Push to Registry') {
            steps {
                script {
                    // Login and push to Gitea Docker registry
                    docker.withRegistry("https://${DOCKER_REGISTRY}", "${DOCKER_CREDENTIALS_ID}") {
                        docker.image("${DOCKER_REGISTRY}/bifroest/${IMAGE_NAME}:${env.BUILD_NUMBER}").push()
                        docker.image("${DOCKER_REGISTRY}/bifroest/${IMAGE_NAME}:latest").push()
                    }
                }
            }
        }
        
        stage('Cleanup') {
            steps {
                script {
                    // Remove local images to save space
                    sh "docker rmi ${DOCKER_REGISTRY}/bifroest/${IMAGE_NAME}:${env.BUILD_NUMBER} || true"
                    sh "docker rmi ${DOCKER_REGISTRY}/bifroest/${IMAGE_NAME}:latest || true"
                }
            }
        }
    }
    
    post {
        success {
            echo 'WoL API Service built and pushed successfully!'
        }
        failure {
            echo 'Build or push failed!'
        }
    }
}
