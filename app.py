import streamlit as st
import requests
from itertools import cycle
import openai
import dotenv
import os
import json

# Open and read the JSON file
with open('company_tickers.json', 'r') as file:
    data = json.load(file)

# Load environment variables
dotenv.load_dotenv()
API_KEY = st.secrets["TRANSCRIPTS_API_KEY"]
OPEN_AI_API_KEY = st.secrets["OPEN_AI_API_KEY"]

# Set page configuration
st.set_page_config(layout="wide")

# Function to fetch transcripts for a single ticker
def fetch_transcripts_for_ticker(ticker: str, api_key: str) -> list:
    """
    Fetch earnings transcripts for all 4 quarters of 2024 and 2025 for a single ticker.
    Returns a list of transcripts for the given ticker.
    """
    years = [2024, 2025]
    quarters = [1, 2, 3, 4]
    transcripts = []
    
    for year in years:
        for quarter in quarters:
            api_url = f'https://api.api-ninjas.com/v1/earningstranscript?ticker={ticker}&year={year}&quarter={quarter}'
            response = requests.get(api_url, headers={'X-Api-Key': api_key})
            
            if response.status_code == 200:
                try:
                    transcript_data = response.json()
                    if transcript_data and "transcript" in transcript_data:
                        transcript = {
                            "ticker": ticker,
                            "year": year,
                            "quarter": quarter,
                            "content": transcript_data["transcript"],
                            "date": transcript_data.get("date", "N/A")
                        }
                        transcripts.append(transcript)
                except ValueError:
                    pass
    
    return transcripts

# Sidebar - User Input
st.sidebar.title("📊 Financial Transcript Viewer")

# Initialize session state
if "selected_tickers" not in st.session_state:
    st.session_state["selected_tickers"] = []  
if "ticker_input_key" not in st.session_state:
    st.session_state["ticker_input_key"] = 0  
if "transcripts_dict" not in st.session_state:
    st.session_state["transcripts_dict"] = {}  
if "selected_transcripts" not in st.session_state:
    st.session_state["selected_transcripts"] = set()
if "analyzed_transcripts" not in st.session_state:
    st.session_state["analyzed_transcripts"] = {}  
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []
if "transcript_summary" not in st.session_state:
    st.session_state["transcript_summary"] = ""
if "show_filter_modal" not in st.session_state:
    st.session_state["show_filter_modal"] = False  
if "filter_companies" not in st.session_state:
    st.session_state["filter_companies"] = set()  
if "filter_years" not in st.session_state:
    st.session_state["filter_years"] = set()  
if "filter_quarters" not in st.session_state:
    st.session_state["filter_quarters"] = set() 

# Parse the JSON document to extract tickers and company names
json_data = data

# Extract tickers and company names
ticker_options = []
for key, value in json_data.items():
    ticker = value["ticker"]
    title = value["title"]
    ticker_options.append({"ticker": ticker, "title": title, "label": f"{ticker} - {title}"})

# Sort ticker options alphabetically by ticker
ticker_options.sort(key=lambda x: x["ticker"].lower())

# Create the list of labels for the dropdown
dropdown_options = [option["label"] for option in ticker_options]

# Add a default option at the start
dropdown_options.insert(0, "Search by Ticker or Company Name...")

# Dropdown for ticker selection
selected_label = st.sidebar.selectbox(
    "**Select a Stock Ticker:**",
    options=dropdown_options,
    index=0,
    key=f"ticker_selectbox_{st.session_state['ticker_input_key']}"
)

# Handle ticker selection
if selected_label and selected_label != "Search by Ticker or Company Name...":
    selected_ticker = selected_label.split(" - ")[0]
    if selected_ticker not in st.session_state["selected_tickers"]:
        st.session_state["selected_tickers"].append(selected_ticker)
        
        with st.sidebar:
            with st.spinner(f"Fetching transcripts for {selected_ticker}..."):
                transcripts = fetch_transcripts_for_ticker(selected_ticker, API_KEY)
                if transcripts:
                    st.session_state["transcripts_dict"][selected_ticker] = transcripts
                else:
                    st.sidebar.warning(f"No transcripts found for {selected_ticker}.")
                    st.session_state["selected_tickers"].remove(selected_ticker)
        st.session_state["ticker_input_key"] += 1  
        st.rerun()

