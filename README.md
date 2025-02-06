# security-triage-bot

This bot is designed to aid with security case management. 

Using DFIR IRIS and Mattermost, cases can be listed and closed.

The GPT component queries the evidence for a case, queries the OpenAI Chat Completion endpoint and adds a note to the case.

The bot is designed to be deployed in a container. Dockerfile included. All authentication relies on HashiCorp Vault.

Chat interface demo
![mattermost_demo](https://github.com/user-attachments/assets/b066f1b6-b808-4ccc-aa20-6b0b6317418f)

DFIR-IRIS case overview
![iris_demo](https://github.com/user-attachments/assets/cee39458-9c42-4ce1-b6f2-dc9524a60fd0)
