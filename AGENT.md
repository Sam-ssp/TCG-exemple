# The TCG Collection MVP web app

## Business Requirements

This project is building a TCG Collection webapp. Key features:
- A user can sign in his account
- When signed in, the user can access his collection and add new cards to his collection
- The webapp also give access to a navigation interface for all Pokemon card sorted across various ways : by Set, by Pokemon, by Illustrator, by Rarities
- User can create special lists in his collection.
- There is an AI chat feature in a sidebar, available from every tab; the AI is able to add cards to the collection, find specific cards from prompt, custom sort all existing cards in the navigation interface.

## Limitations

For the MVP, there will only be a user sign in (hardcoded to 'user' and 'user') but the database will support multiple users for future.

For the MVP, there will only be 1 TCG supported: Pokémon

For the MVP, this will run locally (in a docker container)

## Technical Decisions

- NextJS frontend
- Python FastAPI backend, including serving the static NextJS site at /
- Everything packaged into a Docker container
- Use "uv" as the package manager for python in the Docker container
- Use OpenRouter for the AI calls. An OPENROUTER_API_KEY is in .env in the project root
- Use `openai/gpt-oss-120b` as the model
- Use SQLLite local database for the database, creating a new db if it doesn't exist
- Start and Stop server scripts for Mac, PC, Linux in scripts/

## Starting Point

Database PLAN.md was created and need review and refinement.

## Color Scheme

- Main Grey: '#F3F3ED' 
- Main Dark Grey: '#515151' 
- Blue Accent: '#5D5C8E' 
- Red Accent: '#E78A78' 
- Green Accent: '#70BC94' 
- Yellow Accent: '#F1D3AC'

## Coding standards

1. Use latest versions of libraries and idiomatic approaches as of today
2. Keep it simple - NEVER over-engineer, ALWAYS simplify, NO unnecessary defensive programming. No extra features - focus on simplicity.
3. Be concise. Keep README minimal. IMPORTANT: no emojis ever
4. When hitting issues, always identify root cause before trying a fix. Do not guess. Prove with evidence, then fix the root cause.

## Working documentation

All documents for planning and executing this project will be in the docs/ directory.
Please review the docs/PLAN.md document before proceeding.