# Display selected tickers in rows (4 tickers per row)
if st.session_state["selected_tickers"]:
    st.sidebar.markdown("**Selected Tickers:**")
    tickers = st.session_state["selected_tickers"]
    num_tickers = len(tickers)
    tickers_per_row = 4
    num_rows = (num_tickers + tickers_per_row - 1) // tickers_per_row

    for row in range(num_rows):
        start_idx = row * tickers_per_row
        end_idx = min(start_idx + tickers_per_row, num_tickers)
        row_tickers = tickers[start_idx:end_idx]
        
        cols = st.sidebar.columns(len(row_tickers))
        for idx, ticker in enumerate(row_tickers):
            with cols[idx]:
                if st.button(f"{ticker} ✖️", key=f"remove_{ticker}_{start_idx + idx}", use_container_width=True):
                    st.session_state["selected_tickers"].remove(ticker)
                    if ticker in st.session_state["transcripts_dict"]:
                        del st.session_state["transcripts_dict"][ticker]
                    st.session_state["selected_transcripts"] = {
                        label for label in st.session_state["selected_transcripts"]
                        if not label.startswith(f"{ticker} ")
                    }
                    if not st.session_state["transcripts_dict"]:
                        st.session_state["chat_history"] = []
                        st.session_state["transcript_summary"] = ""
                        st.session_state["analyzed_transcripts"] = {}
                    st.rerun()

# Search Transcript input
search_query = st.sidebar.text_input("Search text in Available Transcript:")

# Define selected_transcripts
selected_transcripts = st.session_state["selected_transcripts"]

# Display Transcripts Grouped by Company Ticker with Filters
if st.session_state["transcripts_dict"]:
    all_transcripts = []
    for ticker, transcripts in st.session_state["transcripts_dict"].items():
        all_transcripts.extend(transcripts)
    
    if search_query:
        all_transcripts = [t for t in all_transcripts if search_query.lower() in t["content"].lower()]
    
    col1, col2 = st.columns([8, 1])
    with col1:
        st.subheader("Available Transcripts")
    with col2:
        if st.button("Filter", key="filter_available_transcripts"):
            st.session_state["show_filter_modal"] = not st.session_state["show_filter_modal"]

    if st.session_state["show_filter_modal"]:
        with st.expander("Filter Options", expanded=True):
            st.markdown("**Select Companies:**")
            companies = sorted({transcript["ticker"] for transcript in all_transcripts})
            for company in companies:
                if st.checkbox(company, value=(company in st.session_state["filter_companies"]), key=f"filter_company_{company}"):
                    st.session_state["filter_companies"].add(company)
                else:
                    st.session_state["filter_companies"].discard(company)

            st.markdown("**Select Years:**")
            years = sorted({transcript["year"] for transcript in all_transcripts})
            for year in years:
                if st.checkbox(str(year), value=(year in st.session_state["filter_years"]), key=f"filter_year_{year}"):
                    st.session_state["filter_years"].add(year)
                else:
                    st.session_state["filter_years"].discard(year)

            st.markdown("**Select Quarters:**")
            quarters = sorted({transcript["quarter"] for transcript in all_transcripts})
            for quarter in quarters:
                if st.checkbox(f"Q{quarter}", value=(quarter in st.session_state["filter_quarters"]), key=f"filter_quarter_{quarter}"):
                    st.session_state["filter_quarters"].add(quarter)
                else:
                    st.session_state["filter_quarters"].discard(quarter)

            if st.button("Apply Filters"):
                st.session_state["show_filter_modal"] = False
                st.rerun()

    filtered_transcripts = all_transcripts
    if st.session_state["filter_companies"]:
        filtered_transcripts = [t for t in filtered_transcripts if t["ticker"] in st.session_state["filter_companies"]]
    if st.session_state["filter_years"]:
        filtered_transcripts = [t for t in filtered_transcripts if t["year"] in st.session_state["filter_years"]]
    if st.session_state["filter_quarters"]:
        filtered_transcripts = [t for t in filtered_transcripts if t["quarter"] in st.session_state["filter_quarters"]]

    if filtered_transcripts:
        transcripts_by_ticker = {}
        for transcript in filtered_transcripts:
            ticker = transcript["ticker"]
            if ticker not in transcripts_by_ticker:
                transcripts_by_ticker[ticker] = []
            transcripts_by_ticker[ticker].append(transcript)
        
        for ticker, transcripts in transcripts_by_ticker.items():
            st.markdown(f"### {ticker}")
            cols = cycle(st.columns(4))
            for transcript in transcripts:
                col = next(cols)
                label = f"{transcript['ticker']} FY{transcript['year']} Q{transcript['quarter']} ({transcript['date']})"
                with col:
                    if col.button(f"FY{transcript['year']} Q{transcript['quarter']} ({transcript['date']})", key=f"btn_{label}", use_container_width=True):
                        if label in selected_transcripts:
                            selected_transcripts.remove(label)
                        else:
                            selected_transcripts.add(label)
        
        st.session_state["selected_transcripts"] = selected_transcripts
    else:
        st.markdown("**No transcripts match the selected filters.**")
