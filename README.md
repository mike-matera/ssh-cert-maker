# SSH Certificate Service 

This is a work in progress. 

This agent creates an SSH key pair and signs the public key using an embedded SSH user certificate authority. The three files are downloaded to the client in a ZIP file. The purpose is to make a web application where a student can download an identity file for logging in to a shared Linux server. The server is configured to trust the user CA so there's no per-user `authorized_key` file configuration. When complete this process deprecates the use of passwords. 

## Technology 

This will be a Google Cloud Run application. 

## Authentication 

Authentication is not handled by this application. It must be done using Cloud Run. 

## To Do 

Change the application to use Google's authentication token. 

