# Project Journey: Building a Smart Investor Pitch Generator

This document chronicles the development of the "Smart Investor Pitch Generator," a tool designed to automatically create investor-ready pitch decks based on a company's Crunchbase profile.

## Table of Contents

- [Project Goal](#project-goal)
- [Initial Setup & Tech Stack](#initial-setup--tech-stack)
- [Key Development Stages & Decisions](#key-development-stages--decisions)
  - [Phase 1: Crunchbase API Integration](#phase-1-crunchbase-api-integration)
  - [Phase 2: Backend Development with Gemini](#phase-2-backend-development-with-gemini)
  - [Phase 3: Frontend with Streamlit](#phase-3-frontend-with-streamlit)
- [Challenges and Learnings](#challenges-and-learnings)

## Project Goal

The primary objective of this project was to leverage Large Language Models (LLMs) to automate the creation of compelling investor pitches. By inputting a company name, the tool fetches data from Crunchbase and uses it to generate a pitch deck covering key aspects like problem, solution, market size, and team.

## Initial Setup & Tech Stack

- **Frontend:** Streamlit
- **Backend:** Python
- **Core Logic:** Google Gemini
- **Data Source:** Crunchbase API

## Key Development Stages & Decisions

### Phase 1: Crunchbase API Integration

- **Initial Approach:** We started by using the `crunchbase-python` library to interact with the Crunchbase API.
- **Challenge:** We encountered issues with the library, specifically with authentication and searching for organizations. The library seemed to be outdated or not well-maintained.
- **Solution:** We switched to using the `requests` library to directly call the Crunchbase API. This gave us more control and allowed us to debug issues more effectively. We focused on the `/autocompletes` and `/entities/organizations/{uuid}` endpoints.
- **Learning:** Direct API calls, while more verbose, can be more reliable than depending on third-party libraries that might not be up-to-date.

### Phase 2: Backend Development with Gemini

- **Initial Approach:** We planned to use a simple Flask backend to handle requests from the frontend, call the Crunchbase API, and then pass the data to the Gemini model.
- **Prompt Engineering:** A significant amount of time was spent on crafting the perfect prompt for Gemini. We iterated multiple times to get the desired output format, tone, and content for the investor pitch. We experimented with different ways to structure the input data from Crunchbase to guide the model's output.
- **Challenge:** The initial prompts were too generic, leading to bland and uninspiring pitches.
- **Solution:** We developed a more detailed prompt that specified the sections of the pitch deck (Problem, Solution, etc.) and provided examples of the desired tone and style. We also found that providing curated data from Crunchbase, rather than the entire raw JSON, resulted in better outputs.

### Phase 3: Frontend with Streamlit

- **Simplicity:** Streamlit was chosen for its simplicity and speed of development. The goal was to create a minimal UI to input a company name and display the generated pitch.
- **UI Components:** We used `st.text_input` for the company name and `st.markdown` to display the generated pitch, which was formatted in Markdown.
- **Integration:** The Streamlit app calls the Python backend, which orchestrates the calls to Crunchbase and Gemini.

## Challenges and Learnings

- **API Reliability:** Relying on external APIs like Crunchbase means being prepared for potential downtime or changes in the API.
- **Prompt Engineering is Key:** The quality of the output from the LLM is highly dependent on the quality of the prompt. It's an iterative process of refinement.
- **Data Preprocessing:** Raw data from APIs often needs to be cleaned and structured before being fed to an LLM. This preprocessing step is crucial for getting high-quality results.
- **Tooling:** While Streamlit is great for rapid prototyping, for a more complex application, a more robust frontend framework might be necessary. 