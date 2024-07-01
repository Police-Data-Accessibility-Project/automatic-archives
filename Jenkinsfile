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
        stage('Run Automatic Archive') {
            steps {
                echo 'Running Automatic Archive...'
                sh 'python cache_url.py'
            }
        }
    }
}