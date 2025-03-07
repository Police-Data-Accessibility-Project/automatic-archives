#!/usr/bin/env groovy

/*
This script runs all health monitoring actions
*/

pipeline {

    agent {
        dockerfile {
            filename 'Dockerfile'
            args '-e VUE_APP_PDAP_API_KEY=$VUE_APP_PDAP_API_KEY -e VITE_VUE_APP_BASE_URL=$VITE_VUE_APP_BASE_URL'
        }
    }

    stages {
        stage('Retrieve JSON from Previous Build') {
            steps {
                script{
                    try {
                            copyArtifacts projectName: "${env.JOB_NAME}", filter: 'cache.json', selector: lastSuccessful()
                            def jsonContent = readFile 'cache.json'
                            def jsonData = new groovy.json.JsonSlurper().parseText(jsonContent)
                            echo "Loaded JSON from previous build: ${jsonData}"
                        } catch (Exception e) {
                            echo "No previous successful build found, proceeding without cache."
                    }
                }
            }
        }
        stage('Run Automatic Archive') {
            steps {
                echo 'Running Automatic Archive...'
                sh 'python cache_url.py'
            }
        }
        stage('Save cache') {
            steps {
                archiveArtifacts artifacts: 'cache.json', fingerprint: true
            }
        }
    }
    post {
        failure {
            script {
                def payload = """{
                    "content": "🚨 Build Failed: ${env.JOB_NAME} #${env.BUILD_NUMBER}"
                }"""

                sh """
                curl -X POST -H "Content-Type: application/json" -d '${payload}' ${env.WEBHOOK_URL}
                """
            }
        }
    }
}