else:
    st.subheader("Available Transcripts")
    st.markdown("**No transcripts selected**")

# Sidebar Display of Selected Transcripts
st.sidebar.subheader("Selected Transcripts")
if selected_transcripts:
    for label in selected_transcripts:
        st.sidebar.text(label)
else:
    st.sidebar.text("None selected")

# Prepare Data for Processing
if selected_transcripts:
    transcript_data = ""
    selected_by_ticker = {}
    for label in selected_transcripts:
        transcript = next((t for t in all_transcripts if f"{t['ticker']} FY{t['year']} Q{t['quarter']} ({t['date']})" == label), None)
        if transcript:
            ticker = transcript["ticker"]
            if ticker not in selected_by_ticker:
                selected_by_ticker[ticker] = []
            selected_by_ticker[ticker].append(transcript)
            transcript_data += f"\n\n### {label}\n{transcript['content']}"

# Prompt 1: Generate Summary for New Transcripts
if selected_transcripts:
    new_transcripts = {}
    for label in selected_transcripts:
        transcript = next((t for t in all_transcripts if f"{t['ticker']} FY{t['year']} Q{t['quarter']} ({t['date']})" == label), None)
        if transcript and label not in st.session_state["analyzed_transcripts"]:
            new_transcripts[label] = transcript["content"]

    if new_transcripts:
        client = openai.OpenAI(api_key=OPEN_AI_API_KEY)
        
        with st.spinner("AI is analyzing selected transcripts..."):
            # Prepare the prompt for summarizing the transcripts
            prompt_1 = """
You are a fundamental analyst with 5+ years of buy-side experience. Your purpose is to read earnings call transcripts and provide a summary for a financial analyst focused on fundamental equity research. Use only information directly from the transcript. Do not infer or fabricate data beyond what is explicitly mentioned. Prioritize clarity and brevity, but disclose figures (numbers, percentages) when citing any important point. Use bullet points when helpful. If a section (e.g., drivers of Margins) is not addressed in the transcript, clearly state ‘Not disclosed in call.’

**Output Structure:**
- Start with a one-paragraph summarization of the overall takeaway.
- Then, provide a more in-depth output organized by each period reported (e.g., Q1 2024, FY 2024).
- For each period, separate into two buckets: Topline and Margins.
  - Topline: Include Revenue growth, Gross Volume, or other topline KPIs.
  - Margins: Include Gross Margin, EBIT or Operating Margin, Net Margin, etc.
- For each period, provide a section with the most important questions asked by analysts during the call and management’s summarized answers (summarize only the answer, not the question).

**Example Output:**
Overall Takeaway:  
ABC Corp margins have been declining over the last few quarters (Q1, Q2, Q3 and Q4 of 2024) primarily due to (a) higher freight costs, (b) higher SG&A expenses – due to higher performance bonus, and (c) an increase in markdowns due to more promotional environment.  

Q4 2024  
Topline  
- Revenue grew +12% YoY (vs. +10% cons.), driven by:  
- +18% international growth (Europe +25%, APAC +15%)  
- Pricing contributed +4pts; volume flat overall  
- Core product A saw +20% YoY growth, while Product B declined -5%  
- Management cited stronger-than-expected holiday demand and FX tailwinds (+1pt)  

Margins  
- Gross margin compressed 180bps YoY to 52.1% (vs. 53.5% cons.)  
- Driven by +200bps in higher freight and warehousing costs  
- Partially offset by +50bps from favorable mix  
- EBIT margin fell to 18.4% (vs. 20.0% cons.)  
- Impacted by $30M restructuring charge (non-recurring)  
- Net margin at 13.5%, down 150bps YoY  

Key questions asked  
- Q: “Can you walk us through how much of the gross margin pressure is expected to persist into FY 2025?”  
  A (Summary): freight cost impacted 200bps, and higher promotional due to competitors higher discounts in the second half of 2025.  
- Q: “What assumptions underlie the conservative FY 2025 revenue guide?”  
  A (Summary): assume no macro improvement and no buybacks. Only the demand we see Today.

Analyze the following transcripts and provide the summary as per the structure above:
"""
            # Combine all new transcripts into the prompt
            prompt_1 += transcript_data

            # Call the OpenAI API to generate the summary
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": prompt_1}
                ]
            )
            summary = response.choices[0].message.content

            # Store the summary in session state
            st.session_state["transcript_summary"] = summary
            for label in new_transcripts.keys():
                st.session_state["analyzed_transcripts"][label] = summary

