## NL2SQL Enterprise Data Proxy Agent

This project contains the source code and deployment scripts for an enterprise-grade Natural Language to SQL (NL2SQL) agent. The agent is designed to be deployed on Google Cloud's Agent Engine, and registered with Gemini Enterprise, provides a conversational interface to query structured data in a database.

## Key Features

*   **Natural Language to SQL:** Translates natural language questions into SQL queries.
*   **Enterprise Data Proxy:** Acts as a proxy to your enterprise data, allowing you to securely expose data to a conversational AI agent.
*   **Google Cloud Agent Engine:** Designed for deployment on Google Cloud's managed Agent Engine service.
*   **Debug and Deployment Scripts:** Includes a suite of scripts for debugging and deploying the agent.

## Getting Started

1.  **Configure Environment:** Copy the `.env.template` file to `.env` and fill in the required environment variables.
2.  **Deploy Agent:** Use the scripts in the `.scripts` directory to deploy the agent to your Google Cloud project.
3.  **Package for Distribution:** Use the `.scripts/zip.sh` script to create a distributable archive of the project.