# Display the Transcript Summary (Always, if it exists)
if selected_transcripts and st.session_state["transcript_summary"]:
    st.subheader("📝 Transcript Summary")
    st.markdown(st.session_state["transcript_summary"])

# Prompt 2: Chatbot for Answering User Queries
if selected_transcripts:
    st.subheader("💬 Chat with AI about Selected Transcripts")

    chat_container = st.container()

    with chat_container:
        for user_query, ai_response in st.session_state["chat_history"]:
            with st.chat_message("user"):
                st.markdown(f"{user_query}")
            with st.chat_message("assistant"):
                st.markdown(f"{ai_response}")

    user_query = st.chat_input("Ask questions about the selected transcripts:")

    if user_query:
        with chat_container:
            with st.chat_message("user"):
                st.markdown(f"{user_query}")

        # Prepare the prompt for answering user queries
        prompt_2 = """
You are a fundamental analyst with 5+ years of buy-side experience. Your purpose is to answer questions based on the information provided in the selected earnings call transcripts for a financial analyst focused on fundamental equity research. Use only information directly from the transcript. Do not infer or fabricate data beyond what is explicitly mentioned. Prioritize clarity and brevity, but disclose figures (numbers, percentages) when citing any important point. Use bullet points when helpful. If a section or data point is not addressed in the transcript, clearly state ‘Not disclosed in call.’ Assume the user is an experienced portfolio manager.

Analyze the following transcripts and answer the user's question:
"""
        prompt_2 += transcript_data
        client = openai.OpenAI(api_key=OPEN_AI_API_KEY)

        # Call the OpenAI API to answer the user's query
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt_2},
                {"role": "user", "content": user_query}
            ]
        )
        answer = response.choices[0].message.content

        with chat_container:
            with st.chat_message("assistant"):
                st.markdown(f"{answer}")

        st.session_state["chat_history"].append((user_query, answer))